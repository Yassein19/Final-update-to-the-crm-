from pydantic import BaseModel, Field
from typing import Optional, List, Dict
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
    currency: Optional[str] = "USD"
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
    payment_status: Optional[str] = "Under Payment"
    order_status: Optional[str] = "Under Approval"
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
    currency: Optional[str] = "USD"
    offer_type: Optional[str] = "Firm"
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
    total_value_active_usd: float
    total_value_active_eur: float
    total_value_won_usd: float
    total_value_won_eur: float
    total_value_lost_usd: float
    total_value_lost_eur: float
    due_this_week_alerts: List[InquiryOut]
    near_delivery_alerts: List[InquiryOut]

class ValueBreakdown(BaseModel):
    usd: float = 0.0
    eur: float = 0.0

class CategoryStats(BaseModel):
    count: int = 0
    values: ValueBreakdown = ValueBreakdown()

class CategoryDetailItem(BaseModel):
    name: str
    count: int = 0
    percentage: float = 0.0
    usd_value: float = 0.0
    eur_value: float = 0.0

class CategoryDetailView(BaseModel):
    category_name: str
    total_count: int = 0
    total_usd: float = 0.0
    total_eur: float = 0.0
    principal_breakdown: List[CategoryDetailItem] = []
    monthly_frequency: Dict[str, int] = {}

class AnnualReportData(BaseModel):
    year: str
    # 1) Dashboard: overall view
    tenders_total: CategoryStats
    tenders_cancelled: CategoryStats
    tenders_declined: CategoryStats
    tenders_firm: CategoryStats
    tenders_budgetary: CategoryStats
    
    submitted_lost: CategoryStats
    submitted_ongoing: CategoryStats
    submitted_awarded: CategoryStats
    
    orders_under_production: CategoryStats
    orders_shipped: CategoryStats
    orders_paid: CategoryStats
    orders_due_payment: CategoryStats
    
    # 2) Distribution for Pie Chart
    chart_distribution: dict
    category_views: Optional[Dict[str, CategoryDetailView]] = None

# --- BUSINESS INTELLIGENCE & ANALYTICS SCHEMAS ---

class CompanyKPIs(BaseModel):
    win_rate: float = 0.0
    avg_inquiry_val_usd: float = 0.0
    avg_inquiry_val_eur: float = 0.0
    avg_order_val_usd: float = 0.0
    avg_order_val_eur: float = 0.0
    avg_sales_cycle_days: float = 0.0
    pipeline_value_usd: float = 0.0
    pipeline_value_eur: float = 0.0
    total_inquiries: int = 0
    active_inquiries: int = 0
    won_orders: int = 0
    lost_inquiries: int = 0
    declined_inquiries: int = 0

class CompanyReportData(BaseModel):
    company_id: int
    company_name: str
    company_type: str = "Client"  # "Client" or "Principal"
    kpis: CompanyKPIs
    inquiry_trend: dict = {}
    principal_performance: List[dict] = []
    largest_orders: List[dict] = []
    most_active_principal: str = "N/A"
    inquiries: List[InquiryOut] = []
    ai_executive_summary: str = ""

class MetricComparison(BaseModel):
    current: float = 0.0
    previous: float = 0.0
    change_pct: float = 0.0
    direction: str = "flat"  # "up", "down", "flat"

class ComparisonAnalyticsData(BaseModel):
    period: str  # "Daily", "Weekly", "Monthly", "Yearly"
    current_label: str
    previous_label: str
    metrics: dict  # Metric -> MetricComparison
    natural_explanation: str

class SalesAnalyticsData(BaseModel):
    daily: dict = {}
    weekly: dict = {}
    monthly: dict = {}
    yearly: dict = {}
    insights: List[str] = []

class TimeSeriesData(BaseModel):
    period_type: str  # "Daily", "Weekly", "Monthly", "Quarterly", "Yearly"
    labels: List[str] = []
    inquiries_count: List[int] = []
    won_orders_count: List[int] = []
    pipeline_usd: List[float] = []
    pipeline_eur: List[float] = []
    win_rate: List[float] = []
    avg_sales_cycle_days: List[float] = []

