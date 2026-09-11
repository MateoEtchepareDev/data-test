#!/usr/bin/env python
"""Dev-only runner: starts the API service on localhost for UI tests.

Adds the service/shared source dirs to sys.path and serves the Flask app on
127.0.0.1:<port>. Never used in production (Lambda uses Mangum).
"""

import sys
from pathlib import Path

API_SRC = Path(__file__).resolve().parents[1] / "services" / "api" / "src"
SHARED_SRC = Path(__file__).resolve().parents[1] / "packages" / "shared" / "src"
for p in (API_SRC, SHARED_SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from api.app import app  # noqa: E402

port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)