from measurement import WallTimeMetric
from statistics import mean, median, stdev

def compute_wall_time_metric(wall_times: list[float]) -> WallTimeMetric:
    return WallTimeMetric(
        mean_ms   = mean(wall_times),
        median_ms = median(wall_times),
        stddev_ms = stdev(wall_times) if len(wall_times) > 1 else 0.0,
        min_ms    = min(wall_times),
        max_ms    = max(wall_times),
    )