#!/bin/bash

################################################################################
# JDK Smart Factory Platform - One-Click Installer for XAMPP
# 
# This script installs and configures the JDK Smart Factory application
# to work with XAMPP MySQL (database: jdk)
#
# Usage: ./install.sh
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="jdk"
DB_USER="root"
DB_PASSWORD=""
DB_HOST="localhost"
DB_PORT="3306"
PYTHON_VENV=".venv"
BACKEND_DIR="$(pwd)/backend"
FRONTEND_DIR="$(pwd)/frontend"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   JDK Smart Factory Platform - Enterprise Edition       ║${NC}"
echo -e "${BLUE}║           One-Click Installer for XAMPP                 ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8+ first."
        exit 1
    fi
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python $PYTHON_VERSION found"
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js 18+ first."
        exit 1
    fi
    NODE_VERSION=$(node --version)
    print_success "Node.js $NODE_VERSION found"
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install npm first."
        exit 1
    fi
    NPM_VERSION=$(npm --version)
    print_success "npm $NPM_VERSION found"
    
    # Check MySQL client
    if ! command -v mysql &> /dev/null; then
        print_warning "MySQL client not found. Will attempt to connect using Python."
    else
        print_success "MySQL client found"
    fi
    
    # Check if XAMPP MySQL is running
    print_status "Checking MySQL connection..."
    if ! python3 -c "import pymysql; pymysql.connect(host='$DB_HOST', port=$DB_PORT, user='$DB_USER', password='$DB_PASSWORD')" 2>/dev/null; then
        print_error "Cannot connect to MySQL at $DB_HOST:$DB_PORT"
        print_warning "Please ensure XAMPP MySQL is running:"
        print_warning "  1. Open XAMPP Control Panel"
        print_warning "  2. Start the MySQL module"
        print_warning "  3. Run this installer again"
        exit 1
    fi
    print_success "Connected to MySQL successfully"
}

# Create database
create_database() {
    print_status "Creating database '$DB_NAME'..."
    
    python3 << EOF
import pymysql

try:
    connection = pymysql.connect(
        host='$DB_HOST',
        port=$DB_PORT,
        user='$DB_USER',
        password='$DB_PASSWORD'
    )
    cursor = connection.cursor()
    
    # Create database if not exists
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    print("Database '$DB_NAME' created or already exists")
    
    # Grant privileges
    cursor.execute(f"GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost'")
    cursor.execute("FLUSH PRIVILEGES")
    print("Privileges granted")
    
    cursor.close()
    connection.close()
except Exception as e:
    print(f"Error: {e}")
    exit(1)
EOF
    
    print_success "Database setup complete"
}

# Setup Python virtual environment
setup_python_env() {
    print_status "Setting up Python virtual environment..."
    
    if [ -d "$PYTHON_VENV" ]; then
        print_warning "Virtual environment already exists. Recreating..."
        rm -rf "$PYTHON_VENV"
    fi
    
    python3 -m venv "$PYTHON_VENV"
    print_success "Virtual environment created"
    
    # Activate virtual environment
    source "$PYTHON_VENV/bin/activate"
    
    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip --quiet
    
    # Install Python dependencies
    print_status "Installing Python dependencies..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt --quiet
        print_success "Python dependencies installed"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
    
    # Deactivate virtual environment
    deactivate
}

# Install Node.js dependencies
setup_node_env() {
    print_status "Installing Node.js dependencies..."
    
    cd "$FRONTEND_DIR"
    
    if [ -d "node_modules" ]; then
        print_warning "Node modules already exist. Reinstalling..."
        rm -rf "node_modules"
    fi
    
    npm install --silent
    print_success "Node.js dependencies installed"
    
    cd ..
}

# Build frontend
build_frontend() {
    print_status "Building frontend application..."
    
    cd "$FRONTEND_DIR"
    
    # Create .env file for frontend
    cat > .env << EOF
VITE_API_BASE_URL=http://localhost:8000/api
EOF
    
    npm run build --silent
    print_success "Frontend built successfully"
    
    cd ..
}

