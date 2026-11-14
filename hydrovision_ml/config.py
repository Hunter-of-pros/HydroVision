"""Configuration loader and physical constants for HydroVision.

Loads parameters from root config.json and exports project-wide constants.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def _find_config_path() -> Path:
    # First check current working directory
    cwd_path = Path.cwd() / "config.json"
    if cwd_path.is_file():
        return cwd_path
    # Fallback to repository root relative to this file
    repo_root_path = Path(__file__).resolve().parent.parent / "config.json"
    if repo_root_path.is_file():
        return repo_root_path
    raise FileNotFoundError("Could not locate config.json in working directory or repo root.")


def load_config() -> Dict[str, Any]:
    config_path = _find_config_path()
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Global configuration dictionary
CONFIG: Dict[str, Any] = load_config()

# Grid specifications
GRID: Dict[str, Any] = CONFIG["grid"]
ROWS: int = int(GRID["rows"])
COLS: int = int(GRID["cols"])
CELL_SIZE_M: float = float(GRID["cell_size_m"])

# Temporal simulation parameters
TIME_CONFIG: Dict[str, Any] = CONFIG["time"]
DT_S: int = int(TIME_CONFIG["dt_s"])
HORIZON_STEPS: int = int(TIME_CONFIG["horizon_steps"])
NUM_FRAMES: int = HORIZON_STEPS + 1  # t=0 through t=HORIZON_STEPS * DT_S

# Hydrological threshold
WET_THRESHOLD_M: float = float(CONFIG["wet_threshold_m"])

# Default dataset storage path
import os
DATA_DIR: Path = Path(os.getenv("HYDRO_DATA_DIR", CONFIG.get("data_dir", r"C:\hydrovision_data\data")))

# Contract metadata
CONTRACT_VERSION: str = str(CONFIG["contract_version"])

