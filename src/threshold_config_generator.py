from pathlib import Path
import yaml

from csv_writer import ensure_dir, repo_to_filename
from measurement import Measurement
from paths import THRESHOLDS_DIR

def remove_suffix(name: str, stats_metrics: set) -> None:
    if name.endswith("_stddev"):
        stats_metrics.add(name.removesuffix("_stddev"))
    return

def get_yaml_path(csv_filename: str)-> Path:
    filename = csv_filename.replace(".csv", ".yaml")
    path     = THRESHOLDS_DIR / filename
    ensure_dir(THRESHOLDS_DIR / filename)
    return path

def compute_thresholds(z_score: int, yaml_path: Path | str, measurement: Measurement) -> None:
    """
    If enabled in CLI, computes dynamic noise floor, improvement and regression thresholds based on running workload\n

    z_score: number of standard deviations from the mean considered as noise\n
    yaml_path: path to static threshold config file, used for metric directions and fallbacks for metrics not collecting stddev\n
    measurement: collected measurement from workload runner

    Stores .yaml threshold configuration file in config/thresholds/ using .csv file naming schema
    """

    if z_score == 0:
        return
    
    with open(yaml_path, "r+") as file:
        data = yaml.safe_load(file) or {}
    data.setdefault("workload", {})["name"]       = measurement.workload.name
    data.setdefault("workload", {})["iterations"] = measurement.workload.iterations
    data.setdefault("workload", {})["run_id"]     = str(measurement.metadata.run_id)

    for seg_name, seg_metrics in measurement.metrics.items(): 
        stats_metrics = set()
        for full_metric_name in seg_metrics.record.keys():
            remove_suffix(full_metric_name, stats_metrics)

        for metric_name in stats_metrics:
            stddev    = measurement.metrics[seg_name].record.get(f"{metric_name}_stddev", -1.0)
            mean      = measurement.metrics[seg_name].record.get(f"{metric_name}_mean", -1.0)
            coeff_var = stddev/mean if mean > 0 else -1 #coefficient of variation
            
            if metric_name not in data.get("thresholds", {}):
                data.setdefault("thresholds", {})[metric_name] = {}
            
            if coeff_var >= 0:
                #adjacent ranges, same threshold pct
                data["thresholds"][metric_name]["noise_floor_pct"]           = z_score * coeff_var * 100
                data["thresholds"][metric_name]["improvement_threshold_pct"] = z_score * coeff_var * 100
                data["thresholds"][metric_name]["regression_threshold_pct"]  = z_score * coeff_var * 100    

    csv_filename = repo_to_filename(
        measurement.metadata.version.repository, 
        measurement.workload.name, 
        measurement.to_csv_header()
    )

    path = get_yaml_path(csv_filename)

    with open(f"{path}", "w") as file:
        yaml.safe_dump(data, file, default_flow_style = False)