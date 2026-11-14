"""Test configuration file validity and required keys.

Phase: Quality & Contract Assurance
"""

import json
from pathlib import Path


def test_config_file_exists_and_loads():
    config_path = Path(__file__).resolve().parent.parent / "config.json"
    assert config_path.is_file(), "config.json must exist in project root"

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    assert isinstance(config, dict)
    assert config.get("contract_version") == "1.0"


def test_config_grid_specification():
    from hydrovision_ml.config import CELL_SIZE_M, COLS, GRID, ROWS

    assert ROWS == 64
    assert COLS == 64
    assert CELL_SIZE_M == 40
    assert GRID["rows"] == 64
    assert GRID["cols"] == 64
    assert GRID["cell_size_m"] == 40


def test_config_time_and_thresholds():
    from hydrovision_ml.config import DT_S, HORIZON_STEPS, NUM_FRAMES, WET_THRESHOLD_M

    assert DT_S == 60
    assert HORIZON_STEPS == 120
    assert NUM_FRAMES == 121
    assert WET_THRESHOLD_M == 0.05


def test_config_params_ranges():
    from hydrovision_ml.config import CONFIG

    params = CONFIG.get("params", {})
    required_keys = [
        "rain_intensity_mmhr",
        "rain_duration_min",
        "rain_shape",
        "drain_capacity_mmhr",
        "horizon_steps",
    ]
    for key in required_keys:
        assert key in params, f"Missing required parameter configuration for '{key}'"

    assert params["rain_intensity_mmhr"]["min"] <= params["rain_intensity_mmhr"]["default"] <= params["rain_intensity_mmhr"]["max"]
    assert params["rain_duration_min"]["min"] <= params["rain_duration_min"]["default"] <= params["rain_duration_min"]["max"]
    assert "constant" in params["rain_shape"]["allowed"]
    assert params["drain_capacity_mmhr"]["default"] == 0

