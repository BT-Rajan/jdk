"""
JDK Smart Factory Platform — Pydantic Schemas
Request/response models for API endpoints.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


# Enums matching database models
class RoleEnum(str, Enum):
    SUPER_ADMIN = "Super Admin"
    PRODUCTION_PLANNER = "Production Planner"
    WAREHOUSE_USER = "Warehouse User"
    PURCHASING_USER = "Purchasing User"
    MANAGEMENT_VIEWER = "Management Viewer"


class PriorityEnum(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    NORMAL = "Normal"
    LOW = "Low"


class OrderStatusEnum(str, Enum):
    OPEN = "Open"
    APPROVED = "Approved"
    PRODUCTION_PLANNED = "Production Planned"
    IN_PRODUCTION = "In Production"
    READY_FOR_SHIPMENT = "Ready For Shipment"
    SHIPPED = "Shipped"
    CLOSED = "Closed"
    CANCELLED = "Cancelled"


# Auth schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=100)
    role: RoleEnum = RoleEnum.MANAGEMENT_VIEWER


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    display_name: Optional[str] = None
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str
    password: str


# Customer schemas
class CustomerBase(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=100)
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    id: int
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Product schemas
class ProductBase(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    default_bag_size_kg: float = 25.0


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    description: Optional[str] = None
    default_bag_size_kg: Optional[float] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    id: int
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Raw Material schemas
class RawMaterialBase(BaseModel):
    material_name: str = Field(..., min_length=1, max_length=100)
    unit: str = Field(..., pattern="^(bags|kg|tons)$")


class RawMaterialCreate(RawMaterialBase):
    current_stock: float = 0.0
    reorder_point: float = 0.0
    minimum_stock: float = 0.0
    lead_time_days: int = 7


class RawMaterialUpdate(BaseModel):
    unit: Optional[str] = None
    is_active: Optional[bool] = None


class RawMaterialInventoryUpdate(BaseModel):
    current_stock: Optional[float] = None
    reorder_point: Optional[float] = None
    minimum_stock: Optional[float] = None
    lead_time_days: Optional[int] = None


class RawMaterialResponse(RawMaterialBase):
    id: int
    is_active: bool
    created_at: datetime
    inventory: Optional["RawMaterialInventoryResponse"] = None
    
    model_config = ConfigDict(from_attributes=True)


class RawMaterialInventoryResponse(BaseModel):
    id: int
    material_id: int
    current_stock: float
    reorder_point: float
    minimum_stock: float
    lead_time_days: int
    last_updated: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Finished Goods Inventory schemas
class FinishedGoodsInventoryBase(BaseModel):
    product_id: int
    available_kg: float = 0.0
    reserved_kg: float = 0.0


class FinishedGoodsInventoryUpdate(BaseModel):
    available_kg: Optional[float] = None
    reserved_kg: Optional[float] = None


class FinishedGoodsInventoryResponse(FinishedGoodsInventoryBase):
    id: int
    last_updated: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Product Formula schemas
class ProductFormulaBase(BaseModel):
    product_id: int
    material_id: int
    percentage: float = Field(..., gt=0, le=100)


class ProductFormulaCreate(ProductFormulaBase):
    pass


class ProductFormulaResponse(ProductFormulaBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)


# Supplier schemas
class SupplierBase(BaseModel):
    material_id: int
    supplier_name: str = Field(..., min_length=1, max_length=100)
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    price_per_unit: float = Field(..., gt=0)
    lead_time_days: int = 7
    is_preferred: bool = False


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    price_per_unit: Optional[float] = None
    lead_time_days: Optional[int] = None
    is_preferred: Optional[bool] = None
    is_active: Optional[bool] = None


class SupplierResponse(SupplierBase):
    id: int
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Order schemas
class OrderBase(BaseModel):
    order_no: str = Field(..., min_length=1, max_length=20)
    customer_id: int
    product_id: int
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., pattern="^(bags|kg|tons)$")
    bag_size_kg: float = 25.0
    priority: PriorityEnum = PriorityEnum.NORMAL
    status: OrderStatusEnum = OrderStatusEnum.OPEN
    delivery_date: date
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    quantity: Optional[float] = None
    priority: Optional[PriorityEnum] = None
    status: Optional[OrderStatusEnum] = None
    delivery_date: Optional[date] = None
    notes: Optional[str] = None
    reserved_fg_kg: Optional[float] = None


class OrderResponse(OrderBase):
    id: int
    reserved_fg_kg: float
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class OrderWithDetailsResponse(OrderResponse):
    customer: Optional[CustomerResponse] = None
    product: Optional[ProductResponse] = None


# MRP/ATP Result schemas
class MaterialRequirementRow(BaseModel):
    material: str
    required_qty: float
    current_stock: float
    shortage_qty: float
    lead_time_days: int
    unit_price: Optional[float] = None
    status: str


class OrderFeasibilityRow(BaseModel):
    order_no: str
    product: str
    customer: str
    priority: str
    order_qty: float
    unit: str
    feasibility_status: str
    raw_materials_available: str
    estimated_production_days: int
    earliest_delivery_date: str
    estimated_material_cost: float


class MRPResult(BaseModel):
    order_feasibility: List[OrderFeasibilityRow]
    material_detail: List[MaterialRequirementRow]
    summary_requirement: List[dict]
    reorder_alerts: List[dict]


# Dashboard stats
class DashboardStats(BaseModel):
    total_orders: int
    active_orders: int
    orders_ready: int
    orders_in_production: int
    material_shortages: int
    low_stock_materials: int
    total_customers: int
    total_products: int


# Update forward references
RawMaterialResponse.model_rebuild()
