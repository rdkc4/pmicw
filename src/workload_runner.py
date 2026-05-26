import argparse
import json
import subprocess
import time

from cli_parser import parse_args
from metric_computer import (
    compute_core_cpu_metrics, 
    compute_l1_cache_metrics, 
    compute_l2_cache_metrics, 
    compute_llc_cache_metrics, 
    compute_system_metrics, 
    compute_wall_time_metric
)
from record_parser import parse_perf_json_records

def run_workload(args: argparse.Namespace) -> None:
    wall_times: list[float] = []
    perf_records: dict[str, list[dict[str, float]]] = {
        "core":   [],
        "l1":     [],
        "l2":     [],
        "llc":    [],
        "system": []
    }

    perf_event_sets = {
        "core":   "instructions,cycles,branches,branch-misses", 
        "l1":     "L1-dcache-loads,L1-dcache-load-misses", 
        "l2":     "l2_cache_req_stat.all,l2_cache_req_stat.ic_dc_miss_in_l2",
        "llc":    "cache-references,cache-misses",
        "system": "context-switches,page-faults,minor-faults,major-faults"
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

            duration = (time.perf_counter() - start) * 1000  # milliseconds
            wall_times.append(duration)

            json_record = []
            for line in proc.stderr.splitlines():
                try:
                    json_record.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            
            perf_records[event_set_k].append(parse_perf_json_records(json_record))
        

    wall_time_metric                     = compute_wall_time_metric(wall_times)
    ipc_metric, branch_prediction_metric = compute_core_cpu_metrics(perf_records["core"])
    l1_cache_metric                      = compute_l1_cache_metrics(perf_records["l1"])
    l2_cache_metric                      = compute_l2_cache_metrics(perf_records["l2"])
    llc_cache_metric                     = compute_llc_cache_metrics(perf_records["llc"])
    system_metric                        = compute_system_metrics(perf_records["system"])

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