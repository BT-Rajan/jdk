"""
JDK Smart Factory Platform — Product Routes
CRUD operations for products and formulas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Product, ProductFormula, RawMaterial, FinishedGoodsInventory, User
from ..schemas import (
    ProductCreate, ProductResponse, ProductUpdate,
    ProductFormulaCreate, ProductFormulaResponse
)
from ..security import get_current_user, require_role

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=List[ProductResponse])
async def list_products(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all products."""
    query = db.query(Product)
    if active_only:
        query = query.filter(Product.is_active == True)
    return query.offset(skip).limit(limit).all()


@router.post("", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin", "Production Planner")),
):
    """Create a new product."""
    existing = db.query(Product).filter(
        Product.product_name == product_data.product_name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product with this name already exists",
        )
    
    new_product = Product(**product_data.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    # Create empty finished goods inventory
    fg_inv = FinishedGoodsInventory(product_id=new_product.id)
    db.add(fg_inv)
    db.commit()
    
    return new_product


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin", "Production Planner")),
):
    """Update a product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin")),
):
    """Delete a product (Soft delete)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    
    product.is_active = False
    db.commit()
    return {"message": "Product deactivated successfully"}


# Formula endpoints
@router.get("/{product_id}/formulas", response_model=List[ProductFormulaResponse])
async def list_formulas(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all formulas for a product."""
    return db.query(ProductFormula).filter(
        ProductFormula.product_id == product_id
    ).all()


@router.post("/{product_id}/formulas", response_model=ProductFormulaResponse)
async def create_formula(
    product_id: int,
    formula_data: ProductFormulaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin", "Production Planner")),
):
    """Add a formula component to a product."""
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    
    # Verify material exists
    material = db.query(RawMaterial).filter(
        RawMaterial.id == formula_data.material_id
    ).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Raw material not found",
        )
    
    new_formula = ProductFormula(**formula_data.model_dump())
    db.add(new_formula)
    db.commit()
    db.refresh(new_formula)
    return new_formula


@router.delete("/{product_id}/formulas/{formula_id}")
async def delete_formula(
    product_id: int,
    formula_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Super Admin", "Production Planner")),
):
    """Remove a formula component from a product."""
    formula = db.query(ProductFormula).filter(
        ProductFormula.id == formula_id,
        ProductFormula.product_id == product_id
    ).first()
    if not formula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Formula not found",
        )
    
    db.delete(formula)
    db.commit()
    return {"message": "Formula removed successfully"}
