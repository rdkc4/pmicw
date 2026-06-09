from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass(frozen = True)
class MetricSpec:
    name: str

@dataclass(frozen = True)
class PlotGroupConfig:
    name: str
    metrics: list[MetricSpec]

    def get_metric_names(self) -> list[str]:
        return [metric.name for metric in self.metrics]


def load_plot_config(yaml_path: Path | str) -> dict[str, PlotGroupConfig]:
    with open(yaml_path, "r", encoding = "utf-8") as f:
        raw_data = yaml.safe_load(f) or {}

    plot_groups: dict[str, PlotGroupConfig] = {}
    raw_plot_groups                         = raw_data.get("plot_groups", {})

    for group_name, group_content in raw_plot_groups.items():
        parsed_metrics: list[MetricSpec] = []
        raw_metrics:    list[dict]       = group_content.get("metrics", [])

        for metric_data in raw_metrics:
            name   = str(metric_data.get("name", ""))
            suffix = str(metric_data.get("suffix", "")) 
            parsed_metrics.append(MetricSpec(f"{name}_{suffix}" if suffix else name))

        group_config_instance = PlotGroupConfig(
            name    = group_name,
            metrics = parsed_metrics
        )

        plot_groups[group_name] = group_config_instance

    return plot_groups