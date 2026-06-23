"""
Serve both the API (backend/app.py) and the static frontend from a single process.
Run: python serve.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from flask import send_from_directory
from app import app

FRONTEND = os.path.join(os.path.dirname(__file__), 'frontend')

@app.route('/')
@app.route('/<path:path>')
def static_frontend(path='index.html'):
    # API routes are already registered, this catches everything else
    if path.startswith('api/'):
        return app.send_static_file(path)
    try:
        return send_from_directory(FRONTEND, path)
    except Exception:
        return send_from_directory(FRONTEND, 'index.html')

if __name__ == '__main__':
    print("=" * 60)
    print("  JDK Smart Factory Platform v2.0")
    print("  Open: http://localhost:5000")
    print("  Default login: admin / admin123")
    print("=" * 60)
    app.run(debug=True, port=5000, host='0.0.0.0')
