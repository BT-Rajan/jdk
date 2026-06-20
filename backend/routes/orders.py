"""
JDK Smart Factory Platform — Order Routes
CRUD operations for customer orders.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import CustomerOrder, Customer, Product, User
from ..schemas import OrderCreate, OrderResponse, OrderUpdate, OrderWithDetailsResponse
from ..security import get_current_user, require_role

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=List[OrderResponse])
async def list_orders(
    skip: int = 0,
    limit: int = 100,
    status_filter: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all orders with optional status filter."""
    query = db.query(CustomerOrder)
    if status_filter:
        query = query.filter(CustomerOrder.status == status_filter)
    return query.order_by(CustomerOrder.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin", "Production Planner")),
):
    """Create a new customer order."""
    # Check if order number exists
    existing = db.query(CustomerOrder).filter(
        CustomerOrder.order_no == order_data.order_no
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order number already exists",
        )
    
    # Verify customer exists
    customer = db.query(Customer).filter(Customer.id == order_data.customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    
    # Verify product exists
    product = db.query(Product).filter(Product.id == order_data.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    
    new_order = CustomerOrder(**order_data.model_dump(), created_by=current_user.id)
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order


@router.get("/{order_id}", response_model=OrderWithDetailsResponse)
async def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific order with details."""
    order = db.query(CustomerOrder).filter(CustomerOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    return order


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order_data: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin", "Production Planner")),
):
    """Update an order."""
    order = db.query(CustomerOrder).filter(CustomerOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    update_data = order_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}")
async def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin")),
):
    """Delete an order (Soft delete by setting status to Cancelled)."""
    order = db.query(CustomerOrder).filter(CustomerOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    from ..models import OrderStatusEnum
    order.status = OrderStatusEnum.CANCELLED
    db.commit()
    return {"message": "Order cancelled successfully"}
