import argparse
import subprocess
import uuid
import time
from statistics import mean, median, stdev

from cli_parser import parse_args
from measurement import Metadata, Workload, WallTimeMetric
from metric_computer import compute_wall_time_metric

def run_workload():
    args = parse_args()
    wall_times = []

    for _ in range(args.iteration):
        command = [args.workload] + (args.arguments or [])
        
        start = time.perf_counter()
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        duration = (time.perf_counter() - start) * 1000  # milliseconds
        wall_times.append(duration)

    wall_time_metric = compute_wall_time_metric(wall_times)
    print(wall_time_metric)

run_workload()