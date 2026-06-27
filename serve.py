"""
JDK Smart Factory Platform — Single-process launcher
Serves Flask REST API + static frontend on one port.
Run: python serve.py
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from flask import send_from_directory, abort
from app import app

FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend')


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def static_frontend(path):
    """
    Catch-all SPA handler.
    - Never intercepts /api/* routes (they are already registered on the app)
    - Serves real static files (JS, CSS) directly
    - Everything else returns index.html so the JS router handles it
    """
    # Guard: API routes must never reach here — they have their own handlers.
    # If they somehow do, return 404 rather than HTML (avoids silent JSON-parse errors).
    if path.startswith('api/'):
        abort(404)

    # Serve actual files that exist on disk
    file_path = os.path.join(FRONTEND, path)
    if path and os.path.isfile(file_path):
        return send_from_directory(FRONTEND, path)

    # SPA fallback — always index.html
    return send_from_directory(FRONTEND, 'index.html')


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
