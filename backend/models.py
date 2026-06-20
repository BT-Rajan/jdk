"""
JDK Smart Factory Platform — Database Models
SQLAlchemy ORM models for all entities.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Date, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .database import Base


class RoleEnum(str, enum.Enum):
    SUPER_ADMIN = "Super Admin"
    PRODUCTION_PLANNER = "Production Planner"
    WAREHOUSE_USER = "Warehouse User"
    PURCHASING_USER = "Purchasing User"
    MANAGEMENT_VIEWER = "Management Viewer"


class PriorityEnum(str, enum.Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    NORMAL = "Normal"
    LOW = "Low"


class OrderStatusEnum(str, enum.Enum):
    OPEN = "Open"
    APPROVED = "Approved"
    PRODUCTION_PLANNED = "Production Planned"
    IN_PRODUCTION = "In Production"
    READY_FOR_SHIPMENT = "Ready For Shipment"
    SHIPPED = "Shipped"
    CLOSED = "Closed"
    CANCELLED = "Cancelled"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=False)
    role = Column(SQLEnum(RoleEnum), nullable=False, default=RoleEnum.MANAGEMENT_VIEWER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    orders_created = relationship("CustomerOrder", back_populates="created_by_user", foreign_keys="CustomerOrder.created_by")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="refresh_tokens")


class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), unique=True, nullable=False)
    contact_person = Column(String(100))
    email = Column(String(120))
    phone = Column(String(20))
    address = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    orders = relationship("CustomerOrder", back_populates="customer_rel", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    default_bag_size_kg = Column(Float, default=25.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    formulas = relationship("ProductFormula", back_populates="product_rel", cascade="all, delete-orphan")
    orders = relationship("CustomerOrder", back_populates="product_rel", cascade="all, delete-orphan")
    finished_goods = relationship("FinishedGoodsInventory", back_populates="product_rel", cascade="all, delete-orphan")


class RawMaterial(Base):
    __tablename__ = "raw_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    material_name = Column(String(100), unique=True, nullable=False)
    unit = Column(String(20), nullable=False)  # kg, bags, tons
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    inventory = relationship("RawMaterialInventory", back_populates="material_rel", uselist=False, cascade="all, delete-orphan")
    suppliers = relationship("Supplier", back_populates="material_rel", cascade="all, delete-orphan")
    formulas = relationship("ProductFormula", back_populates="material_rel", cascade="all, delete-orphan")


class RawMaterialInventory(Base):
    __tablename__ = "raw_material_inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("raw_materials.id", ondelete="CASCADE"), unique=True, nullable=False)
    current_stock = Column(Float, default=0.0)
    reorder_point = Column(Float, default=0.0)
    minimum_stock = Column(Float, default=0.0)
    lead_time_days = Column(Integer, default=7)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    material_rel = relationship("RawMaterial", back_populates="inventory")


class FinishedGoodsInventory(Base):
    __tablename__ = "finished_goods_inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False)
    available_kg = Column(Float, default=0.0)
    reserved_kg = Column(Float, default=0.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    product_rel = relationship("Product", back_populates="finished_goods")


class ProductFormula(Base):
    __tablename__ = "product_formulas"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    material_id = Column(Integer, ForeignKey("raw_materials.id", ondelete="CASCADE"), nullable=False)
    percentage = Column(Float, nullable=False)  # Percentage of this material in the formula
    
    product_rel = relationship("Product", back_populates="formulas")
    material_rel = relationship("RawMaterial", back_populates="formulas")


class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("raw_materials.id", ondelete="CASCADE"), nullable=False)
    supplier_name = Column(String(100), nullable=False)
    contact_person = Column(String(100))
    email = Column(String(120))
    phone = Column(String(20))
    price_per_unit = Column(Float, nullable=False)
    lead_time_days = Column(Integer, default=7)
    is_preferred = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    material_rel = relationship("RawMaterial", back_populates="suppliers")


class CustomerOrder(Base):
    __tablename__ = "customer_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(20), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)  # bags, kg, tons
    bag_size_kg = Column(Float, default=25.0)
    priority = Column(SQLEnum(PriorityEnum), default=PriorityEnum.NORMAL)
    status = Column(SQLEnum(OrderStatusEnum), default=OrderStatusEnum.OPEN)
    delivery_date = Column(Date, nullable=False)
    reserved_fg_kg = Column(Float, default=0.0)
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    customer_rel = relationship("Customer", back_populates="orders")
    product_rel = relationship("Product", back_populates="orders")
    created_by_user = relationship("User", foreign_keys=[created_by], back_populates="orders_created")
