"""
JDK Smart Factory Platform — Inventory Routes
Manage raw materials, finished goods, and suppliers.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import (
    RawMaterial, RawMaterialInventory, FinishedGoodsInventory,
    Supplier, Product, User
)
from ..schemas import (
    RawMaterialCreate, RawMaterialResponse, RawMaterialUpdate,
    RawMaterialInventoryUpdate, FinishedGoodsInventoryUpdate,
    FinishedGoodsInventoryResponse, SupplierCreate, SupplierResponse, SupplierUpdate
)
from ..security import get_current_user, require_role

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# Raw Materials
@router.get("/materials", response_model=List[RawMaterialResponse])
async def list_materials(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all raw materials."""
    return db.query(RawMaterial).offset(skip).limit(limit).all()


@router.post("/materials", response_model=RawMaterialResponse)
async def create_material(
    material_data: RawMaterialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin", "Warehouse User")),
):
    """Create a new raw material with inventory."""
    existing = db.query(RawMaterial).filter(
        RawMaterial.material_name == material_data.material_name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Material already exists",
        )
    
    # Create material
    material = RawMaterial(
        material_name=material_data.material_name,
        unit=material_data.unit,
    )
    db.add(material)
    db.flush()
    
    # Create inventory record
    inv = RawMaterialInventory(
        material_id=material.id,
        current_stock=material_data.current_stock,
        reorder_point=material_data.reorder_point,
        minimum_stock=material_data.minimum_stock,
        lead_time_days=material_data.lead_time_days,
    )
    db.add(inv)
    db.commit()
    db.refresh(material)
    
    return material


@router.put("/materials/{material_id}", response_model=RawMaterialResponse)
async def update_material(
    material_id: int,
    material_data: RawMaterialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin", "Warehouse User")),
):
    """Update a raw material."""
    material = db.query(RawMaterial).filter(RawMaterial.id == material_id).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found",
        )
    
    update_data = material_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(material, field, value)
    
    db.commit()
    db.refresh(material)
    return material


@router.put("/materials/{material_id}/inventory", response_model=dict)
async def update_inventory(
    material_id: int,
    inv_data: RawMaterialInventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin", "Warehouse User")),
):
    """Update raw material inventory levels."""
    inv = db.query(RawMaterialInventory).filter(
        RawMaterialInventory.material_id == material_id
    ).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found",
        )
    
    update_data = inv_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(inv, field, value)
    
    db.commit()
    return {"message": "Inventory updated successfully"}


# Finished Goods
@router.get("/finished-goods", response_model=List[FinishedGoodsInventoryResponse])
async def list_finished_goods(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all finished goods inventory."""
    return db.query(FinishedGoodsInventory).all()


@router.put("/finished-goods/{product_id}", response_model=FinishedGoodsInventoryResponse)
async def update_finished_goods(
    product_id: int,
    inv_data: FinishedGoodsInventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin", "Warehouse User")),
):
    """Update finished goods inventory."""
    inv = db.query(FinishedGoodsInventory).filter(
        FinishedGoodsInventory.product_id == product_id
    ).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finished goods inventory not found",
        )
    
    update_data = inv_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(inv, field, value)
    
    db.commit()
    db.refresh(inv)
    return inv


# Suppliers
@router.get("/suppliers", response_model=List[SupplierResponse])
async def list_suppliers(
    material_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all suppliers, optionally filtered by material."""
    query = db.query(Supplier)
    if material_id:
        query = query.filter(Supplier.material_id == material_id)
    return query.all()


@router.post("/suppliers", response_model=SupplierResponse)
async def create_supplier(
    supplier_data: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin", "Purchasing User")),
):
    """Create a new supplier."""
    # Verify material exists
    material = db.query(RawMaterial).filter(
        RawMaterial.id == supplier_data.material_id
    ).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found",
        )
    
    new_supplier = Supplier(**supplier_data.model_dump())
    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)
    return new_supplier


@router.put("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: int,
    supplier_data: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin", "Purchasing User")),
):
    """Update a supplier."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
        )
    
    update_data = supplier_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)
    
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/suppliers/{supplier_id}")
async def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin")),
):
    """Delete a supplier (Soft delete)."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
        )
    
    supplier.is_active = False
    db.commit()
    return {"message": "Supplier deactivated successfully"}