# Configure backend
configure_backend() {
    print_status "Configuring backend for XAMPP..."
    
    # Create .env file for backend
    cat > backend/.env << EOF
# Application
APP_NAME=JDK Smart Factory Platform
DEBUG=True

# Database (XAMPP MySQL)
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_USER=root
DATABASE_PASSWORD=
DATABASE_NAME=$DB_NAME

# JWT Authentication
JWT_SECRET_KEY=jdk-smart-factory-super-secret-jwt-key-2024-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Security
BCRYPT_ROUNDS=12
EOF
    
    print_success "Backend configured"
}

# Initialize database and seed data
init_database() {
    print_status "Initializing database schema and seeding data..."
    
    source "$PYTHON_VENV/bin/activate"
    
    cd "$BACKEND_DIR"
    
    # Run database initialization and seeding
    python3 -c "
import sys
sys.path.insert(0, '.')
from database import engine, Base
from seed_data import seed_database

# Create tables
Base.metadata.create_all(bind=engine)
print('Database tables created')

# Seed data
seed_database()
print('Database seeded with test data')
"
    
    deactivate
    cd ..
    
    print_success "Database initialized and seeded"
}

# Create startup scripts
create_startup_scripts() {
    print_status "Creating startup scripts..."
    
    # Backend startup script
    cat > start-backend.sh << 'EOF'
#!/bin/bash
echo "Starting JDK Smart Factory Backend..."
source .venv/bin/activate
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
EOF
    chmod +x start-backend.sh
    
    # Frontend startup script
    cat > start-frontend.sh << 'EOF'
#!/bin/bash
echo "Starting JDK Smart Factory Frontend..."
cd frontend
npm run dev -- --host 0.0.0.0 --port 3000
EOF
    chmod +x start-frontend.sh
    
    # Combined startup script
    cat > start.sh << 'EOF'
#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   JDK Smart Factory Platform - Starting Services        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if MySQL is running
if ! python3 -c "import pymysql; pymysql.connect(host='localhost', port=3306, user='root', password='')" 2>/dev/null; then
    echo -e "${RED}[ERROR]${NC} Cannot connect to MySQL. Please start XAMPP MySQL first."
    exit 1
fi

echo -e "${GREEN}[OK]${NC} MySQL connection verified"
echo ""

# Start backend in background
echo -e "${BLUE}[INFO]${NC} Starting backend server on http://localhost:8000..."
source .venv/bin/activate
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend
echo -e "${BLUE}[INFO]${NC} Starting frontend dev server on http://localhost:3000..."
cd frontend
npm run dev -- --host 0.0.0.0 --port 3000

# Cleanup on exit
trap "kill $BACKEND_PID 2>/dev/null" EXIT
EOF
    chmod +x start.sh
    
    # Stop script
    cat > stop.sh << 'EOF'
#!/bin/bash
echo "Stopping JDK Smart Factory services..."
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
echo "Services stopped"
EOF
    chmod +x stop.sh
    
    print_success "Startup scripts created"
}

# Display login credentials
show_credentials() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              Installation Complete!                      ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Test User Credentials:${NC}"
    echo "─────────────────────────────────────────"
    echo "  Super Admin:     admin / admin123"
    echo "  Production Plan: planner / planner123"
    echo "  Warehouse:       warehouse / warehouse123"
    echo "  Purchasing:      purchase / purchase123"
    echo "  Viewer:          viewer / view123"
    echo ""
    echo -e "${BLUE}To start the application:${NC}"
    echo "  ./start.sh"
    echo ""
    echo -e "${BLUE}To start services separately:${NC}"
    echo "  Terminal 1: ./start-backend.sh"
    echo "  Terminal 2: ./start-frontend.sh"
    echo ""
    echo -e "${BLUE}Access URLs:${NC}"
    echo "  Frontend:  http://localhost:3000"
    echo "  Backend:   http://localhost:8000"
    echo "  API Docs:  http://localhost:8000/docs"
    echo ""
    echo -e "${YELLOW}Note: Make sure XAMPP MySQL is running before starting!${NC}"
    echo ""
}

# Main installation process
main() {
    echo ""
    check_prerequisites
    echo ""
    create_database
    echo ""
    configure_backend
    echo ""
    setup_python_env
    echo ""
    setup_node_env
    echo ""
    build_frontend
    echo ""
    init_database
    echo ""
    create_startup_scripts
    echo ""
    show_credentials
}

# Run main function
main
