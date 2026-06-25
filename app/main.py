from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import os

from app.database import get_db, engine, Base
from app.models import Client, Principal, Inquiry, Order, Comment, ActivityLog
from app.schemas import (
    InquiryOut, InquiryCreate, InquiryUpdate,
    OrderOut, OrderCreate, CommentOut, CommentCreate,
    ActivityLogOut, ClientOut, PrincipalOut, DashboardStats
)
from app.sync import import_from_excel, export_to_excel

# Create SQLite tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Team Engineering CRM API")

# API Routes

@app.get("/api/dashboard", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    # Count totals
    total_inquiries = db.query(Inquiry).filter(Inquiry.is_deleted == False).count()
    active_inquiries = db.query(Inquiry).filter(Inquiry.status == "Active", Inquiry.is_deleted == False).count()
    won_inquiries = db.query(Inquiry).filter(Inquiry.status == "Won", Inquiry.is_deleted == False).count()
    lost_inquiries = db.query(Inquiry).filter(Inquiry.status == "Lost", Inquiry.is_deleted == False).count()
    declined_inquiries = db.query(Inquiry).filter(Inquiry.status == "Declined", Inquiry.is_deleted == False).count()

    # Active Value (sum of values)
    active_objs = db.query(Inquiry).filter(Inquiry.status == "Active", Inquiry.is_deleted == False).all()
    total_value_active = sum([obj.value for obj in active_objs if obj.value is not None])

    # Won Value (sum of total order values)
    won_objs = db.query(Order).join(Inquiry).filter(Inquiry.status == "Won", Inquiry.is_deleted == False).all()
    total_value_won = sum([obj.total_order_value for obj in won_objs if obj.total_order_value is not None])

    # Alerts: Inquiries due this week or overdue
    due_this_week = []
    today = datetime.now().date()
    one_week_later = today + timedelta(days=7)

    all_active = db.query(Inquiry).filter(Inquiry.status == "Active", Inquiry.is_deleted == False).all()
    for inq in all_active:
        if inq.due_date:
            try:
                due_dt = datetime.strptime(inq.due_date, "%Y-%m-%d").date()
                # Overdue OR due within the next 7 days
                if due_dt <= one_week_later:
                    due_this_week.append(inq)
            except ValueError:
                # If date format is weird, skip or include if contains keyword
                pass

    # Alerts: Orders near delivery date (expected delivery within next 30 days)
    near_delivery = []
    thirty_days_later = today + timedelta(days=30)
    all_won_orders = db.query(Order).join(Inquiry).filter(Inquiry.status == "Won", Inquiry.is_deleted == False).all()
    for order in all_won_orders:
        if order.expected_delivery_date:
            try:
                del_dt = datetime.strptime(order.expected_delivery_date, "%Y-%m-%d").date()
                # Near delivery if expected date is between today - 30 days (overdue but recent) and today + 30 days
                if del_dt <= thirty_days_later and order.payment_status != "Order Supplied\nPaid" and order.payment_status != "Paid":
                    near_delivery.append(order.inquiry)
            except ValueError:
                pass

    return DashboardStats(
        total_inquiries=total_inquiries,
        active_inquiries=active_inquiries,
        won_inquiries=won_inquiries,
        lost_inquiries=lost_inquiries,
        declined_inquiries=declined_inquiries,
        total_value_active=total_value_active,
        total_value_won=total_value_won,
        due_this_week_alerts=due_this_week[:10],  # cap at 10 alerts
        near_delivery_alerts=near_delivery[:10]
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
        query = query.filter(Inquiry.status == status)

    inquiries = query.all()

    # Search filter in Python to handle relationship attributes and references easily
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
            
            if (s in client_name or 
                s in principal_name or 
                s in ref or 
                s in qref or 
                s in ord_num or 
                s in contact):
                filtered.append(inq)
        return filtered

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
    status: str = Query(..., description="Active, Won, Lost, Declined"),
    order_data: Optional[OrderCreate] = None,
    db: Session = Depends(get_db)
):
    inquiry = db.query(Inquiry).filter(Inquiry.id == id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    old_status = inquiry.status
    if old_status == status:
        return inquiry

    # Business Rules validation: Can't transition from Declined/Lost -> Won directly
    if old_status in ("Declined", "Lost") and status == "Won":
         raise HTTPException(
             status_code=400,
             detail="Cannot transition directly to Won from Lost/Declined. Transition back to Active first."
         )

    inquiry.status = status
    inquiry.last_update = datetime.now().strftime("%Y-%m-%d")

    # If transitioned to Won, handle Order record creation/update
    if status == "Won":
        if not order_data:
            raise HTTPException(
                status_code=400,
                detail="Order details are required when marking status as Won"
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
            for k, v in order_data.dict().items():
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
    try:
        export_to_excel()
        return {"status": "success", "message": "Database successfully synced back to Excel file."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export: {str(e)}")

@app.post("/api/sync/import")
def sync_import():
    try:
        import_from_excel()
        return {"status": "success", "message": "Database re-imported from Excel successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import: {str(e)}")

# Serve Static UI files
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
