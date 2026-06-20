"""
JDK Smart Factory Platform — MRP/ATP Routes
Run MRP calculations and get feasibility reports.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import CustomerOrder, User
from ..schemas import MRPResult, OrderFeasibilityRow, MaterialRequirementRow
from ..security import get_current_user, require_role
from ..mrp_engine import MRPEngine

router = APIRouter(prefix="/mrp", tags=["MRP"])


@router.get("/run", response_model=MRPResult)
async def run_mrp(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin", "Production Planner")),
):
    """
    Run MRP calculation for all active orders.
    
    Returns order feasibility, material requirements, and reorder alerts.
    """
    engine = MRPEngine(db)
    result = engine.run_fulfillment_mrp()
    
    # Convert to schema models
    order_feasibility = [
        OrderFeasibilityRow(**row) for row in result["order_feasibility"]
    ]
    material_detail = [
        MaterialRequirementRow(**row) for row in result["material_detail"]
    ]
    
    return MRPResult(
        order_feasibility=order_feasibility,
        material_detail=material_detail,
        summary_requirement=result["summary_requirement"],
        reorder_alerts=result["reorder_alerts"],
    )


@router.get("/orders/{order_id}/feasibility")
async def get_order_feasibility(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get feasibility analysis for a specific order."""
    order = db.query(CustomerOrder).filter(CustomerOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    engine = MRPEngine(db)
    summary, materials = engine.feasibility_single_order(order)
    
    return {
        "summary": summary,
        "materials": materials,
    }


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard statistics."""
    from ..models import Customer, Product, RawMaterialInventory
    
    # Count orders by status
    total_orders = db.query(CustomerOrder).count()
    active_orders = db.query(CustomerOrder).filter(
        CustomerOrder.status.notin_(["Shipped", "Closed", "Cancelled"])
    ).count()
    
    orders_ready = db.query(CustomerOrder).filter(
        CustomerOrder.status == "Ready For Shipment"
    ).count()
    
    orders_in_production = db.query(CustomerOrder).filter(
        CustomerOrder.status.in_(["In Production", "Production Planned"])
    ).count()
    
    # Count material shortages (inventory below minimum)
    low_stock = db.query(RawMaterialInventory).filter(
        RawMaterialInventory.current_stock <= RawMaterialInventory.minimum_stock
    ).count()
    
    return {
        "total_orders": total_orders,
        "active_orders": active_orders,
        "orders_ready": orders_ready,
        "orders_in_production": orders_in_production,
        "material_shortages": low_stock,
        "low_stock_materials": low_stock,
        "total_customers": db.query(Customer).count(),
        "total_products": db.query(Product).count(),
    }
