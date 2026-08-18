from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import calendar

from app.database import get_db
from app.models import Client, Principal, Inquiry, Order, Comment, ActivityLog
from app.schemas import (
    CompanyReportData, CompanyKPIs, SalesAnalyticsData,
    TimeSeriesData, ComparisonAnalyticsData, MetricComparison
)

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Business Intelligence"])

def parse_date(date_str):
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None

def calculate_sales_cycle_days(inquiry: Inquiry):
    if not inquiry.inquiry_date:
        return 0
    start_dt = parse_date(inquiry.inquiry_date)
    if not start_dt:
        return 0
        
    end_dt = None
    if inquiry.order and inquiry.order.order_date:
        end_dt = parse_date(inquiry.order.order_date)
    elif inquiry.last_update:
        end_dt = parse_date(inquiry.last_update)
        
    if end_dt and end_dt >= start_dt:
        return (end_dt - start_dt).days
    return 0

@router.get("/company-report", response_model=CompanyReportData)
def get_company_report(
    company_type: str = Query("client", description="client or principal"),
    company_id: Optional[int] = None,
    company_name: Optional[str] = None,
    client_id: Optional[int] = None,  # Backward compatibility
    db: Session = Depends(get_db)
):
    target_type = (company_type or "client").lower()
    target_id = company_id or client_id
    
    entity = None
    resolved_type = "Client"
    
    if target_type == "principal":
        resolved_type = "Principal"
        if target_id:
            entity = db.query(Principal).filter(Principal.id == target_id).first()
        elif company_name:
            entity = db.query(Principal).filter(Principal.name.ilike(company_name.strip())).first()
        else:
            principals = db.query(Principal).all()
            if principals:
                entity = max(principals, key=lambda p: len(p.inquiries))
    else:
        resolved_type = "Client"
        if target_id:
            entity = db.query(Client).filter(Client.id == target_id).first()
        elif company_name:
            entity = db.query(Client).filter(Client.name.ilike(company_name.strip())).first()
        else:
            clients = db.query(Client).all()
            if clients:
                entity = max(clients, key=lambda c: len(c.inquiries))

    if not entity:
        raise HTTPException(status_code=404, detail=f"No {resolved_type} records found for intelligence report.")

    inqs = [i for i in entity.inquiries if not i.is_deleted]
    total_inqs = len(inqs)
    active_inqs = len([i for i in inqs if i.status == "Active"])
    won_inqs = len([i for i in inqs if i.status in ("Won", "Order")])
    lost_inqs = len([i for i in inqs if i.status == "Lost"])
    declined_inqs = len([i for i in inqs if i.status == "Declined"])

    win_rate = round((won_inqs / total_inqs * 100), 1) if total_inqs > 0 else 0.0

    # Values
    inqs_usd = [i.value for i in inqs if i.value and (i.currency or 'USD').upper() == 'USD']
    inqs_eur = [i.value for i in inqs if i.value and (i.currency or 'USD').upper() == 'EUR']
    avg_inq_usd = round(sum(inqs_usd) / len(inqs_usd), 2) if inqs_usd else 0.0
    avg_inq_eur = round(sum(inqs_eur) / len(inqs_eur), 2) if inqs_eur else 0.0

    orders = [i.order for i in inqs if i.status in ("Won", "Order") and i.order]
    active_objs = [i for i in inqs if i.status == "Active"]
    pipe_usd = round(sum([i.value for i in active_objs if i.value and (i.currency or 'USD').upper() == 'USD']), 2)
    pipe_eur = round(sum([i.value for i in active_objs if i.value and (i.currency or 'USD').upper() == 'EUR']), 2)

    sales_cycles = [calculate_sales_cycle_days(i) for i in inqs if i.status in ("Won", "Order", "Lost")]
    avg_cycle = round(sum(sales_cycles) / len(sales_cycles), 1) if sales_cycles else 0.0

    kpis = CompanyKPIs(
        win_rate=win_rate,
        avg_inquiry_val_usd=avg_inq_usd,
        avg_inquiry_val_eur=avg_inq_eur,
        avg_sales_cycle_days=avg_cycle,
        pipeline_value_usd=pipe_usd,
        pipeline_value_eur=pipe_eur,
        total_inquiries=total_inqs,
        active_inquiries=active_inqs,
        won_orders=won_inqs,
        lost_inquiries=lost_inqs,
        declined_inquiries=declined_inqs
    )

    # Top counterparties (Principals if searching Client; Clients if searching Principal)
    partner_counts = {}
    for i in inqs:
        p_name = i.principal.name if (resolved_type == "Client" and i.principal) else (i.client.name if (resolved_type == "Principal" and i.client) else "Unknown")
        partner_counts[p_name] = partner_counts.get(p_name, 0) + 1
        
    most_active_p = max(partner_counts, key=partner_counts.get) if partner_counts else "N/A"
    p_perf = [{"principal": k, "count": v} for k, v in sorted(partner_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

    # Largest orders
    sorted_orders = sorted(orders, key=lambda o: o.total_order_value or 0, reverse=True)[:5]
    largest = [{
        "order_number": o.order_number or f"ORD-{o.id}",
        "order_date": o.order_date or "-",
        "value": o.total_order_value or 0,
        "currency": o.currency or "USD",
        "principal": o.inquiry.principal.name if (o.inquiry and o.inquiry.principal) else "Unknown"
    } for o in sorted_orders]

    # Stalled inquiries (>14 days inactive)
    stalled_count = 0
    today = datetime.now().date()
    for i in active_objs:
        dt = parse_date(i.last_update or i.inquiry_date)
        if dt and (today - dt).days >= 14:
            stalled_count += 1

    partner_label = "primary equipment principal" if resolved_type == "Client" else "top purchasing client"
    ai_summary = (
        f"{resolved_type} '{entity.name}' has achieved a {win_rate}% win rate across {total_inqs} total commercial inquiries ({won_inqs} won contracts). "
        f"Their {partner_label} is {most_active_p}. "
        f"{stalled_count} active inquiry/inquiries have been pending updates for 14+ days and require sales follow-up."
    )

    return CompanyReportData(
        company_id=entity.id,
        company_name=entity.name,
        company_type=resolved_type,
        kpis=kpis,
        inquiry_trend={},
        principal_performance=p_perf,
        largest_orders=largest,
        most_active_principal=most_active_p,
        inquiries=inqs,
        ai_executive_summary=ai_summary
    )

@router.get("/sales-dashboard", response_model=SalesAnalyticsData)
def get_sales_dashboard(db: Session = Depends(get_db)):
    all_inqs = db.query(Inquiry).filter(Inquiry.is_deleted == False).all()
    today = datetime.now().date()

    # Time filters
    today_str = today.strftime("%Y-%m-%d")
    week_start = today - timedelta(days=7)
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    def filter_by_date(items, start_date, end_date=None, attr="inquiry_date"):
        res = []
        for item in items:
            raw_d = getattr(item, attr, None)
            dt = parse_date(raw_d)
            if dt and dt >= start_date:
                if end_date and dt > end_date:
                    continue
                res.append(item)
        return res

    def filter_won_by_date(items, start_date, end_date=None):
        res = []
        for item in items:
            if item.status in ("Won", "Order"):
                ord_date = item.order.order_date if item.order else None
                dt = parse_date(ord_date) if ord_date else parse_date(item.inquiry_date)
                if dt and dt >= start_date:
                    if end_date and dt > end_date:
                        continue
                    res.append(item)
        return res

    def filter_lost_declined_by_date(items, start_date, status, end_date=None):
        res = []
        for item in items:
            if item.status == status:
                dt = parse_date(item.last_update or item.inquiry_date)
                if dt and dt >= start_date:
                    if end_date and dt > end_date:
                        continue
                    res.append(item)
        return res

    # Daily analytics
    d_new = filter_by_date(all_inqs, today, attr="inquiry_date")
    d_won = filter_won_by_date(all_inqs, today)
    d_lost = filter_lost_declined_by_date(all_inqs, today, "Lost")
    d_declined = filter_lost_declined_by_date(all_inqs, today, "Declined")
    
    daily_stats = {
        "new_inquiries": len(d_new),
        "won_orders": len(d_won),
        "lost_inquiries": len(d_lost),
        "declined_inquiries": len(d_declined),
        "active_inquiries": len([i for i in all_inqs if i.status == "Active"]),
        "due_today": len([i for i in all_inqs if i.status == "Active" and parse_date(i.due_date) == today])
    }

    # Weekly analytics
    w_inqs = filter_by_date(all_inqs, week_start, attr="inquiry_date")
    w_won = filter_won_by_date(all_inqs, week_start)

    weekly_stats = {
        "weekly_inquiries": len(w_inqs),
        "won_orders": len(w_won)
    }

    # Monthly & Yearly Analytics
    m_inqs = filter_by_date(all_inqs, month_start, attr="inquiry_date")
    y_inqs = filter_by_date(all_inqs, year_start, attr="inquiry_date")

    m_won = filter_won_by_date(all_inqs, month_start)
    y_won = filter_won_by_date(all_inqs, year_start)

    monthly_stats = {
        "inquiries_count": len(m_inqs),
        "won_orders": len(m_won),
        "win_rate": round((len(m_won) / len(m_inqs) * 100), 1) if m_inqs else 0.0
    }

    yearly_stats = {
        "inquiries_count": len(y_inqs),
        "won_orders": len(y_won),
        "win_rate": round((len(y_won) / len(y_inqs) * 100), 1) if y_inqs else 0.0
    }

    insights = [
        f"Year-to-date won orders total {len(y_won)} across {len(y_inqs)} commercial inquiries.",
        f"This month has logged {len(m_inqs)} new inquiries with a {monthly_stats['win_rate']}% conversion win rate.",
        f"Currently {daily_stats['active_inquiries']} active inquiries are in progress in the commercial pipeline."
    ]

    return SalesAnalyticsData(
        daily=daily_stats,
        weekly=weekly_stats,
        monthly=monthly_stats,
        yearly=yearly_stats,
        insights=insights
    )

@router.get("/time-series", response_model=TimeSeriesData)
def get_time_series(period: str = Query("Monthly", description="Daily, Weekly, Monthly, Quarterly, Yearly"), db: Session = Depends(get_db)):
    all_inqs = db.query(Inquiry).filter(Inquiry.is_deleted == False).all()
    
    # Group inquiries by timeframe label
    buckets = {}
    for inq in all_inqs:
        dt = parse_date(inq.inquiry_date)
        if not dt:
            continue
            
        p = (period or "Monthly").lower()
        if p == "monthly":
            label = dt.strftime("%b %Y")
            sort_key = dt.strftime("%Y-%m")
        elif p == "quarterly":
            q = (dt.month - 1) // 3 + 1
            label = f"Q{q} {dt.year}"
            sort_key = f"{dt.year}-Q{q}"
        elif p == "yearly":
            label = str(dt.year)
            sort_key = str(dt.year)
        else: # Weekly / Daily
            label = dt.strftime("%Y-%m-%d")
            sort_key = label

        if sort_key not in buckets:
            buckets[sort_key] = {"label": label, "inqs": [], "won": []}
        buckets[sort_key]["inqs"].append(inq)
        if inq.status in ("Won", "Order"):
            buckets[sort_key]["won"].append(inq)

    sorted_keys = sorted(buckets.keys())
    labels = []
    inqs_cnt = []
    won_cnt = []
    pipe_usd = []
    pipe_eur = []
    win_rates = []
    sales_cycles = []

    for k in sorted_keys:
        b = buckets[k]
        labels.append(b["label"])
        b_inqs = b["inqs"]
        b_won = b["won"]
        
        inqs_cnt.append(len(b_inqs))
        won_cnt.append(len(b_won))
        
        active_inqs = [i for i in b_inqs if i.status == "Active"]
        p_usd = sum([i.value for i in active_inqs if i.value and (i.currency or 'USD').upper() == 'USD'])
        p_eur = sum([i.value for i in active_inqs if i.value and (i.currency or 'USD').upper() == 'EUR'])
        pipe_usd.append(round(p_usd, 2))
        pipe_eur.append(round(p_eur, 2))
        
        wr = round((len(b_won) / len(b_inqs) * 100), 1) if b_inqs else 0.0
        win_rates.append(wr)

        cycles = [calculate_sales_cycle_days(i) for i in b_inqs if i.status in ("Won", "Lost")]
        avg_c = round(sum(cycles) / len(cycles), 1) if cycles else 0.0
        sales_cycles.append(avg_c)

    return TimeSeriesData(
        period_type=period or "Monthly",
        labels=labels,
        inquiries_count=inqs_cnt,
        won_orders_count=won_cnt,
        pipeline_usd=pipe_usd,
        pipeline_eur=pipe_eur,
        win_rate=win_rates,
        avg_sales_cycle_days=sales_cycles
    )

@router.get("/comparison", response_model=ComparisonAnalyticsData)
def get_comparison(period: str = Query("Monthly", description="Daily, Weekly, Monthly, Yearly"), db: Session = Depends(get_db)):
    all_inqs = db.query(Inquiry).filter(Inquiry.is_deleted == False).all()
    today = datetime.now().date()

    p = (period or "Monthly").lower()
    if p == "daily":
        curr_start = today
        prev_start = today - timedelta(days=1)
        prev_end = prev_start
        curr_label = "Today"
        prev_label = "Yesterday"
    elif p == "weekly":
        curr_start = today - timedelta(days=7)
        prev_start = curr_start - timedelta(days=7)
        prev_end = curr_start - timedelta(days=1)
        curr_label = "This Week"
        prev_label = "Last Week"
    elif p == "yearly":
        curr_start = today.replace(month=1, day=1)
        prev_start = today.replace(year=today.year - 1, month=1, day=1)
        prev_end = today.replace(year=today.year - 1, month=12, day=31)
        curr_label = f"{today.year}"
        prev_label = f"{today.year - 1}"
    else:  # Monthly (default)
        curr_start = today.replace(day=1)
        first_of_this_month = today.replace(day=1)
        last_day_prev_month = first_of_this_month - timedelta(days=1)
        prev_start = last_day_prev_month.replace(day=1)
        prev_end = last_day_prev_month
        curr_label = today.strftime("%B %Y")
        prev_label = prev_start.strftime("%B %Y")

    def filter_period(inquiries, start, end=None):
        res = []
        for i in inquiries:
            dt = parse_date(i.inquiry_date)
            if dt and dt >= start:
                if end and dt > end:
                    continue
                res.append(i)
        return res

    curr_inqs = filter_period(all_inqs, curr_start)
    prev_inqs = filter_period(all_inqs, prev_start, prev_end)

    def calc_metrics(inq_list):
        won = [i for i in inq_list if i.status in ("Won", "Order")]
        active = [i for i in inq_list if i.status == "Active"]
        pipe_usd = sum([i.value for i in active if i.value and (i.currency or 'USD').upper() == 'USD'])
        wr = round((len(won) / len(inq_list) * 100), 1) if inq_list else 0.0
        return {
            "inquiries": len(inq_list),
            "orders": len(won),
            "win_rate": wr,
            "pipeline_usd": round(pipe_usd, 2)
        }

    c_m = calc_metrics(curr_inqs)
    p_m = calc_metrics(prev_inqs)

    def make_cmp(curr_v, prev_v):
        if prev_v > 0:
            chg = round(((curr_v - prev_v) / prev_v * 100), 1)
        else:
            chg = 100.0 if curr_v > 0 else 0.0
        dir_val = "up" if chg > 0 else ("down" if chg < 0 else "flat")
        return MetricComparison(current=curr_v, previous=prev_v, change_pct=chg, direction=dir_val)

    comparison_dict = {
        "Inquiries": make_cmp(c_m["inquiries"], p_m["inquiries"]),
        "Won Orders": make_cmp(c_m["orders"], p_m["orders"]),
        "Win Rate (%)": make_cmp(c_m["win_rate"], p_m["win_rate"]),
        "Pipeline (USD)": make_cmp(c_m["pipeline_usd"], p_m["pipeline_usd"])
    }

    inq_cmp = comparison_dict["Inquiries"]
    exp = (
        f"Comparing {curr_label} vs {prev_label}: Inquiries changed by {inq_cmp.change_pct}% "
        f"({c_m['inquiries']} vs {p_m['inquiries']})."
    )

    return ComparisonAnalyticsData(
        period=period or "Monthly",
        current_label=curr_label,
        previous_label=prev_label,
        metrics=comparison_dict,
        natural_explanation=exp
    )
