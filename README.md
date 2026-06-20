# JDK Smart Factory Platform - Enterprise Edition

A modern, enterprise-class Smart Factory Management System with MRP/ATP capabilities.

## Features

- **Secure Authentication**: JWT-based authentication with role-based access control
- **Modern UI**: Responsive React frontend with Tailwind CSS
- **Enterprise Database**: MySQL backend with proper schema design
- **Role-Based Access**: 5 different user roles with specific permissions
- **MRP Engine**: Material Requirements Planning and Available-to-Promise calculations
- **Complete Modules**: Orders, Inventory, Products, Customers, Suppliers, Reports

## Quick Start with XAMPP

### Prerequisites

1. **XAMPP installed** with MySQL running
2. **Python 3.8+** installed
3. **Node.js 18+** installed

### Installation

1. **Start XAMPP MySQL** from the XAMPP Control Panel

2. **Run the one-click installer**:
   ```bash
   ./install.sh
   ```

3. **Start the application**:
   ```bash
   ./start.sh
   ```

4. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Test User Credentials

| Username   | Password      | Role                |
|------------|---------------|---------------------|
| admin      | admin123      | Super Admin         |
| planner    | planner123    | Production Planner  |
| warehouse  | warehouse123  | Warehouse User      |
| purchase   | purchase123   | Purchasing User     |
| viewer     | view123       | Management Viewer   |

## Manual Setup (Alternative)

If you prefer manual setup:

### Backend Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your database settings

# Initialize database
cd backend
python3 -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"
python3 seed_data.py
cd ..

# Start backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
echo "VITE_API_BASE_URL=http://localhost:8000/api" > .env

# Build for production or run development server
npm run build        # Production build
npm run dev          # Development server
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React SPA     │────▶│   FastAPI       │────▶│   MySQL         │
│   (Frontend)    │     │   (Backend)     │     │   (Database)    │
│   Port: 3000    │     │   Port: 8000    │     │   Port: 3306    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Project Structure

```
/workspace
├── backend/                 # FastAPI backend
│   ├── main.py             # Application entry point
│   ├── config.py           # Configuration settings
│   ├── database.py         # Database connection
│   ├── models.py           # SQLAlchemy models
│   ├── schemas.py          # Pydantic schemas
│   ├── security.py         # Authentication & authorization
│   ├── seed_data.py        # Test data generator
│   └── routes/             # API endpoints
│       ├── auth.py         # Authentication routes
│       ├── customers.py    # Customer management
│       ├── products.py     # Product management
│       ├── orders.py       # Order management
│       ├── inventory.py    # Inventory management
│       └── mrp.py          # MRP calculations
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # Reusable components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   ├── hooks/          # Custom hooks
│   │   └── types/          # TypeScript types
│   └── public/             # Static assets
├── install.sh              # One-click installer
├── start.sh                # Start all services
├── stop.sh                 # Stop all services
├── start-backend.sh        # Start backend only
├── start-frontend.sh       # Start frontend only
└── requirements.txt        # Python dependencies
```

## Security Features

- **Password Hashing**: Bcrypt for secure password storage
- **JWT Tokens**: Access and refresh tokens with expiration
- **Role-Based Access Control**: 5 predefined roles with specific permissions
- **CORS Protection**: Configurable cross-origin resource sharing
- **Input Validation**: Pydantic schemas for request validation

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - User logout

### Customers
- `GET /api/customers` - List all customers
- `POST /api/customers` - Create customer
- `GET /api/customers/{id}` - Get customer details
- `PUT /api/customers/{id}` - Update customer
- `DELETE /api/customers/{id}` - Delete customer

### Products
- `GET /api/products` - List all products
- `POST /api/products` - Create product
- `GET /api/products/{id}` - Get product details
- `PUT /api/products/{id}` - Update product
- `DELETE /api/products/{id}` - Delete product

### Orders
- `GET /api/orders` - List all orders
- `POST /api/orders` - Create order
- `GET /api/orders/{id}` - Get order details
- `PUT /api/orders/{id}` - Update order
- `POST /api/orders/{id}/approve` - Approve order
- `POST /api/orders/{id}/cancel` - Cancel order

### Inventory
- `GET /api/inventory/raw-materials` - Raw materials inventory
- `GET /api/inventory/finished-goods` - Finished goods inventory
- `POST /api/inventory/raw-materials/adjust` - Adjust stock
- `POST /api/inventory/finished-goods/adjust` - Adjust stock

### MRP
- `GET /api/mrp/calculate` - Run MRP calculation
- `GET /api/mrp/atp` - Available-to-Promise check
- `GET /api/mrp/reports` - Generate MRP reports

## User Roles

| Role | Permissions |
|------|-------------|
| **Super Admin** | Full system access, user management |
| **Production Planner** | Create/manage orders, run MRP, plan production |
| **Warehouse User** | Manage inventory, adjust stock levels |
| **Purchasing User** | Manage suppliers, create purchase orders |
| **Management Viewer** | Read-only access to reports and dashboards |

## Troubleshooting

### MySQL Connection Error
- Ensure XAMPP MySQL is running
- Check if port 3306 is available
- Verify database credentials in `backend/.env`

### Port Already in Use
- Backend: Change port in `start-backend.sh`
- Frontend: Change port in `start-frontend.sh`

### Permission Denied
```bash
chmod +x install.sh start.sh stop.sh
```

## License

Proprietary - JDK Smart Factory Platform

## Support

For support, please contact your system administrator.
