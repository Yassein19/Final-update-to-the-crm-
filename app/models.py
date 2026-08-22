from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    inquiries = relationship("Inquiry", back_populates="client")

class Principal(Base):
    __tablename__ = "principals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    inquiries = relationship("Inquiry", back_populates="principal")

class Inquiry(Base):
    __tablename__ = "inquiries"
    id = Column(Integer, primary_key=True, index=True)
    inquiry_date = Column(String, nullable=True)
    last_update = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    
    principal_id = Column(Integer, ForeignKey("principals.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    
    inquiry_reference = Column(Text, nullable=True)
    quotation_reference = Column(Text, nullable=True)
    value = Column(Float, nullable=True)
    currency = Column(String, nullable=False, default="USD") # USD, EUR, EGP
    offer_type = Column(String, nullable=False, default="Firm") # Firm, Budgetary
    submission_method = Column(String, nullable=True)
    status = Column(String, nullable=False, default="Active") # Active, Order, Lost, Declined
    
    bid_bond_value = Column(String, nullable=True)
    performance_bond = Column(String, nullable=True)
    quotation_validity = Column(String, nullable=True)
    expiration_date = Column(String, nullable=True)
    contact_person = Column(String, nullable=True)
    
    is_deleted = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    client = relationship("Client", back_populates="inquiries")
    principal = relationship("Principal", back_populates="inquiries")
    order = relationship("Order", back_populates="inquiry", uselist=False, cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="inquiry", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="inquiry", cascade="all, delete-orphan")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, ForeignKey("inquiries.id"), primary_key=True)
    order_number = Column(String, nullable=True)
    order_date = Column(String, nullable=True)
    order_value = Column(Float, nullable=True)
    additionals = Column(Float, nullable=True)
    total_order_value = Column(Float, nullable=True)
    currency = Column(String, nullable=False, default="USD") # USD, EUR, EGP
    order_confirmation_number = Column(String, nullable=True)
    team_commission = Column(String, nullable=True)
    order_confirmations = Column(Text, nullable=True)
    delivery_term = Column(String, nullable=True)
    cargo_x = Column(String, nullable=True)
    delay_penalty = Column(String, nullable=True)
    delivery_period = Column(String, nullable=True)
    expected_delivery_date = Column(String, nullable=True)
    performance_bond_guarantee = Column(String, nullable=True)
    payment_method = Column(String, nullable=True)
    payment_status = Column(String, nullable=True, default="Under Payment") # Payment Submitted, Paid, Under Payment
    order_status = Column(String, nullable=False, default="Under Approval") # Under Approval, Under Production, Under Shipping, Shipped, Under Payment
    source_sheet = Column(String, nullable=False, default="Orders") # Orders, LESER's Orders, etc.

    # Relationships
    inquiry = relationship("Inquiry", back_populates="order")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    inquiry_id = Column(Integer, ForeignKey("inquiries.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    inquiry = relationship("Inquiry", back_populates="comments")

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    inquiry_id = Column(Integer, ForeignKey("inquiries.id"), nullable=False)
    action = Column(String, nullable=False) # e.g., "Created", "Status changed to Won", "Updated"
    timestamp = Column(DateTime, default=datetime.utcnow)

    inquiry = relationship("Inquiry", back_populates="activity_logs")
