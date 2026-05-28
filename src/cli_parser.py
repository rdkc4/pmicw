"""
CLI Parsing Module for the Workload Profiler.

This module exposes the command-line interface structure using `argparse`.

Expected Syntax:
    <workload> [workload-options] [options]

Core Structural Rules:
 - [positional]:
    - `workload` is a mandatory positional argument
 
 - [workload-options]:
    - `-args`, `--arguments` - list of arguments for the workload separated by space
                             - usage: [--arguments <argument-1> <argument-2> ... <argument-n>]

    - `-it`, `--iteration` - number of iterations workload should run
                           - default: 1
                           - usage: [--iteration <n>], where n > 0

    - `-wit`, `--warmup-iteration` - number of warmup iterations workload should run
                                   - default: 0
                                   - usage: [--warmup-iteration <n>], where n > 0 
    
 - [options]
    - `-m`, `--metric` - list of metrics separated by space
                       - options: wall-time, cpu, gpu, memory
                       - default: wall-time (always included)
                       - usage: [--metric wall-time cpu gpu memory]

    - `-cmp`, `--compare` - compare current results with n previous results
                          - usage: [--compare <n>], where n > 0

    - `-cmp2`, `--compare-two` - compare two specific versions
                               - usage: [--compare-two <version-1> <version-2>]

    - `-cmpw`, `--compare-with` - compare current version with a specific version
                                - usage: [--compare-with <version>]

    - `-rfmt`, `--report-format` - list of report formats separated by space 
                                 - format in which comparison data should be reported
                                 - options: csv, json, html 
                                 - default: csv
                                 - usage: [--report-format csv json html]

    - `-vfmt`, `--visual-format` - list of visual formats separated by space
                                 - format in which the comparison data should be displayed
                                 - options: table, chart, graph
                                 - default: graph
                                 - usage [--visual-format table chart graph]
    
    - `-help`, `--help` - shows help message and exits
"""

import argparse

def parse_args() -> argparse.Namespace:
    parser = create_cli_parser()
    return parser.parse_args()

def create_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        'cli-parser', 
        usage    = '%(prog)s workload [workload-options] [options]', 
        add_help = False
    )

    parser.add_argument(
        'workload', 
        help = 'the command or script to execute as the workload'
    )

    add_workload_options(parser)
    add_options(parser)

    return parser

def add_workload_options(parser: argparse.ArgumentParser) -> None:
    workload_options = parser.add_argument_group('workload-options')

    workload_options.add_argument(
        '-args', '--arguments', 
        nargs = '*', 
        help  = 'arguments for the workload separated by space'
    )

    workload_options.add_argument(
        '-it', '--iteration',
        type    = positive_int,
        default = 1,
        help    = 'define the number of iterations to run the workload (default: 1)'
    )

    workload_options.add_argument(
        '-wit', '--warmup-iteration',
        type    = positive_int,
        default = 0,
        help    = 'define the number of iterations to run the warmup for the workload (default: 0)'
    )

def add_options(parser: argparse.ArgumentParser) -> None:
    options = parser.add_argument_group('options')

    options.add_argument(
        '-m', '--metric',
        nargs   = '*',
        default = ['wall-time'],
        choices = ['wall-time', 'cpu', 'gpu', 'memory'],
        help    = 'metrics to collect separated by space (default: wall-time)'
    )

    options.add_argument(
        '-cmp', '--compare',
        type = positive_int,
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
        nargs   = '*',
        default = ['csv'],
        choices = ['json', 'csv', 'html'],
        help    = 'report formats separated by space (default: csv)'
    )

    options.add_argument(
        '-vfmt', '--visual-format',
        nargs   = '*',
        default = ['graph'],
        choices = ['table', 'chart', 'graph'],
        help    = 'visualization formats separated by space (default: graph)'
    )

    options.add_argument(
        '-h', '--help',
        action = 'help',
        help   = 'show this help message and exit'
    )

def positive_int(value: str) -> int:
    try:
        ivalue = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f'Invalid integer value: {value}')
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f'Iteration count must be greater than 0, got {ivalue}')
    return ivalue