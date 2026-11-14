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

from backend.app import app  # noqa: E402
