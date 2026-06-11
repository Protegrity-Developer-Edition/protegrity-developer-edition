#!/usr/bin/env python3
"""BusinessCustomerApp — standalone launcher."""
import os
import sys
from pathlib import Path

_PARENT = str(Path(__file__).resolve().parent.parent)
_LOCAL = str(Path(__file__).resolve().parent)
os.chdir(_PARENT)
sys.path.insert(0, _LOCAL)
sys.path.insert(1, _PARENT)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(_PARENT) / ".env", override=True)
except ImportError:
    pass

# Force LangGraph orchestrator for business app
os.environ["ORCHESTRATOR"] = "langgraph"

import app as app_module

if __name__ == "__main__":
    port = int(os.environ.get("BUSINESS_PORT", 5003))
    print(f"[BusinessCustomerApp] Banking Cloud Portal on port {port}")
    app_module.app.run(host="0.0.0.0", port=port, debug=True)
