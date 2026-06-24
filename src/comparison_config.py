from __future__ import annotations

from argparse import Namespace
import argparse
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import yaml

from threshold_config_generator import get_yaml_path

# list of all suffixes a metric can have
SUFFIXES = ["_total", "_mean", "_median", "_stddev", "_min", "_max"]

class Direction(StrEnum):
    HIGHER_BETTER = "higher_better" # higher values mean improvement
    LOWER_BETTER  = "lower_better"  # lower values mean improvement
    NEUTRAL       = "neutral"       # metric is not necessarily influenced by value

@dataclass(frozen = True)
class ThresholdConfig:
    """
    Threshold Config related to a specific metric
    """
    direction:                 Direction = Direction.NEUTRAL # improvement direction
    noise_floor_pct:           float     = 0.0               # noise-floor boundary in percentage (should be a positive number)
    improvement_threshold_pct: float     = 0.0               # improvement boundary, defines when improvement is reached (depending on direction)
    regression_threshold_pct:  float     = 0.0               # regression boundary, defines when regression is reached (depending on direction)

def load_thresholds_config(args: argparse.Namespace, yaml_path: Path | str) -> dict[str, ThresholdConfig]:
    """
    Loads the yaml threshold configuration, according to CLI

    args: parsed CLI arguments

    yaml_path: path to a static (fallback) yaml configuration

    Returns dictionary of metrics (suffix included) mapped to their threshold configurations
    """

    dynamic_path = args.use_computed_thresholds
    if dynamic_path:
        if dynamic_path == 'default':
            #if no path is provided to -uct, --use-computed-thresholds, gets configuration corresponding to its csv name
            dynamic_path = get_yaml_path(Path(args.path).name)

        if Path(dynamic_path).is_file():
            yaml_path = dynamic_path

    with open(yaml_path, "r", encoding = "utf-8") as f:
        raw_data = yaml.safe_load(f) or {}

    extended_map: dict[str, ThresholdConfig] = {}
    raw_thresholds                           = raw_data.get("thresholds", {})

    for base_metric_name, raw_cfg in raw_thresholds.items():
        raw_direction  = raw_cfg.get("direction", "neutral")
        
        try:
            direction = Direction(raw_direction)
        except:
            direction = Direction.NEUTRAL # invalid directions fall back to neutral

        config_instance = ThresholdConfig(
            direction                 = direction,
            noise_floor_pct           = float(raw_cfg.get("noise_floor_pct", 0.0)),
            improvement_threshold_pct = float(raw_cfg.get("improvement_threshold_pct", 0.0)),
            regression_threshold_pct  = float(raw_cfg.get("regression_threshold_pct", 0.0))
        )

        extended_map[base_metric_name] = config_instance

        for suffix in SUFFIXES:
            suffixed_key               = f"{base_metric_name}{suffix}"
            extended_map[suffixed_key] = config_instance

    return extended_map
