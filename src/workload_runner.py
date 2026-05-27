import argparse
import json
import subprocess
import time

from cli_parser import parse_args
from measurement import Metadata
from metric_computer import (
    compute_wall_time_metric,
    compute_execution_core_metrics,
    compute_private_cache_metrics,
    compute_shared_cache_metrics
)
from record_parser import parse_perf_json_records

def run_workload(args: argparse.Namespace) -> None:
    wall_times:   list[float] = []
    perf_records: dict[str, list[dict[str, float]]] = {
        "execution_core": [],
        "private_caches": [],
        "shared_caches":  []
    }

    perf_event_sets = {
        "execution_core": "'{instructions,cycles,branches,branch-misses,context-switches,page-faults,minor-faults,major-faults}'", 
        "private_caches": "'{L1-dcache-loads,L1-dcache-load-misses,l2_cache_req_stat.all,l2_cache_req_stat.ic_dc_miss_in_l2}'", 
        "shared_caches":  "'{cache-references,cache-misses}'"
    }

    for event_set_k, event_set in perf_event_sets.items():
        command = [
            "perf", "stat",
            "-j",
            "-e", event_set,
            args.workload
        ] + (args.arguments or [])

        for _ in range(args.iteration):
            start = time.perf_counter()
            
            proc = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            duration_ms = (time.perf_counter() - start) * 1000
            wall_times.append(duration_ms)

            json_record = []
            for line in proc.stderr.splitlines():
                try:
                    json_record.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            
            perf_records[event_set_k].append(parse_perf_json_records(json_record))
        
    wall_time_metric                                    = compute_wall_time_metric(wall_times)
    ipc_metric, branch_prediction_metric, system_metric = compute_execution_core_metrics(perf_records["execution_core"])
    l1_cache_metric, l2_cache_metric                    = compute_private_cache_metrics(perf_records["private_caches"])
    llc_cache_metric                                    = compute_shared_cache_metrics(perf_records["shared_caches"])

    print(wall_time_metric)
    print(ipc_metric)
    print(branch_prediction_metric)
    print(l1_cache_metric)
    print(l2_cache_metric)
    print(llc_cache_metric)
    print(system_metric)

def main():
    args = parse_args()
    run_workload(args)

if __name__ == "__main__":
    main()