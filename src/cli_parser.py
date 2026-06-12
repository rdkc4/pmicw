"""
CLI Parsing Module for the Workload Profiler.

This module exposes the command-line interface structure using `argparse`.


CLI Parser for Workload Runner:

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

    - `-help`, `--help` - shows help message and exits


CLI Parser for Comparison Tool:

Expected Syntax:
    [options]

Core Structural Rules:
 - [options]
    - `-w`,   `--workload-name` - name of the workload that is being compared
                                - required
                                - usage: [--workload-name <name>]

    - `-p`,   `--path`    - path to csv where results of the measurements are stored
                          - required
                          - usage: [--path <path>]

    - `-rid`, `--run-id`  - id of the contender run
                          - usage: [--run-id <id>]

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
from enum import StrEnum

class MetricOptions(StrEnum):
    """
    Metric Option entries for Workload Runner's CLI parser
    """
    WALL_TIME = 'wall-time'
    CPU       = 'cpu'
    GPU       = 'gpu'
    MEMORY    = 'memory'
    THREAD    = 'thread'

class ReportFormatOptions(StrEnum):
    """
    Report Format Options for Comparison Tool's CLI parser
    """
    CSV  = 'csv'
    MD   = 'md'
    JSON = 'json'

class VisualFormatOptions(StrEnum):
    """
    Visualization Format Options for Comparison Tool's CLI parser
    """
    TABLE = 'table'
    CHART = 'chart'
    GRAPH = 'graph'

MetricSelection: TypeAlias = list[MetricOptions]
ReportFormats:   TypeAlias = list[ReportFormatOptions]
VisualFormats:   TypeAlias = list[VisualFormatOptions]

def parse_runner_args() -> argparse.Namespace:
    """
    Entry point for Workload Runner argument parser

    Creates an instance of a parser and parses arguments received from CLI

    Returns argparse.Namespace containing all arguments passed via CLI
    """
    parser = create_runner_cli_parser()
    return parser.parse_args()

def create_runner_cli_parser() -> argparse.ArgumentParser:
    """
    Creates the instance of the Workload Runner's CLI parser

    Appends Workload Runner's options, workload, and workload args
    
    Expected syntax: [options] <workload> [workload-args...]

    All options must be passed before workload,
    any argument after the workload will be treated as workload argument

    Workload arguments are not handled by Workload Runner parser,
    they are just passed to workload

    Returns instance of the Workload Runner parser
    """
    parser = argparse.ArgumentParser(
        'runner-cli-parser',
        usage    = '%(prog)s [options] <workload> [workload-args...]',
        add_help = False
    )

    add_runner_options(parser)
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

def add_runner_options(parser: argparse.ArgumentParser) -> None:
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
        '-h', '--help',
        action = 'help',
        help   = 'show this help message and exit'
    )

def parse_metrics(metrics_str: str) -> MetricSelection:
    """
    Parses Workload Runner's metric selection

    Throws if any invalid metrics are listed

    Returns list of selected metric options
    """
    metrics = [metric.strip() for metric in metrics_str.split(',')]

    invalid = set(metrics) - set(MetricOptions)
    if invalid:
        raise argparse.ArgumentTypeError(f'invalid metrics: {", ".join(invalid)}')
    
    # safe to cast since "invalid" will capture all invalid metric entries
    return [MetricOptions(metric) for metric in metrics]

def parse_comparison_args() -> argparse.Namespace:
    """
    Entry point for Comparison Tool argument parser

    Creates an instance of a parser and parses arguments received from CLI

    Returns argparse.Namespace containing all arguments passed via CLI
    """
    parser = create_comparison_cli_parser()
    return parser.parse_args()

def create_comparison_cli_parser() -> argparse.ArgumentParser:
    """
    Creates the instance of the Comparison Tool's CLI parser

    Appends Comparison Tool's options
    
    Expected syntax: [options]

    `--path` and `--workload-name` options are mandatory

    Returns instance of the Comparison Tool parser
    """
    parser = argparse.ArgumentParser(
        'comparison-cli-parser',
        usage    = '%(prog)s [options]',
        add_help = False
    )
    add_comparison_options(parser)

    return parser

def add_comparison_options(parser: argparse.ArgumentParser) -> None:
    options = parser.add_argument_group('options')

    options.add_argument(
        '-wn', '--workload-name',
        required = True,
        help     = 'name of the workload that is being compared'
    )

    options.add_argument(
        '-p', '--path',
        required = True,
        help     = 'path to csv file of the results'
    )

    options.add_argument(
        '-rid', '--run-id',
        help = 'id of the contender run'
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
        type = str,
        help = 'compare current run with a specific run by its run ID'
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

def parse_report_formats(formats_str: str) -> ReportFormats:
    """
    Parses Comparison Tool's report format selection

    Throws if any invalid report formats are listed

    Returns list of selected report formats
    """
    formats = [fmt.strip() for fmt in formats_str.split(',')]

    invalid = set(formats) - set(ReportFormatOptions)
    if invalid:
        raise argparse.ArgumentTypeError(f'invalid report formats: {", ".join(sorted(invalid))}')

    # safe to cast since "invalid" will capture all invalid metric entries
    return [ReportFormatOptions(fmt) for fmt in formats]

def parse_visual_formats(formats_str: str) -> VisualFormats:
    """
    Parses Comparison Tool's visual format selection

    Throws if any invalid visual formats are listed

    Returns list of selected visual formats
    """
    formats = [fmt.strip() for fmt in formats_str.split(',')]

    invalid = set(formats) - set(VisualFormatOptions)
    if invalid:
        raise argparse.ArgumentTypeError(f'invalid visual formats: {", ".join(sorted(invalid))}')

    # safe to cast since "invalid" will capture all invalid metric entries
    return [VisualFormatOptions(fmt) for fmt in formats]

def parse_positive_int(value: str) -> int:
    try:
        ivalue = int(value)

    except ValueError:
        raise argparse.ArgumentTypeError(f'Invalid integer value: {value}')
    
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f'Iteration count must be greater than 0, got {ivalue}')

    return ivalue