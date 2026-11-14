import os
import sys
from pathlib import Path

# Add project root to sys.path so backend and hydrovision_ml are resolvable
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

# Ensure current working directory is project root so config.json and fixtures resolve
os.chdir(str(root_dir))

# If torch is not available in serverless environment, gracefully use the 2D SWE physical solver
try:
    import torch  # noqa: F401
except ImportError:
    os.environ["HYDRO_MODE"] = "mock"

from urllib.parse import parse_qs, urlencode
from backend.app import app as fastapi_app  # noqa: E402


class VercelPathAdapter:
    """ASGI middleware that ensures Vercel serverless request paths match FastAPI routes."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            raw_path = scope.get("path", "")
            raw_query = scope.get("query_string", b"").decode("latin-1")
            query_params = parse_qs(raw_query, keep_blank_values=True)
            
            # 1. Check explicit __path passed from vercel.json rewrite
            extracted_path = None
            if "__path" in query_params:
                extracted_path = query_params.pop("__path")[0]
                # Re-encode cleaned query string without __path
                new_query = urlencode(query_params, doseq=True)
                scope["query_string"] = new_query.encode("latin-1")
            
            # 2. Check Vercel proxy headers if no __path
            if not extracted_path:
                headers = dict(scope.get("headers", []))
                matched = headers.get(b"x-matched-path", b"").decode("latin-1")
                forwarded = headers.get(b"x-forwarded-uri", b"").decode("latin-1")
                target = matched or forwarded or raw_path
                target = target.split("?")[0]
                for prefix in ("/api/index.py", "/api/index", "/api"):
                    if target.startswith(prefix):
                        target = target[len(prefix):] or "/"
                        break
                extracted_path = target
            
            if extracted_path:
                if not extracted_path.startswith("/"):
                    extracted_path = "/" + extracted_path
                scope["path"] = extracted_path
                scope["raw_path"] = extracted_path.encode("latin-1")

        await self.app(scope, receive, send)


app = VercelPathAdapter(fastapi_app)
