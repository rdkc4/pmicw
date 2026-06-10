#!/usr/bin/env python3

import argparse
from dataclasses import dataclass
import sys

import pandas as pd

from cli_parser import parse_comparison_args
from comparison_config import ThresholdConfig, load_thresholds_config
from deltas_computer import compute_deltas
from measurement_query import execute_query, fetch_last_n, fetch_two
from plot_config import PlotGroupConfig, load_plot_config
from report_visualizer import visualize_report
from report_writer import write_report

@dataclass
class ComparisonDataFrames:
    cmp_df:  pd.DataFrame | None = None
    cmp2_df: pd.DataFrame | None = None
    cmpw_df: pd.DataFrame | None = None

def compare_n(n: int, contender_id: str, path: str, threshold_cfg: dict[str, ThresholdConfig]) -> pd.DataFrame:
    comparison_data = execute_query(fetch_last_n(n, contender_id, path))
    deltas_df       = compute_deltas(comparison_data, contender_id, threshold_cfg)

    return deltas_df

def compare_two(baseline_id: str, contender_id: str, path: str, threshold_cfg: dict[str, ThresholdConfig]) -> pd.DataFrame:
    comparison_data = execute_query(fetch_two(baseline_id, contender_id, path))
    deltas_df       = compute_deltas(comparison_data, contender_id, threshold_cfg)

    return deltas_df

def compare(args: argparse.Namespace, threshold_cfg: dict[str, ThresholdConfig]) -> ComparisonDataFrames:
    cmp_dfs = ComparisonDataFrames()
    if args.compare and args.run_id:
        cmp_dfs.cmp_df  = compare_n(args.compare, args.run_id, args.path, threshold_cfg)
    
    if args.compare_with and args.run_id:
        cmp_dfs.cmpw_df = compare_two(args.compare_with, args.run_id, args.path, threshold_cfg)
    
    if args.compare_two:
        baseline        = args.compare_two[0]
        contender       = args.compare_two[1]
        cmp_dfs.cmp2_df = compare_two(baseline, contender, args.path, threshold_cfg)

    return cmp_dfs

def report(cmp_dfs: ComparisonDataFrames, args: argparse.Namespace) -> None:
    if cmp_dfs.cmp_df is not None and not cmp_dfs.cmp_df.empty:
        write_report(cmp_dfs.cmp_df, args.report_format, f"{args.run_id}_{args.compare}")
    elif args.compare:
        print(f"Failed to write report for cmp", file = sys.stderr)

    if cmp_dfs.cmpw_df is not None and not cmp_dfs.cmpw_df.empty:
        write_report(cmp_dfs.cmpw_df, args.report_format, f"{args.run_id}_{args.compare_with}")
    elif args.compare_with:
        print(f"Failed to write report for cmpw", file = sys.stderr)

    if cmp_dfs.cmp2_df is not None and not cmp_dfs.cmp2_df.empty:
        write_report(cmp_dfs.cmp2_df, args.report_format, f"{args.cmp[1]}_{args.cmp[0]}")
    elif args.compare_two:
        print(f"Failed to write report for cmp2", file = sys.stderr)

def visualize(cmp_dfs: ComparisonDataFrames, args: argparse.Namespace, cfg: dict[str, PlotGroupConfig]) -> None:
    if cmp_dfs.cmp_df is not None and not cmp_dfs.cmp_df.empty:
        visualize_report(cmp_dfs.cmp_df, cfg, args.visual_format)
    elif args.compare:
        print(f"Failed to visualize report for cmp", file = sys.stderr)
    
    if cmp_dfs.cmpw_df is not None and not cmp_dfs.cmpw_df.empty:
        visualize_report(cmp_dfs.cmpw_df, cfg, args.visual_format)
    elif args.compare_with:
        print(f"Failed to visualize report for cmpw", file = sys.stderr)

    if cmp_dfs.cmp2_df is not None and not cmp_dfs.cmp2_df.empty:
        visualize_report(cmp_dfs.cmp2_df, cfg, args.visual_format)
    elif args.compare_two:
        print(f"Failed to visualize report for cmp2", file = sys.stderr)

def main() -> None:
    args          = parse_comparison_args()
    threshold_cfg = load_thresholds_config("config/comparison_threshold_config.yaml")
    plot_cfg      = load_plot_config("config/plot_config.yaml")
    cmp_dfs       = compare(args, threshold_cfg)

    report(cmp_dfs, args)
    visualize(cmp_dfs, args, plot_cfg)

if __name__ == "__main__":
    main()