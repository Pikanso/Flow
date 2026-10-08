"""Open an existing instance or start the local service."""
import json
import runpy
import sys
import urllib.request
import webbrowser
from pathlib import Path

try:
    with urllib.request.urlopen('http://127.0.0.1:8765/api/health', timeout=2) as response:
        active = json.load(response).get('app') == 'Flow'
except Exception:
    active = False
if active:
    webbrowser.open('http://127.0.0.1:8765')
else:
    sys.argv = ['server.py', '--open']
    runpy.run_path(str(Path(__file__).with_name('server.py')), run_name='__main__')
