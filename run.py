"""
JDK Smart Factory Platform — Entry Point
Run: python run.py

Note: debug=True/reloader intentionally NOT used here — it previously
caused an infinite reload loop (Flask session key regenerates on each
reloader restart, killing sessions and triggering repeated reloads).
Prefer `python serve.py` for the full startup banner.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from app import app

if __name__ == '__main__':
    app.run(debug=False, use_reloader=False, port=5000, host='0.0.0.0', threaded=True)
