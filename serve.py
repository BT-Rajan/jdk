"""
Serve both the API (backend/app.py) and the static frontend from a single process.
Run: python serve.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from flask import send_from_directory
from app import app

FRONTEND = os.path.join(os.path.dirname(__file__), 'frontend')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def static_frontend(path):
    # Never intercept API routes — they are already registered on the app
    if path.startswith('api/'):
        from flask import abort
        abort(404)

    # Serve real files that exist (JS, CSS, assets…)
    full = os.path.join(FRONTEND, path)
    if path and os.path.isfile(full):
        return send_from_directory(FRONTEND, path)

    # Everything else → SPA shell
    return send_from_directory(FRONTEND, 'index.html')

if __name__ == '__main__':
    print("=" * 60)
    print("  JDK Smart Factory Platform v2.0")
    print("  Open: http://localhost:5000")
    print("  Default login: admin / admin123")
    print("=" * 60)
    app.run(debug=False, port=5000, host='0.0.0.0')
