"""
Metric Configuration Schema and Loader.

Parses metrics.yaml into a typed ProfilerConfig.  The loader validates
derived formula symbols against the full computed namespace that will exist
at runtime, surfacing typos as load-time errors rather than runtime crashes.

Schema overview

Each segment has a list of metric definitions.  Four types are supported:

    ratio   - per-iteration num/den rate; emits stats + optional totals
    stats   - descriptive stats over a sampled series; optional total
    sum     - single accumulated total from one record key
    derived - scalar expression evaluated after all other segments finish;
              references computed fields by their exact output name
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Literal
from enum import StrEnum

import yaml

TotalsSpec = list[Literal["numerator", "denominator"]]

STATS_SUFFIX = ["mean", "median", "stddev", "min", "max"]

class Segments(StrEnum):
    WALL_TIME = "wall_time"
    CPU       = "cpu"
    GPU       = "gpu"
    MEMORY    = "memory"
    THREAD    = "thread"
    LD        = "ld"
    PERF      = "perf"

@dataclass
class BaseMetric:
    name:  str
    scale: float = 1.0

    def output_fields(self) -> list[str]:
        raise NotImplementedError("Subclasses must implement output_fields()")

@dataclass
class RatioMetric(BaseMetric):
    numerator:   str        = ""
    denominator: str        = ""
    totals:      TotalsSpec = field(default_factory = list)

    def output_fields(self) -> list[str]:
        fields = []
        if "numerator" in self.totals:
            fields.append(total_key(self.numerator))

        if "denominator" in self.totals:
            fields.append(total_key(self.denominator))

        fields += stats_fields(self.name)
        return fields

@dataclass
class StatsMetric(BaseMetric):
    key:   str   = ""
    scale: float = 1.0
    total: bool  = False

    def output_fields(self) -> list[str]:
        fields = []
        if self.total:
            fields.append(f"{self.name}_total")

        fields += stats_fields(self.name)
        return fields

@dataclass
class SumMetric(BaseMetric):
    key: str = ""

    def output_fields(self) -> list[str]:
        return [f"{self.name}_total"]

@dataclass
class DerivedMetric(BaseMetric):
    formula: str = ""

    def output_fields(self) -> list[str]:
        return [self.name]

    def formula_symbols(self) -> set[str]:
        try:
            tree = ast.parse(self.formula, mode = "eval")

        except SyntaxError as e:
            raise ValueError(f"Derived metric '{self.name}' has invalid formula syntax: {e}")
        
        return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}

@dataclass
class PerfGroup:
    name:       str
    events:     list[str]
    use_ld_env: bool = False

@dataclass
class SegmentConfig:
    name:        str
    metrics:     list[BaseMetric]
    perf_groups: list[PerfGroup] = field(default_factory=list)

    def output_fields(self) -> list[str]:
        fields = []
        for m in self.metrics:
            fields.extend(m.output_fields())

        return fields

    def non_derived_fields(self) -> list[str]:
        fields = []
        for m in self.metrics:
            if not isinstance(m, DerivedMetric):
                fields.extend(m.output_fields())

        return fields
    
    def read_keys_for_target(self, target) -> list[str]:
        keys = []
        for metric in self.metrics:
            key = getattr(metric, 'key', None)
            if key is not None and (target is None or hasattr(target, key)):
                keys.append(key)

        return keys

    def read_keys(self):
        keys = []
        for metric in self.metrics:
            key = getattr(metric, 'key', None)
            if key is not None:
                keys.append(key)

        return keys

@dataclass
class ProfilerConfig:
    segments: dict[str, SegmentConfig]

    def csv_fields(self) -> list[str]:
        fields = []
        for seg in self.segments.values():
            fields.extend(seg.output_fields())

        return fields

    def derived_metrics(self) -> list[tuple[str, DerivedMetric]]:
        result = []
        for seg_name, seg in self.segments.items():
            for m in seg.metrics:
                if isinstance(m, DerivedMetric):
                    result.append((seg_name, m))

        return result
    
@dataclass
class PerfGroupConfig:
    name:   str
    events: list[str]
    env:    dict[str, str] | None

SAFE_BUILTINS = {"abs", "round", "min", "max", "sum"}

def load_config(path: str = "metrics.yaml") -> ProfilerConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)

    segments: dict[str, SegmentConfig] = {}

    for seg_name, seg_raw in raw.get("segments", {}).items():
        perf_groups = [
            PerfGroup(
                name       = pg["name"],
                events     = pg["events"],
                use_ld_env = pg.get("use_ld_env", False),
            )
            for pg in seg_raw.get("perf_groups", [])
        ]

        metrics: list[BaseMetric] = []
        for m_raw in seg_raw.get("metrics", []):
            metrics.append(parse_metric(seg_name, m_raw))

        segments[seg_name] = SegmentConfig(
            name        = seg_name,
            metrics     = metrics,
            perf_groups = perf_groups,
        )

    cfg = ProfilerConfig(segments)
    validate_derived(cfg)
    return cfg

def parse_base_metric(raw: dict) -> dict:
    return {
        "name": raw.get("name"),
        "scale": float(raw.get("scale", 1.0))
    }

def parse_metric(seg_name: str, raw: dict) -> BaseMetric:
    mtype       = raw.get("type")
    base_fields = parse_base_metric(raw)

    if not base_fields.get("name"):
        raise ValueError(f"Segment '{seg_name}': metric missing 'name' field.")
    
    if not mtype:
        raise ValueError(f"Segment '{seg_name}', metric '{base_fields["name"]}': missing 'type' field.")

    if mtype == "ratio":
        return RatioMetric(
            **base_fields,
            numerator   = raw["numerator"],
            denominator = raw["denominator"],
            totals      = raw.get("totals", [])
        )
    
    if mtype == "stats":
        return StatsMetric(
            **base_fields,
            key   = raw["key"],
            total = bool(raw.get("total", False)),
        )
    
    if mtype == "sum":
        return SumMetric(
            **base_fields,
            key = raw["key"]
        )
    
    if mtype == "derived":
        return DerivedMetric(
            **base_fields,
            formula = raw["formula"]
        )

    raise ValueError(
        f"Segment '{seg_name}', metric '{base_fields["name"]}': unknown type '{mtype}'. "
        "Expected: ratio | stats | sum | derived"
    )

def validate_derived(cfg: ProfilerConfig) -> None:
    available: set[str] = set()

    for segment in cfg.segments.values():
        for field_name in segment.non_derived_fields():
            available.add(field_name)

        for metric in segment.metrics:
            if not isinstance(metric, DerivedMetric):
                continue

            symbols = metric.formula_symbols()
            unknown = symbols - available - SAFE_BUILTINS
            if unknown:
                raise ValueError(
                    f"Derived metric '{metric.name}' references unknown symbol(s): "
                    f"{', '.join(sorted(unknown))}.\n"
                    f"Available at this point: {', '.join(sorted(available))}"
                )

            available.add(metric.name)

def safe_key(key: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", key)

def total_key(event_key: str) -> str:
    return f"{safe_key(event_key)}_total"

def stats_fields(name: str) -> list[str]:
    return [f"{name}_{stat}" for stat in STATS_SUFFIX]
