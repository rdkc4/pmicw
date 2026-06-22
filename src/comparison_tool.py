#!/usr/bin/env python3

import argparse
import sys
import pandas as pd

from cli_parser import parse_comparison_args
from comparison_config import ThresholdConfig, load_thresholds_config
from comparison_context import ComparisonDataFrames, ComparisonReportGroups, ComparisonVisualGroups
from dashboard_generator import generate_dashboard
from deltas_computer import compute_deltas
from measurement_query import execute_query, fetch_last_n, fetch_two
from plot_config import PlotGroupConfig, load_plot_config
from report_visualizer import visualize_report
from report_writer import write_report

def compare_n(
    n:             int, 
    contender_id:  str, 
    workload_name: str, 
    path:          str, 
    threshold_cfg: dict[str, ThresholdConfig]
) -> pd.DataFrame:
    """
    Compares last N measurements with contender

    n: number of previous measurements\n
    contender_id: id of the contender run\n
    workload_name: name of the workload that is being benchmarked\n
    path: path to a csv storage of the results\n
    threshold_cfg: configuration defining the thresholds of the metrics

    Returns the data frame containing comparison data,
    or empty data frame if contender wasn't found or if contender is the only run
    """
    comparison_data = execute_query(fetch_last_n(n, contender_id, workload_name, path))
    deltas_df       = compute_deltas(comparison_data, contender_id, threshold_cfg)

    return deltas_df

def compare_two(
    baseline_id:   str, 
    contender_id:  str, 
    workload_name: str, 
    path:          str, 
    threshold_cfg: dict[str, ThresholdConfig]
) -> pd.DataFrame:
    """
    Compares two measurements

    baseline_id: id of the baseline run\n
    contender_id: id of the contender run\n
    workload_name: name of the workload that is being benchmarked\n
    path: path to a csv storage of the results\n
    threshold_cfg: configuration defining the thresholds of the metrics

    Returns the data frame containing comparison data,
    or empty data frame if either baseline or contender weren't found
    """
    comparison_data = execute_query(fetch_two(baseline_id, contender_id, workload_name, path))
    deltas_df       = compute_deltas(comparison_data, contender_id, threshold_cfg)

    return deltas_df

def compare(args: argparse.Namespace, threshold_cfg: dict[str, ThresholdConfig]) -> ComparisonDataFrames:
    """
    Entry point for comparison data computation

    args: parsed CLI arguments\n
    threshold_cfg: configuration defining the thresholds of the metrics

    Performs compare, compare-with and compare-two, depending on the options selected via CLI

    Returns comparison data frames grouped by comparison type
    """
    cmp_dfs = ComparisonDataFrames()
    if args.compare and args.run_id:
        cmp_dfs.cmp_df  = compare_n(args.compare, args.run_id, args.workload_name, args.path, threshold_cfg)
    
    if args.compare_with and args.run_id:
        cmp_dfs.cmpw_df = compare_two(args.compare_with, args.run_id, args.workload_name, args.path, threshold_cfg)
    
    if args.compare_two:
        baseline        = args.compare_two[0]
        contender       = args.compare_two[1]
        cmp_dfs.cmp2_df = compare_two(baseline, contender, args.workload_name, args.path, threshold_cfg)

    return cmp_dfs

def report(cmp_dfs: ComparisonDataFrames, args: argparse.Namespace) -> ComparisonReportGroups:
    """
    Entry point for comparison report generation

    cmp_dfs: comparison data frames\n
    args: parsed CLI arguments

    Returns comparison reports grouped by comparison type
    """
    report_groups = ComparisonReportGroups()

    if cmp_dfs.cmp_df is not None and not cmp_dfs.cmp_df.empty:
        report_groups.cmp = write_report(cmp_dfs.cmp_df, args.report_format, args.workload_name, "cmp")
    elif args.compare:
        print(f"Failed to write report for cmp", file = sys.stderr)

    if cmp_dfs.cmpw_df is not None and not cmp_dfs.cmpw_df.empty:
        report_groups.cmpw = write_report(cmp_dfs.cmpw_df, args.report_format, args.workload_name, "cmpw")
    elif args.compare_with:
        print(f"Failed to write report for cmpw", file = sys.stderr)

    if cmp_dfs.cmp2_df is not None and not cmp_dfs.cmp2_df.empty:
        report_groups.cmp2 = write_report(cmp_dfs.cmp2_df, args.report_format, args.workload_name, "cmp2")
    elif args.compare_two:
        print(f"Failed to write report for cmp2", file = sys.stderr)

    return report_groups

def visualize(
    cmp_dfs:  ComparisonDataFrames, 
    args:     argparse.Namespace, 
    plot_cfg: dict[str, PlotGroupConfig]
) -> ComparisonVisualGroups:
    """
    Entry point for comparison visualization

    cmp_dfs: comparison data frames\n
    args: parsed CLI arguments\n
    plot_cfg: configuration defining metrics that should be displayed

    Returns comparison visualization grouped by comparison type
    """
    visual_groups = ComparisonVisualGroups()

    if cmp_dfs.cmp_df is not None and not cmp_dfs.cmp_df.empty:
        visual_groups.cmp = visualize_report(cmp_dfs.cmp_df, plot_cfg, args.visual_format)
    elif args.compare:
        print(f"Failed to visualize report for cmp", file = sys.stderr)
    
    if cmp_dfs.cmpw_df is not None and not cmp_dfs.cmpw_df.empty:
        visual_groups.cmpw = visualize_report(cmp_dfs.cmpw_df, plot_cfg, args.visual_format)
    elif args.compare_with:
        print(f"Failed to visualize report for cmpw", file = sys.stderr)

    if cmp_dfs.cmp2_df is not None and not cmp_dfs.cmp2_df.empty:
        visual_groups.cmp2 = visualize_report(cmp_dfs.cmp2_df, plot_cfg, args.visual_format)
    elif args.compare_two:
        print(f"Failed to visualize report for cmp2", file = sys.stderr)

    return visual_groups

def main() -> None:
    args          = parse_comparison_args()
    threshold_cfg = load_thresholds_config(args, "config/comparison_threshold_config.yaml")
    plot_cfg      = load_plot_config("config/plot_config.yaml")
    cmp_dfs       = compare(args, threshold_cfg)

    report_groups = report(cmp_dfs, args)
    visual_groups = visualize(cmp_dfs, args, plot_cfg)
    generate_dashboard(report_groups, visual_groups, args.workload_name)

if __name__ == "__main__":
    main()