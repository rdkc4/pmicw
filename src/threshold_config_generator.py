from pathlib import Path
import sys

import yaml

from cli_parser import parse_runner_args
from command_config import load_command_config
# from comparison_config import SUFFIXES
from measurement import Measurement, Metrics
from metric_config import load_config

from workload_runner import assemble_measurement, assemble_workload, run_workload, setup_workload_context

#for now computes thresholds for metrics with standard deviation collected
def remove_suffix(name: str, stats_metrics: set) -> None:
    if name.endswith("_stddev"):
        stats_metrics.add(name.removesuffix("_stddev"))
    return

def store_computed_thresholds(yaml_path: Path | str, measurement: Measurement) -> None:
    
    with open(yaml_path, "r+") as file:
        data = yaml.safe_load(file) or {}
    data.setdefault("workload", {})["name"] = measurement.workload.name
    data.setdefault("workload", {})["iterations"] = measurement.workload.iterations

    for seg_name, seg_metrics in measurement.metrics.items(): 

        stats_metrics = set()
        for full_metric_name, metric_value in seg_metrics.record.items():
            remove_suffix(full_metric_name, stats_metrics)

        for metric_name in stats_metrics:
            if metric_name not in data.get("thresholds", {}):
                data.setdefault("thresholds", {})[metric_name] = {}
            data["thresholds"][metric_name]["computed_noise_floor"] = 2 * measurement.metrics[seg_name].record.get(f"{metric_name}_stddev", -1.0)
            # data["thresholds"][metric_name]["computed_improvement_threshold"] = TODO
            # data["thresholds"][metric_name]["computed_regression_threshold"] = TODO

    
    with open(yaml_path, "w") as file:
        yaml.safe_dump(data, file, default_flow_style=False)
    return


def main():
    args     = parse_runner_args()
    cfg      = load_config("config/metric_config.yaml")
    cmd_cfg  = load_command_config("config/command_config.yaml")
    ctx      = setup_workload_context(args)
    workload = assemble_workload(args)

    try:
        metrics = run_workload(ctx, cfg, cmd_cfg)

    except RuntimeError as e:
        print(f"Error in threshold generator: {e}", file = sys.stderr)
        sys.exit(1)

    measurement = assemble_measurement(workload, metrics, cfg)

    store_computed_thresholds("config/computed_threshold_config.yaml", measurement)


if __name__ == "__main__":
    main()