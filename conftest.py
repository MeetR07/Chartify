"""
Root-level conftest.py — auto-loaded by pytest before any test.

Adds the project root to sys.path so that both:
  - `import backend.xyz` (backend package)
  - `import server` / `import main` (root entry-points)
resolve correctly regardless of which directory pytest is invoked from.

This makes per-file sys.path.insert() calls in individual test files redundant
(they are kept for backwards-compat with python -m unittest invocations).
"""
import os
import sys

# Insert project root at the front of sys.path
_ROOT = os.path.abspath(os.path.dirname(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
