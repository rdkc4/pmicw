#!/usr/bin/env python3

import argparse
import sys

import pandas as pd

from cli_parser import parse_comparison_args
from deltas_computer import compute_deltas
from measurement_query import execute_query, fetch_last_n, fetch_two
from metrics_config import ProfilerConfig, load_config
from report_writer import write_report

def compare_n(n: int, contender_id: str, path: str, cfg: ProfilerConfig) -> pd.DataFrame:
    comparison_data = execute_query(fetch_last_n(n, contender_id, path))
    deltas_df       = compute_deltas(comparison_data, contender_id, cfg)

    return deltas_df

def compare_two(baseline_id: str, contender_id: str, path: str, cfg: ProfilerConfig) -> pd.DataFrame:
    comparison_data = execute_query(fetch_two(baseline_id, contender_id, path))
    deltas_df       = compute_deltas(comparison_data, contender_id, cfg)

    return deltas_df

def report(args: argparse.Namespace, path: str, cfg: ProfilerConfig) -> None:
    if args.compare and args.run_id:
        deltas_df = compare_n(args.compare, args.run_id, path, cfg)

        if not deltas_df.empty:
            write_report(deltas_df, args.report_format, f"{args.run_id}_{args.compare}")
        else:
            print(f"Failed to write report: deltas data frame is empty", file = sys.stderr)

    if args.compare_with and args.run_id:
        deltas_df = compare_two(args.compare_with, args.run_id, path, cfg)

        if not deltas_df.empty:
            write_report(deltas_df, args.report_format, f"{args.run_id}_{args.compare_with}")
        else:
            print(f"Failed to write report: deltas data frame is empty", file = sys.stderr)

    if args.compare_two:
        baseline  = args.compare_two[0]
        contender = args.compare_two[1]
        deltas_df = compare_two(baseline, contender, path, cfg)

        if not deltas_df.empty:
            write_report(deltas_df, args.report_format, f"{contender}_{baseline}")
        else:
            print(f"Failed to write report: deltas data frame is empty", file = sys.stderr)

def main() -> None:
    args = parse_comparison_args()
    path = args.path
    cfg  = load_config("config/metrics_config.yaml")

    report(args, path, cfg)

if __name__ == "__main__":
    main()