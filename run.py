"""
JDK Smart Factory Platform — Entry Point
Run: python run.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from app import app

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
