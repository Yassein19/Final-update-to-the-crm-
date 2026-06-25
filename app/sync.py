import os
import pandas as pd
import numpy as np
from datetime import datetime
import openpyxl
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import Client, Principal, Inquiry, Order, Comment, ActivityLog

EXCEL_PATH = r"c:\Users\yassein ahmed\OneDrive\Desktop\Team Eng\STATUS 2025-2026.xlsx"

def clean_str(val):
    if pd.isna(val) or val is None:
        return ""
    val_str = str(val).strip()
    if val_str.endswith(".0"):
        # For numbers loaded as float strings
        val_str = val_str[:-2]
    return val_str

def clean_float(val):
    if pd.isna(val) or val is None:
        return 0.0
    try:
        return float(val)
    except ValueError:
        return 0.0

def clean_date(val):
    if pd.isna(val) or val is None or str(val).strip() == "":
        return ""
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, pd.Timestamp):
        return val.strftime("%Y-%m-%d")
    val_str = str(val).strip()
    # Try parsing different formats
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(val_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return val_str

def get_or_create_client(db: Session, name: str):
    name = name.strip()
    if not name:
        name = "Unknown Client"
    client = db.query(Client).filter(Client.name == name).first()
    if not client:
        client = Client(name=name)
        db.add(client)
        db.commit()
        db.refresh(client)
    return client

def get_or_create_principal(db: Session, name: str):
    name = name.strip()
    if not name:
        name = "Unknown Principal"
    principal = db.query(Principal).filter(Principal.name == name).first()
    if not principal:
        principal = Principal(name=name)
        db.add(principal)
        db.commit()
        db.refresh(principal)
    return principal

def import_from_excel():
    db = SessionLocal()
    try:
        # Reset database tables
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("Database tables recreated.")

        xls = pd.ExcelFile(EXCEL_PATH)
        sheet_names = xls.sheet_names
        print("Sheets found:", sheet_names)

        # 1. Parse Inquiries Sheets
        inquiries_sheets = {
            "Inquires": "Active",
            "Declined Inquiries": "Declined",
            "Lost Inquiries": "Lost"
        }

        for sheet, status in inquiries_sheets.items():
            if sheet not in sheet_names:
                print(f"Warning: Sheet {sheet} not found in Excel.")
                continue
            
            df = pd.read_excel(xls, sheet_name=sheet, header=7)
            # Remove entirely empty rows
            df = df.dropna(how='all')
            print(f"Processing sheet {sheet}: {len(df)} rows found.")

            for _, row in df.iterrows():
                principal_name = clean_str(row.get("Principal", ""))
                client_name = clean_str(row.get("Client", ""))
                if not principal_name and not client_name:
                    continue  # skip empty/header padding rows

                client = get_or_create_client(db, client_name)
                principal = get_or_create_principal(db, principal_name)

                inquiry = Inquiry(
                    inquiry_date=clean_date(row.get("Inquiry Date")),
                    last_update=clean_date(row.get("Last Update")),
                    due_date=clean_date(row.get(" Due date") if " Due date" in row else row.get("Due date")),
                    principal_id=principal.id,
                    client_id=client.id,
                    inquiry_reference=clean_str(row.get("Inquiry Reference")),
                    quotation_reference=clean_str(row.get("Quotation Reference")),
                    value=clean_float(row.get(" Values") if " Values" in row else row.get("Values")),
                    submission_method=clean_str(row.get("Submission Method")),
                    status=status,
                    bid_bond_value=clean_str(row.get("Bid Bond Value")),
                    performance_bond=clean_str(row.get("Performance Bond")),
                    quotation_validity=clean_str(row.get("Quotation Validity")),
                    expiration_date=clean_date(row.get(" Expiration Date") if " Expiration Date" in row else row.get("Expiration Date")),
                    contact_person=clean_str(row.get("Contact Person")),
                    is_deleted=False
                )
                db.add(inquiry)
                db.commit()
                db.refresh(inquiry)

                # Parse and add comments
                comments_text = clean_str(row.get("Comments / Updates", ""))
                if comments_text:
                    # Legacy sheets contain multi-line comments. We split them by newline.
                    comment_lines = [c.strip() for c in comments_text.split('\n') if c.strip()]
                    for line in comment_lines:
                        comment = Comment(
                            inquiry_id=inquiry.id,
                            content=line,
                            created_at=datetime.utcnow()
                        )
                        db.add(comment)
                    db.commit()

                # Add initial activity log
                log = ActivityLog(
                    inquiry_id=inquiry.id,
                    action=f"Imported from Excel '{sheet}' sheet with status '{status}'",
                    timestamp=datetime.utcnow()
                )
                db.add(log)
                db.commit()

        # 2. Parse Won Order Sheets
        order_sheets = ["Orders", "LESER's Orders", " Bartec Orders", " Bartec Orders 2025"]
        for sheet in order_sheets:
            if sheet not in sheet_names:
                print(f"Warning: Sheet {sheet} not found in Excel.")
                continue
            
            df = pd.read_excel(xls, sheet_name=sheet, header=6)
            df = df.dropna(how='all')
            print(f"Processing sheet {sheet}: {len(df)} rows.")

            for _, row in df.iterrows():
                client_name = clean_str(row.get("Client", ""))
                principal_name = clean_str(row.get("Principal", ""))
                if not client_name and not principal_name:
                    continue

                client = get_or_create_client(db, client_name)
                principal = get_or_create_principal(db, principal_name)

                inquiry_ref = clean_str(row.get("Client Refrence (Inquiry no.)"))
                quot_ref = clean_str(row.get("Principal Reference (Quotation no.)"))
                inquiry_date = clean_date(row.get("Inquiry Date"))

                # Try to find a matching Inquiry in database
                inquiry = None
                if inquiry_ref or quot_ref:
                    if inquiry_ref:
                        inquiry = db.query(Inquiry).filter(
                            Inquiry.client_id == client.id,
                            Inquiry.principal_id == principal.id,
                            Inquiry.inquiry_reference == inquiry_ref,
                            Inquiry.status != "Won"
                        ).first()
                    if not inquiry and quot_ref:
                        inquiry = db.query(Inquiry).filter(
                            Inquiry.client_id == client.id,
                            Inquiry.principal_id == principal.id,
                            Inquiry.quotation_reference == quot_ref,
                            Inquiry.status != "Won"
                        ).first()
                
                if not inquiry:
                    # Create base inquiry since none matched
                    inquiry = Inquiry(
                        inquiry_date=inquiry_date,
                        last_update=clean_date(datetime.utcnow()),
                        due_date="",
                        principal_id=principal.id,
                        client_id=client.id,
                        inquiry_reference=inquiry_ref,
                        quotation_reference=quot_ref,
                        value=clean_float(row.get("Order Value")),
                        submission_method="Excel Import",
                        status="Won",
                        is_deleted=False
                    )
                    db.add(inquiry)
                    db.commit()
                    db.refresh(inquiry)
                else:
                    # Update existing inquiry status to Won
                    inquiry.status = "Won"
                    db.commit()

                # Parse total order value column (varies in LESER's Orders)
                tot_val_col = "Total Price" if "Total Price" in row else "Total Order Value"
                
                # Check for TEAM Commisiion
                team_comm = clean_str(row.get("TEAM Commisiion", ""))

                order = Order(
                    id=inquiry.id,
                    order_number=clean_str(row.get("Order Number")),
                    order_date=clean_date(row.get("Order Date")),
                    order_value=clean_float(row.get("Order Value")),
                    additionals=clean_float(row.get("Additionals")),
                    total_order_value=clean_float(row.get(tot_val_col)),
                    order_confirmation_number=clean_str(row.get("Order Confirmation Number")),
                    team_commission=team_comm,
                    order_confirmations=clean_str(row.get("Order Confirmations.")),
                    delivery_term=clean_str(row.get("Delivery Term")),
                    cargo_x=clean_str(row.get("Cargo-X")),
                    delay_penalty=clean_str(row.get("Delay Penalty")),
                    delivery_period=clean_str(row.get("Delivery Period")),
                    expected_delivery_date=clean_date(row.get("Expected Delivery Date")),
                    performance_bond_guarantee=clean_str(row.get("Performance Bond Guarantee")),
                    payment_method=clean_str(row.get("Payment method")),
                    payment_status=clean_str(row.get("Payment Status")),
                    source_sheet=sheet
                )
                db.add(order)
                db.commit()

                comments_text = clean_str(row.get("Comments", ""))
                if comments_text:
                    comment_lines = [c.strip() for c in comments_text.split('\n') if c.strip()]
                    for line in comment_lines:
                        comment = Comment(
                            inquiry_id=inquiry.id,
                            content=line,
                            created_at=datetime.utcnow()
                        )
                        db.add(comment)
                    db.commit()

                # Add log
                log = ActivityLog(
                    inquiry_id=inquiry.id,
                    action=f"Imported Order details from Excel '{sheet}' sheet",
                    timestamp=datetime.utcnow()
                )
                db.add(log)
                db.commit()
        
        print("Import completed successfully!")
    finally:
        db.close()

def export_to_excel():
    db = SessionLocal()
    try:
        # Load existing workbook to preserve non-data elements if possible
        wb = openpyxl.load_workbook(EXCEL_PATH)
        
        # 1. Export Inquiries Sheets
        inquiries_sheets = {
            "Inquires": "Active",
            "Declined Inquiries": "Declined",
            "Lost Inquiries": "Lost"
        }

        for sheet_name, status in inquiries_sheets.items():
            if sheet_name not in wb.sheetnames:
                wb.create_sheet(sheet_name)
            ws = wb[sheet_name]
            
            # Clear old data starting from row 9
            # Keep rows 1-8 (headers and formatting)
            max_r = ws.max_row
            if max_r >= 9:
                # Unmerge any merged cells in the data zone first
                merged_ranges_to_remove = [
                    mr for mr in list(ws.merged_cells.ranges)
                    if mr.min_row >= 9
                ]
                for mr in merged_ranges_to_remove:
                    ws.unmerge_cells(str(mr))
                # Now safely clear cell values
                for row in range(9, max_r + 1):
                    for col in range(1, ws.max_column + 1):
                        cell = ws.cell(row=row, column=col)
                        try:
                            cell.value = None
                        except AttributeError:
                            pass  # skip any remaining merged shadow cells

            # Fetch active/relevant records
            records = db.query(Inquiry).filter(
                Inquiry.status == status,
                Inquiry.is_deleted == False
            ).all()

            for r_idx, req in enumerate(records, 9):
                # Format comments timeline into a single newline-separated block
                comments_text = "\n".join([c.content for c in req.comments])
                
                ws.cell(row=r_idx, column=1, value=req.inquiry_date)
                ws.cell(row=r_idx, column=2, value=req.last_update)
                ws.cell(row=r_idx, column=3, value=req.due_date)
                ws.cell(row=r_idx, column=4, value=req.principal.name if req.principal else "")
                ws.cell(row=r_idx, column=5, value=req.client.name if req.client else "")
                ws.cell(row=r_idx, column=6, value=req.inquiry_reference)
                ws.cell(row=r_idx, column=7, value=req.quotation_reference)
                ws.cell(row=r_idx, column=8, value=req.value)
                ws.cell(row=r_idx, column=9, value=req.submission_method)
                ws.cell(row=r_idx, column=10, value=req.status if status == "Active" else status)
                ws.cell(row=r_idx, column=11, value=req.bid_bond_value)
                ws.cell(row=r_idx, column=12, value=req.performance_bond)
                ws.cell(row=r_idx, column=13, value=req.quotation_validity)
                ws.cell(row=r_idx, column=14, value=req.expiration_date)
                ws.cell(row=r_idx, column=15, value=req.contact_person)
                ws.cell(row=r_idx, column=16, value=comments_text)

        # 2. Export Order Sheets
        order_sheets = ["Orders", "LESER's Orders", " Bartec Orders", " Bartec Orders 2025"]
        for sheet_name in order_sheets:
            if sheet_name not in wb.sheetnames:
                wb.create_sheet(sheet_name)
            ws = wb[sheet_name]
            
            # Clear old data starting from row 8
            max_r = ws.max_row
            if max_r >= 8:
                merged_ranges_to_remove = [
                    mr for mr in list(ws.merged_cells.ranges)
                    if mr.min_row >= 8
                ]
                for mr in merged_ranges_to_remove:
                    ws.unmerge_cells(str(mr))
                for row in range(8, max_r + 1):
                    for col in range(1, ws.max_column + 1):
                        cell = ws.cell(row=row, column=col)
                        try:
                            cell.value = None
                        except AttributeError:
                            pass

            # Fetch orders belonging to this sheet
            orders = db.query(Order).join(Inquiry).filter(
                Inquiry.status == "Won",
                Inquiry.is_deleted == False,
                Order.source_sheet == sheet_name
            ).all()

            for r_idx, o in enumerate(orders, 8):
                comments_text = "\n".join([c.content for c in o.inquiry.comments])
                
                # Check columns list to handle LESER's Orders differences
                ws.cell(row=r_idx, column=1, value=o.inquiry.client.name if o.inquiry.client else "")
                ws.cell(row=r_idx, column=2, value=o.inquiry.principal.name if o.inquiry.principal else "")
                ws.cell(row=r_idx, column=3, value=o.inquiry.inquiry_date)
                ws.cell(row=r_idx, column=4, value=o.inquiry.inquiry_reference)
                ws.cell(row=r_idx, column=5, value=o.inquiry.quotation_reference)
                ws.cell(row=r_idx, column=6, value=o.order_number)
                ws.cell(row=r_idx, column=7, value=o.order_date)
                ws.cell(row=r_idx, column=8, value=o.order_value)
                ws.cell(row=r_idx, column=9, value=o.additionals)
                
                if sheet_name == "LESER's Orders":
                    ws.cell(row=r_idx, column=10, value=o.total_order_value) # Total Price
                    ws.cell(row=r_idx, column=11, value=o.order_confirmation_number)
                    ws.cell(row=r_idx, column=12, value=o.order_confirmations)
                    ws.cell(row=r_idx, column=13, value=o.delivery_term)
                    ws.cell(row=r_idx, column=14, value=o.cargo_x)
                    ws.cell(row=r_idx, column=15, value=o.delay_penalty)
                    ws.cell(row=r_idx, column=16, value=o.delivery_period)
                    ws.cell(row=r_idx, column=17, value=o.expected_delivery_date)
                    ws.cell(row=r_idx, column=18, value="") # Days until delivery date (formula/empty)
                    ws.cell(row=r_idx, column=19, value=o.performance_bond_guarantee)
                    ws.cell(row=r_idx, column=20, value=o.payment_method)
                    ws.cell(row=r_idx, column=21, value=o.payment_status)
                    ws.cell(row=r_idx, column=22, value=comments_text)
                else:
                    ws.cell(row=r_idx, column=10, value=o.total_order_value) # Total Order Value
                    ws.cell(row=r_idx, column=11, value=o.order_confirmation_number)
                    ws.cell(row=r_idx, column=12, value=o.team_commission)
                    ws.cell(row=r_idx, column=13, value=o.order_confirmations)
                    ws.cell(row=r_idx, column=14, value=o.delivery_term)
                    ws.cell(row=r_idx, column=15, value=o.cargo_x)
                    ws.cell(row=r_idx, column=16, value=o.delay_penalty)
                    ws.cell(row=r_idx, column=17, value=o.delivery_period)
                    ws.cell(row=r_idx, column=18, value=o.expected_delivery_date)
                    ws.cell(row=r_idx, column=19, value="") # Days until delivery
                    ws.cell(row=r_idx, column=20, value=o.performance_bond_guarantee)
                    ws.cell(row=r_idx, column=21, value=o.payment_method)
                    ws.cell(row=r_idx, column=22, value=o.payment_status)
                    ws.cell(row=r_idx, column=23, value=comments_text)

        wb.save(EXCEL_PATH)
        print("Excel sync completed successfully!")
        return True
    except Exception as e:
        print("Error exporting to Excel:", e)
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    # Test importing
    import_from_excel()
