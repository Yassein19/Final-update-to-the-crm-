from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import os
import time

from app.database import get_db, engine, Base
from app.models import Client, Principal, Inquiry, Order, Comment, ActivityLog
from app.schemas import (
    InquiryOut, InquiryCreate, InquiryUpdate,
    OrderOut, OrderCreate, CommentOut, CommentCreate,
    ActivityLogOut, ClientOut, PrincipalOut, DashboardStats,
    AnnualReportData, CategoryStats, ValueBreakdown, CategoryDetailItem, CategoryDetailView
)
from app.sync import import_from_excel, export_to_excel
from app.routers import analytics

# Create SQLite tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Team Engineering CRM API")
app.include_router(analytics.router)

# API Routes

@app.get("/api/dashboard", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    # Count totals
    total_inquiries = db.query(Inquiry).filter(Inquiry.is_deleted == False).count()
    active_inquiries = db.query(Inquiry).filter(Inquiry.status == "Active", Inquiry.is_deleted == False).count()
    won_inquiries = db.query(Inquiry).filter(Inquiry.status.in_(["Won", "Order"]), Inquiry.is_deleted == False).count()
    lost_inquiries = db.query(Inquiry).filter(Inquiry.status == "Lost", Inquiry.is_deleted == False).count()
    declined_inquiries = db.query(Inquiry).filter(Inquiry.status == "Declined", Inquiry.is_deleted == False).count()

    # Active Value (USD vs EUR vs EGP)
    active_objs = db.query(Inquiry).filter(Inquiry.status == "Active", Inquiry.is_deleted == False).all()
    total_value_active_usd = sum([obj.value for obj in active_objs if obj.value is not None and (obj.currency or 'USD').upper() == 'USD'])
    total_value_active_eur = sum([obj.value for obj in active_objs if obj.value is not None and (obj.currency or 'USD').upper() == 'EUR'])
    total_value_active_egp = sum([obj.value for obj in active_objs if obj.value is not None and (obj.currency or 'USD').upper() in ('EGP', 'LE', 'L.E')])

    # Won Value (USD vs EUR vs EGP)
    won_objs = db.query(Order).join(Inquiry).filter(Inquiry.status.in_(["Won", "Order"]), Inquiry.is_deleted == False).all()
    total_value_won_usd = sum([obj.total_order_value for obj in won_objs if obj.total_order_value is not None and (obj.currency or 'USD').upper() == 'USD'])
    total_value_won_eur = sum([obj.total_order_value for obj in won_objs if obj.total_order_value is not None and (obj.currency or 'USD').upper() == 'EUR'])
    total_value_won_egp = sum([obj.total_order_value for obj in won_objs if obj.total_order_value is not None and (obj.currency or 'USD').upper() in ('EGP', 'LE', 'L.E')])

    # Lost Value (USD vs EUR vs EGP)
    lost_objs = db.query(Inquiry).filter(Inquiry.status == "Lost", Inquiry.is_deleted == False).all()
    total_value_lost_usd = sum([obj.value for obj in lost_objs if obj.value is not None and (obj.currency or 'USD').upper() == 'USD'])
    total_value_lost_eur = sum([obj.value for obj in lost_objs if obj.value is not None and (obj.currency or 'USD').upper() == 'EUR'])
    total_value_lost_egp = sum([obj.value for obj in lost_objs if obj.value is not None and (obj.currency or 'USD').upper() in ('EGP', 'LE', 'L.E')])

    # Alerts: Inquiries due this week or overdue
    due_this_week = []
    today = datetime.now().date()
    one_week_later = today + timedelta(days=7)

    all_active = db.query(Inquiry).filter(Inquiry.status == "Active", Inquiry.is_deleted == False).all()
    for inq in all_active:
        if inq.due_date:
            try:
                due_dt = datetime.strptime(inq.due_date, "%Y-%m-%d").date()
                if due_dt <= one_week_later:
                    due_this_week.append(inq)
            except ValueError:
                pass

    # Alerts: Orders near delivery date
    near_delivery = []
    thirty_days_later = today + timedelta(days=30)
    all_won_orders = db.query(Order).join(Inquiry).filter(Inquiry.status.in_(["Won", "Order"]), Inquiry.is_deleted == False).all()
    for order in all_won_orders:
        if order.expected_delivery_date:
            try:
                del_dt = datetime.strptime(order.expected_delivery_date, "%Y-%m-%d").date()
                if del_dt <= thirty_days_later and (order.payment_status or "").lower() != "paid":
                    near_delivery.append(order.inquiry)
            except ValueError:
                pass

    return DashboardStats(
        total_inquiries=total_inquiries,
        active_inquiries=active_inquiries,
        won_inquiries=won_inquiries,
        lost_inquiries=lost_inquiries,
        declined_inquiries=declined_inquiries,
        total_value_active_usd=total_value_active_usd,
        total_value_active_eur=total_value_active_eur,
        total_value_active_egp=total_value_active_egp,
        total_value_won_usd=total_value_won_usd,
        total_value_won_eur=total_value_won_eur,
        total_value_won_egp=total_value_won_egp,
        total_value_lost_usd=total_value_lost_usd,
        total_value_lost_eur=total_value_lost_eur,
        total_value_lost_egp=total_value_lost_egp,
        due_this_week_alerts=due_this_week[:10],
        near_delivery_alerts=near_delivery[:10]
    )

@app.get("/api/annual-report", response_model=AnnualReportData)
def get_annual_report(year: Optional[str] = None, db: Session = Depends(get_db)):
    # Helper to calculate count and three-currency breakdown
    def calc_stats(inquiries_list):
        usd_val = sum([i.value for i in inquiries_list if i.value and (i.currency or 'USD').upper() == 'USD'])
        eur_val = sum([i.value for i in inquiries_list if i.value and (i.currency or 'USD').upper() == 'EUR'])
        egp_val = sum([i.value for i in inquiries_list if i.value and (i.currency or 'USD').upper() in ('EGP', 'LE', 'L.E')])
        return CategoryStats(count=len(inquiries_list), values=ValueBreakdown(usd=usd_val, eur=eur_val, egp=egp_val))

    def calc_order_stats(orders_list):
        usd_val = sum([o.total_order_value for o in orders_list if o.total_order_value and (o.currency or 'USD').upper() == 'USD'])
        eur_val = sum([o.total_order_value for o in orders_list if o.total_order_value and (o.currency or 'USD').upper() == 'EUR'])
        egp_val = sum([o.total_order_value for o in orders_list if o.total_order_value and (o.currency or 'USD').upper() in ('EGP', 'LE', 'L.E')])
        return CategoryStats(count=len(orders_list), values=ValueBreakdown(usd=usd_val, eur=eur_val, egp=egp_val))

    # Base inquiry query
    inq_query = db.query(Inquiry)
    if year and year.lower() != "all":
        inq_query = inq_query.filter(Inquiry.inquiry_date.like(f"%{year}%"))

    all_inqs = inq_query.all()
    non_deleted_inqs = [i for i in all_inqs if not i.is_deleted]

    # 1. Tenders / Inquiries
    tenders_total = calc_stats(non_deleted_inqs)
    tenders_cancelled = calc_stats([i for i in all_inqs if i.is_deleted])
    tenders_declined = calc_stats([i for i in non_deleted_inqs if i.status == "Declined"])
    tenders_firm = calc_stats([i for i in non_deleted_inqs if (i.offer_type or 'Firm').lower() == "firm"])
    tenders_budgetary = calc_stats([i for i in non_deleted_inqs if (i.offer_type or 'Firm').lower() == "budgetary"])

    # 2. Submitted offers
    submitted_lost = calc_stats([i for i in non_deleted_inqs if i.status == "Lost"])
    submitted_ongoing = calc_stats([i for i in non_deleted_inqs if i.status == "Active"])
    submitted_awarded = calc_stats([i for i in non_deleted_inqs if i.status in ("Won", "Order")])

    # 3. Orders breakdown
    order_query = db.query(Order).join(Inquiry).filter(Inquiry.is_deleted == False)
    if year and year.lower() != "all":
        order_query = order_query.filter((Order.order_date.like(f"%{year}%")) | (Inquiry.inquiry_date.like(f"%{year}%")))
    
    all_orders = order_query.all()
    orders_under_prod = calc_order_stats([o for o in all_orders if "production" in (o.order_status or "").lower()])
    orders_shipped = calc_order_stats([o for o in all_orders if "shipped" in (o.order_status or "").lower()])
    orders_paid = calc_order_stats([o for o in all_orders if (o.payment_status or "").lower() == "paid" or (o.order_status or "").lower() == "under payment"])
    orders_due = calc_order_stats([o for o in all_orders if (o.payment_status or "").lower() != "paid"])

    chart_dist = {
        "Active / Ongoing": len([i for i in non_deleted_inqs if i.status == "Active"]),
        "Order / Awarded": len([i for i in non_deleted_inqs if i.status in ("Won", "Order")]),
        "Lost Offers": len([i for i in non_deleted_inqs if i.status == "Lost"]),
        "Declined": len([i for i in non_deleted_inqs if i.status == "Declined"]),
        "Budgetary Offers": len([i for i in non_deleted_inqs if (i.offer_type or "").lower() == "budgetary"])
    }

    def build_category_view(cat_name, items):
        tot_count = len(items)
        usd_val = sum([i.value for i in items if i.value and str(i.currency or 'USD').upper() == 'USD'])
        eur_val = sum([i.value for i in items if i.value and str(i.currency or 'USD').upper() == 'EUR'])
        egp_val = sum([i.value for i in items if i.value and str(i.currency or 'USD').upper() in ('EGP', 'LE', 'L.E')])

        p_map = {}
        for i in items:
            p_name = i.principal.name if (i.principal and i.principal.name) else "Unknown Principal"
            if p_name not in p_map:
                p_map[p_name] = {"count": 0, "usd": 0.0, "eur": 0.0, "egp": 0.0}
            p_map[p_name]["count"] += 1
            val = i.value or 0.0
            curr = str(i.currency or 'USD').upper()
            if curr == 'USD':
                p_map[p_name]["usd"] += val
            elif curr == 'EUR':
                p_map[p_name]["eur"] += val
            elif curr in ('EGP', 'LE', 'L.E'):
                p_map[p_name]["egp"] += val

        p_items = []
        for p_name, stats in p_map.items():
            pct = round((stats["count"] / tot_count * 100.0), 1) if tot_count > 0 else 0.0
            p_items.append(CategoryDetailItem(
                name=p_name,
                count=stats["count"],
                percentage=pct,
                usd_value=round(stats["usd"], 2),
                eur_value=round(stats["eur"], 2),
                egp_value=round(stats["egp"], 2)
            ))
        p_items.sort(key=lambda x: x.count, reverse=True)

        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        monthly_freq = {m: 0 for m in months}
        for i in items:
            if i.inquiry_date:
                try:
                    d_str = str(i.inquiry_date).strip()
                    dt = None
                    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"):
                        try:
                            dt = datetime.strptime(d_str[:10] if len(d_str) >= 10 else d_str, fmt)
                            break
                        except ValueError:
                            continue
                    if dt:
                        m_str = months[dt.month - 1]
                        monthly_freq[m_str] += 1
                except Exception:
                    pass

        return CategoryDetailView(
            category_name=cat_name,
            total_count=tot_count,
            total_usd=round(usd_val, 2),
            total_eur=round(eur_val, 2),
            total_egp=round(egp_val, 2),
            principal_breakdown=p_items,
            monthly_frequency=monthly_freq
        )

    cat_views = {
        "Inquiries": build_category_view("Inquiries", non_deleted_inqs),
        "Declined": build_category_view("Declined", [i for i in non_deleted_inqs if i.status == "Declined"]),
        "Lost Offers": build_category_view("Lost Offers", [i for i in non_deleted_inqs if i.status == "Lost"]),
        "Budgetary": build_category_view("Budgetary", [i for i in non_deleted_inqs if (i.offer_type or "").lower() == "budgetary"]),
        "Ongoing Offers": build_category_view("Ongoing Offers", [i for i in non_deleted_inqs if i.status == "Active"]),
        "Orders": build_category_view("Orders", [i for i in non_deleted_inqs if i.status in ("Won", "Order")])
    }

    return AnnualReportData(
        year=year or "All Years",
        tenders_total=tenders_total,
        tenders_cancelled=tenders_cancelled,
        tenders_declined=tenders_declined,
        tenders_firm=tenders_firm,
        tenders_budgetary=tenders_budgetary,
        submitted_lost=submitted_lost,
        submitted_ongoing=submitted_ongoing,
        submitted_awarded=submitted_awarded,
        orders_under_production=orders_under_prod,
        orders_shipped=orders_shipped,
        orders_paid=orders_paid,
        orders_due_payment=orders_due,
        chart_distribution=chart_dist,
        category_views=cat_views
    )

@app.get("/api/inquiries", response_model=List[InquiryOut])
def get_inquiries(
    status: Optional[str] = None,
    search: Optional[str] = None,
    show_deleted: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(Inquiry)
    if not show_deleted:
        query = query.filter(Inquiry.is_deleted == False)
    else:
        query = query.filter(Inquiry.is_deleted == True)
        
    if status:
        if status.lower() != "all":
            query = query.filter(Inquiry.status == status)
    else:
        # Default: exclude Won inquiries from standard inquiries view (they move to Orders)
        query = query.filter(Inquiry.status != "Won")

    inquiries = query.all()

    if search:
        s = search.lower()
        filtered = []
        for inq in inquiries:
            client_name = inq.client.name.lower() if inq.client else ""
            principal_name = inq.principal.name.lower() if inq.principal else ""
            ref = inq.inquiry_reference.lower() if inq.inquiry_reference else ""
            qref = inq.quotation_reference.lower() if inq.quotation_reference else ""
            ord_num = inq.order.order_number.lower() if (inq.order and inq.order.order_number) else ""
            contact = inq.contact_person.lower() if inq.contact_person else ""
            inq_date = str(inq.inquiry_date or "").lower()
            due_date = str(inq.due_date or "").lower()
            last_upd = str(inq.last_update or "").lower()
            ord_date = str(inq.order.order_date or "").lower() if inq.order else ""
            exp_deliv = str(inq.order.expected_delivery_date or "").lower() if inq.order else ""
            
            if (s in client_name or 
                s in principal_name or 
                s in ref or 
                s in qref or 
                s in ord_num or 
                s in contact or
                s in inq_date or
                s in due_date or
                s in last_upd or
                s in ord_date or
                s in exp_deliv):
                filtered.append(inq)
        
        filtered.sort(key=lambda inq: (1 if (inq.inquiry_date or "").strip() else 0, (inq.inquiry_date or "").strip()), reverse=True)
        return filtered

    inquiries.sort(key=lambda inq: (1 if (inq.inquiry_date or "").strip() else 0, (inq.inquiry_date or "").strip()), reverse=True)
    return inquiries

@app.get("/api/inquiries/{id}", response_model=InquiryOut)
def get_inquiry(id: int, db: Session = Depends(get_db)):
    inquiry = db.query(Inquiry).filter(Inquiry.id == id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return inquiry

@app.post("/api/inquiries", response_model=InquiryOut)
def create_inquiry(payload: InquiryCreate, db: Session = Depends(get_db)):
    # Find or create Client & Principal
    client = db.query(Client).filter(Client.name == payload.client_name.strip()).first()
    if not client:
        client = Client(name=payload.client_name.strip())
        db.add(client)
        db.commit()
        db.refresh(client)

    principal = db.query(Principal).filter(Principal.name == payload.principal_name.strip()).first()
    if not principal:
        principal = Principal(name=payload.principal_name.strip())
        db.add(principal)
        db.commit()
        db.refresh(principal)

    inquiry = Inquiry(
        inquiry_date=payload.inquiry_date or datetime.now().strftime("%Y-%m-%d"),
        last_update=datetime.now().strftime("%Y-%m-%d"),
        due_date=payload.due_date,
        principal_id=principal.id,
        client_id=client.id,
        inquiry_reference=payload.inquiry_reference,
        quotation_reference=payload.quotation_reference,
        value=payload.value,
        currency=payload.currency or "USD",
        offer_type=payload.offer_type or "Firm",
        submission_method=payload.submission_method,
        status="Active",
        bid_bond_value=payload.bid_bond_value,
        performance_bond=payload.performance_bond,
        quotation_validity=payload.quotation_validity,
        expiration_date=payload.expiration_date,
        contact_person=payload.contact_person,
        is_deleted=False
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)

    # Activity log
    log = ActivityLog(
        inquiry_id=inquiry.id,
        action="Inquiry Created",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()

    return inquiry

@app.put("/api/inquiries/{id}", response_model=InquiryOut)
def update_inquiry(id: int, payload: InquiryUpdate, db: Session = Depends(get_db)):
    inquiry = db.query(Inquiry).filter(Inquiry.id == id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    if payload.client_name:
        client = db.query(Client).filter(Client.name == payload.client_name.strip()).first()
        if not client:
            client = Client(name=payload.client_name.strip())
            db.add(client)
            db.commit()
            db.refresh(client)
        inquiry.client_id = client.id

    if payload.principal_name:
        principal = db.query(Principal).filter(Principal.name == payload.principal_name.strip()).first()
        if not principal:
            principal = Principal(name=payload.principal_name.strip())
            db.add(principal)
            db.commit()
            db.refresh(principal)
        inquiry.principal_id = principal.id

    # Update basic fields if provided
    for key, val in payload.dict(exclude_unset=True).items():
        if key not in ("client_name", "principal_name"):
            setattr(inquiry, key, val)

    inquiry.last_update = datetime.now().strftime("%Y-%m-%d")
    db.commit()

    # Activity log
    log = ActivityLog(
        inquiry_id=inquiry.id,
        action="Inquiry Details Updated",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()

    return inquiry

@app.delete("/api/inquiries/{id}")
def delete_inquiry(id: int, db: Session = Depends(get_db)):
    inquiry = db.query(Inquiry).filter(Inquiry.id == id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    inquiry.is_deleted = True
    inquiry.last_update = datetime.now().strftime("%Y-%m-%d")
    
    log = ActivityLog(
        inquiry_id=inquiry.id,
        action="Inquiry Soft Deleted",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    return {"message": "Inquiry soft deleted successfully"}

@app.post("/api/inquiries/{id}/restore")
def restore_inquiry(id: int, db: Session = Depends(get_db)):
    inquiry = db.query(Inquiry).filter(Inquiry.id == id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    inquiry.is_deleted = False
    inquiry.last_update = datetime.now().strftime("%Y-%m-%d")
    
    log = ActivityLog(
        inquiry_id=inquiry.id,
        action="Inquiry Restored",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    return {"message": "Inquiry restored successfully"}

@app.post("/api/inquiries/{id}/transition", response_model=InquiryOut)
def transition_status(
    id: int,
    status: str = Query(..., description="Active, Order, Lost, Declined"),
    order_data: Optional[OrderCreate] = None,
    db: Session = Depends(get_db)
):
    inquiry = db.query(Inquiry).filter(Inquiry.id == id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    old_status = inquiry.status
    if old_status == status:
        return inquiry

    # Business Rules validation: Can't transition from Declined/Lost -> Order directly
    if old_status in ("Declined", "Lost") and status in ("Won", "Order"):
         raise HTTPException(
             status_code=400,
             detail="Cannot transition directly to Order from Lost/Declined. Transition back to Active first."
         )

    inquiry.status = status
    inquiry.last_update = datetime.now().strftime("%Y-%m-%d")

    # If transitioned to Order, handle Order record creation/update
    if status in ("Won", "Order"):
        if not order_data:
            raise HTTPException(
                status_code=400,
                detail="Order details are required when marking status as Order"
            )
        
        # Determine source sheet based on principal name for won orders
        sheet = "Orders"
        if inquiry.principal:
            p_name = inquiry.principal.name.lower()
            if "leser" in p_name:
                sheet = "LESER's Orders"
            elif "bartec" in p_name:
                sheet = " Bartec Orders" # Default to Bartec Orders

        order = db.query(Order).filter(Order.id == id).first()
        if not order:
            order = Order(
                id=id,
                **order_data.dict(exclude={"source_sheet"}),
                source_sheet=sheet
            )
            db.add(order)
        else:
            for k, v in order_data.dict(exclude={"source_sheet"}).items():
                setattr(order, k, v)
    else:
        # If transitioning away from Won, we keep order but it won't show in Orders sheet
        pass

    log = ActivityLog(
        inquiry_id=inquiry.id,
        action=f"Status transitioned from {old_status} to {status}",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    db.refresh(inquiry)

    return inquiry

# Comments routes

@app.post("/api/inquiries/{id}/comments", response_model=CommentOut)
def add_comment(id: int, payload: CommentCreate, db: Session = Depends(get_db)):
    inquiry = db.query(Inquiry).filter(Inquiry.id == id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    comment = Comment(
        inquiry_id=id,
        content=payload.content,
        created_at=datetime.utcnow()
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # Activity log
    log = ActivityLog(
        inquiry_id=id,
        action=f"Comment added: '{payload.content[:30]}...'",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()

    return comment

@app.get("/api/inquiries/{id}/comments", response_model=List[CommentOut])
def get_comments(id: int, db: Session = Depends(get_db)):
    inquiry = db.query(Inquiry).filter(Inquiry.id == id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return inquiry.comments

# Activity logs for audit trail

@app.get("/api/activity-logs", response_model=List[ActivityLogOut])
def get_activity_logs(db: Session = Depends(get_db)):
    return db.query(ActivityLog).order_by(ActivityLog.timestamp.desc()).limit(100).all()

# Master lookup lists

@app.get("/api/clients", response_model=List[ClientOut])
def get_clients(db: Session = Depends(get_db)):
    return db.query(Client).order_by(Client.name).all()

@app.get("/api/principals", response_model=List[PrincipalOut])
def get_principals(db: Session = Depends(get_db)):
    return db.query(Principal).order_by(Principal.name).all()

# Excel Sync routes

@app.post("/api/sync/export")
def sync_export():
    start_t = time.time()
    try:
        res = export_to_excel()
        elapsed = res.get("elapsed_seconds") if isinstance(res, dict) else round(time.time() - start_t, 2)
        msg = f"Excel Export SUCCEEDED in {elapsed:.2f} seconds."
        print(f"=== [SYNC API] {msg} ===")
        return {"status": "success", "message": msg, "elapsed_seconds": elapsed}
    except Exception as e:
        elapsed = round(time.time() - start_t, 2)
        msg = f"Excel Export FAILED after {elapsed:.2f} seconds. Error: {str(e)}"
        print(f"=== [SYNC API] {msg} ===")
        raise HTTPException(status_code=500, detail=msg)

@app.post("/api/sync/import")
def sync_import():
    start_t = time.time()
    try:
        res = import_from_excel()
        elapsed = res.get("elapsed_seconds") if isinstance(res, dict) else round(time.time() - start_t, 2)
        msg = f"Excel Import SUCCEEDED in {elapsed:.2f} seconds."
        print(f"=== [SYNC API] {msg} ===")
        return {"status": "success", "message": msg, "elapsed_seconds": elapsed}
    except Exception as e:
        elapsed = round(time.time() - start_t, 2)
        msg = f"Excel Import FAILED after {elapsed:.2f} seconds. Error: {str(e)}"
        print(f"=== [SYNC API] {msg} ===")
        raise HTTPException(status_code=500, detail=msg)

# Serve Static UI files
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
