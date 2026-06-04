"""
CLI Parsing Module for the Workload Profiler.

This module exposes the command-line interface structure using `argparse`.

Expected Syntax:
    [options] <workload> [workload-args]

Core Structural Rules:
 - [positional]:
    - `workload` is a mandatory positional argument
    
    - `workload-args` is an optional positional argument 
                      captures all remaining arguments after the workload, 
                      allowing for flexible argument passing to the workload command
    
 - [options]
    - `-m`, `--metric` - list of metrics separated by comma
                       - options: wall-time, cpu, gpu, memory, thread
                       - default: wall-time (always included)
                       - usage: [--metric wall-time,cpu,gpu,memory,thread]

    - `-wit`, `--warmup-iteration` - number of warmup iterations workload should run
                                   - default: 0
                                   - usage: [--warmup-iteration <n>], where n > 0 
                                   
    - `-it`, `--iteration` - number of iterations workload should run
                           - default: 1
                           - usage: [--iteration <n>], where n > 0

    - `-cmp`, `--compare` - compare current results with n previous results
                          - usage: [--compare <n>], where n > 0

    - `-cmp2`, `--compare-two` - compare two specific versions
                               - usage: [--compare-two <version-1> <version-2>]

    - `-cmpw`, `--compare-with` - compare current version with a specific version
                                - usage: [--compare-with <version>]

    - `-rfmt`, `--report-format` - list of report formats separated by comma 
                                 - format in which comparison data should be reported
                                 - options: csv, json, md 
                                 - default: csv
                                 - usage: [--report-format csv,json,md]

    - `-vfmt`, `--visual-format` - list of visual formats separated by comma
                                 - format in which the comparison data should be displayed
                                 - options: table, chart, graph
                                 - default: graph
                                 - usage [--visual-format table,chart,graph]
    
    - `-help`, `--help` - shows help message and exits
"""

import argparse
from typing import TypeAlias

MetricSelection: TypeAlias = list[str]
ReportFormats:   TypeAlias = list[str]
VisualFormats:   TypeAlias = list[str]

METRICS        = {'wall-time', 'cpu', 'gpu', 'memory', 'thread'}
REPORT_FORMATS = {'csv', 'md', 'json'}
VISUAL_FORMATS = {'table', 'chart', 'graph'}

def parse_args() -> argparse.Namespace:
    parser = create_cli_parser()
    return parser.parse_args()

def create_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        'cli-parser', 
        usage    = '%(prog)s [options] <workload> [workload-args...]', 
        add_help = False
    )

    add_options(parser)
    add_workload_args(parser)

    return parser

def add_workload_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        'workload', 
        help = 'the command or script to execute as the workload'
    )

    parser.add_argument(
        'workload_args', 
        nargs   = argparse.REMAINDER,
        help    = 'arguments for the workload separated by space'
    )

def add_options(parser: argparse.ArgumentParser) -> None:
    options = parser.add_argument_group('options')

    options.add_argument(
        '-m', '--metric',
        type    = parse_metrics,
        default = ['wall-time'], # options: wall-time, cpu, gpu, memory, thread
        help    = 'metrics to collect separated by comma (default: wall-time)'
    )

    options.add_argument(
        '-wit', '--warmup-iteration',
        type    = parse_positive_int,
        default = 0,
        help    = 'define the number of iterations to run the warmup for the workload (default: 0)'
    )

    options.add_argument(
        '-it', '--iteration',
        type    = parse_positive_int,
        default = 1,
        help    = 'define the number of iterations to run the workload (default: 1)'
    )

    options.add_argument(
        '-cmp', '--compare',
        type = parse_positive_int,
        help = 'compare with a specific number of previous runs'
    )

    options.add_argument(
        '-cmp2', '--compare-two',
        nargs = 2,
        help  = 'compare two specific runs by their run IDs'
    )

    options.add_argument(
        '-cmpw', '--compare-with',
        nargs = 1,
        help  = 'compare current run with a specific run by its run ID'
    )

    options.add_argument(
        '-rfmt', '--report-format',
        type    = parse_report_formats,
        default = ['csv'], # options: csv, json, md
        help    = 'report formats separated by comma (default: csv)'
    )

    options.add_argument(
        '-vfmt', '--visual-format',
        type    = parse_visual_formats,
        default = ['graph'], # options: table, chart, graph
        help    = 'visualization formats separated by comma (default: graph)'
    )

    options.add_argument(
        '-h', '--help',
        action = 'help',
        help   = 'show this help message and exit'
    )

def parse_metrics(metrics_str: str) -> MetricSelection:
    metrics = [m.strip() for m in metrics_str.split(',')]

    invalid = set(metrics) - METRICS
    if invalid:
        raise argparse.ArgumentTypeError(
            f'invalid metrics: {", ".join(sorted(invalid))}'
        )

    return metrics

def parse_report_formats(formats_str: str) -> ReportFormats:
    formats = [f.strip() for f in formats_str.split(',')]

    invalid = set(formats) - REPORT_FORMATS
    if invalid:
        raise argparse.ArgumentTypeError(
            f'invalid report formats: {", ".join(sorted(invalid))}'
        )

    return formats

def parse_visual_formats(formats_str: str) -> VisualFormats:
    formats = [f.strip() for f in formats_str.split(',')]

    invalid = set(formats) - VISUAL_FORMATS
    if invalid:
        raise argparse.ArgumentTypeError(
            f'invalid visual formats: {", ".join(sorted(invalid))}'
        )

    return formats

def parse_positive_int(value: str) -> int:
    try:
        ivalue = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f'Invalid integer value: {value}')
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f'Iteration count must be greater than 0, got {ivalue}')
    return ivalue