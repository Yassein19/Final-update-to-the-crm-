from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ClientBase(BaseModel):
    name: str

class ClientCreate(ClientBase):
    pass

class ClientOut(ClientBase):
    id: int
    class Config:
        from_attributes = True

class PrincipalBase(BaseModel):
    name: str

class PrincipalCreate(PrincipalBase):
    pass

class PrincipalOut(PrincipalBase):
    id: int
    class Config:
        from_attributes = True

class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    pass

class CommentOut(CommentBase):
    id: int
    inquiry_id: int
    created_at: datetime
    class Config:
        from_attributes = True

class ActivityLogOut(BaseModel):
    id: int
    inquiry_id: int
    action: str
    timestamp: datetime
    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    order_number: Optional[str] = ""
    order_date: Optional[str] = ""
    order_value: Optional[float] = 0.0
    additionals: Optional[float] = 0.0
    total_order_value: Optional[float] = 0.0
    order_confirmation_number: Optional[str] = ""
    team_commission: Optional[str] = ""
    order_confirmations: Optional[str] = ""
    delivery_term: Optional[str] = ""
    cargo_x: Optional[str] = ""
    delay_penalty: Optional[str] = ""
    delivery_period: Optional[str] = ""
    expected_delivery_date: Optional[str] = ""
    performance_bond_guarantee: Optional[str] = ""
    payment_method: Optional[str] = ""
    payment_status: Optional[str] = ""
    source_sheet: Optional[str] = "Orders"

class OrderCreate(OrderBase):
    pass

class OrderOut(OrderBase):
    id: int
    class Config:
        from_attributes = True

class InquiryBase(BaseModel):
    inquiry_date: Optional[str] = ""
    last_update: Optional[str] = ""
    due_date: Optional[str] = ""
    inquiry_reference: Optional[str] = ""
    quotation_reference: Optional[str] = ""
    value: Optional[float] = 0.0
    submission_method: Optional[str] = ""
    status: Optional[str] = "Active"
    bid_bond_value: Optional[str] = ""
    performance_bond: Optional[str] = ""
    quotation_validity: Optional[str] = ""
    expiration_date: Optional[str] = ""
    contact_person: Optional[str] = ""

class InquiryCreate(InquiryBase):
    client_name: str
    principal_name: str

class InquiryUpdate(InquiryBase):
    client_name: Optional[str] = None
    principal_name: Optional[str] = None

class InquiryOut(InquiryBase):
    id: int
    client: Optional[ClientOut] = None
    principal: Optional[PrincipalOut] = None
    is_deleted: bool
    comments: List[CommentOut] = []
    order: Optional[OrderOut] = None
    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_inquiries: int
    active_inquiries: int
    won_inquiries: int
    lost_inquiries: int
    declined_inquiries: int
    total_value_active: float
    total_value_won: float
    due_this_week_alerts: List[InquiryOut]
    near_delivery_alerts: List[InquiryOut]
