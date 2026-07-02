"""
JDK Smart Factory Platform — Single-process launcher
Serves Flask REST API + static frontend on one port.
Run: python serve.py

Note: the frontend static/SPA route is registered inside backend/app.py
itself, so `python backend/app.py` works identically to this launcher.
This file just adds the startup banner.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from app import app

if __name__ == '__main__':
    print("=" * 60)
    print("  JDK Smart Factory Platform v2.0")
    print("  Open: http://localhost:5000")
    print("=" * 60)
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,        # MUST be False — debug=True enables the reloader
        use_reloader=False, # Reloader spawns a child process; secret key regenerates → sessions die → infinite reload
        threaded=True,      # Allow concurrent requests
    )
