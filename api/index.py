import sys
import os

# Ensure the root project directory is on sys.path so server, charts, main, agent are imported cleanly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from server import app
