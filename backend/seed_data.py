"""
JDK Smart Factory Platform — Database Seed Script
Populates the database with test data for all features.
"""

import sys
from datetime import date, timedelta
from passlib.context import CryptContext

# Add parent directory to path
sys.path.insert(0, '.')

from backend.database import engine, Base, SessionLocal
from backend.models import (
    User, RoleEnum, Customer, Product, RawMaterial, RawMaterialInventory,
    FinishedGoodsInventory, ProductFormula, Supplier, CustomerOrder,
    PriorityEnum, OrderStatusEnum
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def seed_database():
    """Seed the database with test data."""
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Check if already seeded
        if db.query(User).count() > 0:
            print("Database already seeded. Skipping...")
            return
        
        print("Seeding database...")
        
        # ─── Users ─────────────────────────────────────────────────────────────
        users_data = [
            {"username": "admin", "email": "admin@jdkfactory.com", "password": "admin123", 
             "display_name": "System Administrator", "role": RoleEnum.SUPER_ADMIN},
            {"username": "planner", "email": "planner@jdkfactory.com", "password": "planner123",
             "display_name": "Production Planner", "role": RoleEnum.PRODUCTION_PLANNER},
            {"username": "warehouse", "email": "warehouse@jdkfactory.com", "password": "warehouse123",
             "display_name": "Warehouse Manager", "role": RoleEnum.WAREHOUSE_USER},
            {"username": "purchase", "email": "purchase@jdkfactory.com", "password": "purchase123",
             "display_name": "Purchasing Agent", "role": RoleEnum.PURCHASING_USER},
            {"username": "viewer", "email": "viewer@jdkfactory.com", "password": "view123",
             "display_name": "Management Viewer", "role": RoleEnum.MANAGEMENT_VIEWER},
        ]
        
        users = {}
        for u in users_data:
            user = User(
                username=u["username"],
                email=u["email"],
                password_hash=hash_password(u["password"]),
                display_name=u["display_name"],
                role=u["role"],
            )
            db.add(user)
            users[u["username"]] = user
        
        db.flush()
        print(f"  Created {len(users)} users")
        
        # ─── Customers ──────────────────────────────────────────────────────────
        customers_data = [
            {"customer_name": "Acme Corporation", "contact_person": "John Smith", 
             "email": "john@acme.com", "phone": "+1-555-0101", "address": "123 Industrial Ave"},
            {"customer_name": "Global Foods Inc", "contact_person": "Sarah Johnson",
             "email": "sarah@globalfoods.com", "phone": "+1-555-0102", "address": "456 Commerce Blvd"},
            {"customer_name": "Tech Manufacturing Ltd", "contact_person": "Mike Chen",
             "email": "mike@techmanuf.com", "phone": "+1-555-0103", "address": "789 Factory Lane"},
            {"customer_name": "Premium Retailers", "contact_person": "Emily Davis",
             "email": "emily@premiumretail.com", "phone": "+1-555-0104", "address": "321 Shopping Center"},
            {"customer_name": "Export Partners LLC", "contact_person": "Robert Wilson",
             "email": "robert@exportpartners.com", "phone": "+1-555-0105", "address": "654 Trade Street"},
        ]
        
        customers = {}
        for c in customers_data:
            customer = Customer(**c)
            db.add(customer)
            customers[c["customer_name"]] = customer
        
        db.flush()
        print(f"  Created {len(customers)} customers")
        
        # ─── Raw Materials ──────────────────────────────────────────────────────
        materials_data = [
            {"material_name": "Base Polymer A", "unit": "kg"},
            {"material_name": "Base Polymer B", "unit": "kg"},
            {"material_name": "Additive X", "unit": "kg"},
            {"material_name": "Additive Y", "unit": "kg"},
            {"material_name": "Colorant Red", "unit": "kg"},
            {"material_name": "Colorant Blue", "unit": "kg"},
            {"material_name": "Stabilizer", "unit": "kg"},
            {"material_name": "Packaging bags", "unit": "bags"},
            {"material_name": "Labeling material", "unit": "bags"},
        ]
        
        materials = {}
        for m in materials_data:
            material = RawMaterial(**m)
            db.add(material)
            materials[m["material_name"]] = material
        
        db.flush()
        
        # ─── Raw Material Inventory ─────────────────────────────────────────────
        inventory_data = [
            {"material_name": "Base Polymer A", "current_stock": 5000, "reorder_point": 1000, "minimum_stock": 500, "lead_time_days": 5},
            {"material_name": "Base Polymer B", "current_stock": 3000, "reorder_point": 800, "minimum_stock": 400, "lead_time_days": 7},
            {"material_name": "Additive X", "current_stock": 500, "reorder_point": 100, "minimum_stock": 50, "lead_time_days": 3},
            {"material_name": "Additive Y", "current_stock": 200, "reorder_point": 100, "minimum_stock": 50, "lead_time_days": 4},
            {"material_name": "Colorant Red", "current_stock": 150, "reorder_point": 50, "minimum_stock": 25, "lead_time_days": 5},
            {"material_name": "Colorant Blue", "current_stock": 80, "reorder_point": 50, "minimum_stock": 25, "lead_time_days": 5},
            {"material_name": "Stabilizer", "current_stock": 300, "reorder_point": 100, "minimum_stock": 50, "lead_time_days": 3},
            {"material_name": "Packaging bags", "current_stock": 2000, "reorder_point": 500, "minimum_stock": 200, "lead_time_days": 2},
            {"material_name": "Labeling material", "current_stock": 1500, "reorder_point": 300, "minimum_stock": 100, "lead_time_days": 3},
        ]
        
        for inv in inventory_data:
            material = materials[inv["material_name"]]
            inv_record = RawMaterialInventory(
                material_id=material.id,
                current_stock=inv["current_stock"],
                reorder_point=inv["reorder_point"],
                minimum_stock=inv["minimum_stock"],
                lead_time_days=inv["lead_time_days"],
            )
            db.add(inv_record)
        
        db.flush()
        print(f"  Created {len(materials)} raw materials with inventory")
        
        # ─── Products ───────────────────────────────────────────────────────────
        products_data = [
            {"product_name": "Premium Compound A", "description": "High-grade polymer compound", "default_bag_size_kg": 25.0},
            {"product_name": "Standard Compound B", "description": "Standard grade polymer", "default_bag_size_kg": 25.0},
            {"product_name": "Specialty Mix C", "description": "Specialty formulation", "default_bag_size_kg": 20.0},
            {"product_name": "Economy Blend D", "description": "Cost-effective blend", "default_bag_size_kg": 25.0},
        ]
        
        products = {}
        for p in products_data:
            product = Product(**p)
            db.add(product)
            products[p["product_name"]] = product
        
        db.flush()
        
        # ─── Finished Goods Inventory ───────────────────────────────────────────
        fg_inventory_data = [
            {"product_name": "Premium Compound A", "available_kg": 2000, "reserved_kg": 500},
            {"product_name": "Standard Compound B", "available_kg": 3500, "reserved_kg": 200},
            {"product_name": "Specialty Mix C", "available_kg": 800, "reserved_kg": 100},
            {"product_name": "Economy Blend D", "available_kg": 5000, "reserved_kg": 0},
        ]
        
        for fg in fg_inventory_data:
            product = products[fg["product_name"]]
            fg_record = FinishedGoodsInventory(
                product_id=product.id,
                available_kg=fg["available_kg"],
                reserved_kg=fg["reserved_kg"],
            )
            db.add(fg_record)
        
        db.flush()
        
        # ─── Product Formulas ───────────────────────────────────────────────────
        formulas_data = [
            # Premium Compound A: 60% Base Polymer A, 20% Base Polymer B, 10% Additive X, 5% Stabilizer, 5% Colorant
            {"product_name": "Premium Compound A", "material_name": "Base Polymer A", "percentage": 60},
            {"product_name": "Premium Compound A", "material_name": "Base Polymer B", "percentage": 20},
            {"product_name": "Premium Compound A", "material_name": "Additive X", "percentage": 10},
            {"product_name": "Premium Compound A", "material_name": "Stabilizer", "percentage": 5},
            {"product_name": "Premium Compound A", "material_name": "Colorant Red", "percentage": 5},
            
            # Standard Compound B: 70% Base Polymer A, 15% Base Polymer B, 10% Additive Y, 5% Stabilizer
            {"product_name": "Standard Compound B", "material_name": "Base Polymer A", "percentage": 70},
            {"product_name": "Standard Compound B", "material_name": "Base Polymer B", "percentage": 15},
            {"product_name": "Standard Compound B", "material_name": "Additive Y", "percentage": 10},
            {"product_name": "Standard Compound B", "material_name": "Stabilizer", "percentage": 5},
            
            # Specialty Mix C: 50% Base Polymer B, 30% Additive X, 15% Additive Y, 5% Colorant Blue
            {"product_name": "Specialty Mix C", "material_name": "Base Polymer B", "percentage": 50},
            {"product_name": "Specialty Mix C", "material_name": "Additive X", "percentage": 30},
            {"product_name": "Specialty Mix C", "material_name": "Additive Y", "percentage": 15},
            {"product_name": "Specialty Mix C", "material_name": "Colorant Blue", "percentage": 5},
            
            # Economy Blend D: 80% Base Polymer A, 15% Additive Y, 5% Stabilizer
            {"product_name": "Economy Blend D", "material_name": "Base Polymer A", "percentage": 80},
            {"product_name": "Economy Blend D", "material_name": "Additive Y", "percentage": 15},
            {"product_name": "Economy Blend D", "material_name": "Stabilizer", "percentage": 5},
        ]
        
        for f in formulas_data:
            product = products[f["product_name"]]
            material = materials[f["material_name"]]
            formula = ProductFormula(
                product_id=product.id,
                material_id=material.id,
                percentage=f["percentage"],
            )
            db.add(formula)
        
        db.flush()
        print(f"  Created {len(products)} products with formulas")
        
        # ─── Suppliers ──────────────────────────────────────────────────────────
        suppliers_data = [
            {"material_name": "Base Polymer A", "supplier_name": "PolymerCorp Industries", "price_per_unit": 2.50, "lead_time_days": 5, "is_preferred": True},
            {"material_name": "Base Polymer A", "supplier_name": "ChemSupply Co", "price_per_unit": 2.75, "lead_time_days": 3, "is_preferred": False},
            {"material_name": "Base Polymer B", "supplier_name": "PolymerCorp Industries", "price_per_unit": 2.20, "lead_time_days": 7, "is_preferred": True},
            {"material_name": "Base Polymer B", "supplier_name": "ResinWorld Ltd", "price_per_unit": 2.35, "lead_time_days": 4, "is_preferred": False},
            {"material_name": "Additive X", "supplier_name": "SpecialtyChem Inc", "price_per_unit": 15.00, "lead_time_days": 3, "is_preferred": True},
            {"material_name": "Additive Y", "supplier_name": "SpecialtyChem Inc", "price_per_unit": 12.50, "lead_time_days": 4, "is_preferred": True},
            {"material_name": "Colorant Red", "supplier_name": "ColorMasters LLC", "price_per_unit": 25.00, "lead_time_days": 5, "is_preferred": True},
            {"material_name": "Colorant Blue", "supplier_name": "ColorMasters LLC", "price_per_unit": 25.00, "lead_time_days": 5, "is_preferred": True},
            {"material_name": "Stabilizer", "supplier_name": "AddiTech Solutions", "price_per_unit": 8.00, "lead_time_days": 3, "is_preferred": True},
            {"material_name": "Packaging bags", "supplier_name": "PackagePro Manufacturing", "price_per_unit": 0.50, "lead_time_days": 2, "is_preferred": True},
            {"material_name": "Packaging bags", "supplier_name": "BagSupply Direct", "price_per_unit": 0.45, "lead_time_days": 4, "is_preferred": False},
            {"material_name": "Labeling material", "supplier_name": "LabelTech Inc", "price_per_unit": 0.30, "lead_time_days": 3, "is_preferred": True},
        ]
        
        for s in suppliers_data:
            material = materials[s["material_name"]]
            supplier = Supplier(
                material_id=material.id,
                supplier_name=s["supplier_name"],
                price_per_unit=s["price_per_unit"],
                lead_time_days=s["lead_time_days"],
                is_preferred=s["is_preferred"],
            )
            db.add(supplier)
        
        db.flush()
        print(f"  Created {len(suppliers_data)} supplier records")
        
        # ─── Customer Orders ────────────────────────────────────────────────────
        today = date.today()
        orders_data = [
            {"order_no": "SO-2024-001", "customer_name": "Acme Corporation", "product_name": "Premium Compound A",
             "quantity": 100, "unit": "bags", "priority": PriorityEnum.HIGH, "status": OrderStatusEnum.OPEN,
             "delivery_date": today + timedelta(days=5)},
            {"order_no": "SO-2024-002", "customer_name": "Global Foods Inc", "product_name": "Standard Compound B",
             "quantity": 200, "unit": "bags", "priority": PriorityEnum.NORMAL, "status": OrderStatusEnum.APPROVED,
             "delivery_date": today + timedelta(days=7)},
            {"order_no": "SO-2024-003", "customer_name": "Tech Manufacturing Ltd", "product_name": "Specialty Mix C",
             "quantity": 50, "unit": "bags", "priority": PriorityEnum.CRITICAL, "status": OrderStatusEnum.IN_PRODUCTION,
             "delivery_date": today + timedelta(days=3)},
            {"order_no": "SO-2024-004", "customer_name": "Premium Retailers", "product_name": "Economy Blend D",
             "quantity": 500, "unit": "kg", "priority": PriorityEnum.NORMAL, "status": OrderStatusEnum.OPEN,
             "delivery_date": today + timedelta(days=10)},
            {"order_no": "SO-2024-005", "customer_name": "Export Partners LLC", "product_name": "Premium Compound A",
             "quantity": 2, "unit": "tons", "priority": PriorityEnum.HIGH, "status": OrderStatusEnum.PRODUCTION_PLANNED,
             "delivery_date": today + timedelta(days=14)},
            {"order_no": "SO-2024-006", "customer_name": "Acme Corporation", "product_name": "Standard Compound B",
             "quantity": 150, "unit": "bags", "priority": PriorityEnum.LOW, "status": OrderStatusEnum.READY_FOR_SHIPMENT,
             "delivery_date": today + timedelta(days=2)},
            {"order_no": "SO-2024-007", "customer_name": "Global Foods Inc", "product_name": "Economy Blend D",
             "quantity": 300, "unit": "bags", "priority": PriorityEnum.NORMAL, "status": OrderStatusEnum.SHIPPED,
             "delivery_date": today - timedelta(days=2)},
            {"order_no": "SO-2024-008", "customer_name": "Tech Manufacturing Ltd", "product_name": "Premium Compound A",
             "quantity": 80, "unit": "bags", "priority": PriorityEnum.HIGH, "status": OrderStatusEnum.CLOSED,
             "delivery_date": today - timedelta(days=10)},
            {"order_no": "SO-2024-009", "customer_name": "Premium Retailers", "product_name": "Specialty Mix C",
             "quantity": 1000, "unit": "kg", "priority": PriorityEnum.NORMAL, "status": OrderStatusEnum.OPEN,
             "delivery_date": today + timedelta(days=12)},
            {"order_no": "SO-2024-010", "customer_name": "Export Partners LLC", "product_name": "Standard Compound B",
             "quantity": 5, "unit": "tons", "priority": PriorityEnum.CRITICAL, "status": OrderStatusEnum.OPEN,
             "delivery_date": today + timedelta(days=8)},
        ]
        
        for o in orders_data:
            customer = customers[o["customer_name"]]
            product = products[o["product_name"]]
            order = CustomerOrder(
                order_no=o["order_no"],
                customer_id=customer.id,
                product_id=product.id,
                quantity=o["quantity"],
                unit=o["unit"],
                bag_size_kg=product.default_bag_size_kg,
                priority=o["priority"],
                status=o["status"],
                delivery_date=o["delivery_date"],
                created_by=users["planner"].id,
            )
            db.add(order)
        
        db.flush()
        print(f"  Created {len(orders_data)} customer orders")
        
        # Commit all
        db.commit()
        
        print("\n✅ Database seeded successfully!")
        print("\nTest credentials:")
        print("  admin / admin123 (Super Admin)")
        print("  planner / planner123 (Production Planner)")
        print("  warehouse / warehouse123 (Warehouse User)")
        print("  purchase / purchase123 (Purchasing User)")
        print("  viewer / view123 (Management Viewer)")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
