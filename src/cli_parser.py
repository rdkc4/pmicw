import argparse

def create_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        'cli-parser', 
        usage='%(prog)s workload [workload-options] [options]', 
        add_help=False
    )
    parser.add_argument('workload', help='define the workload')

    add_workload_options(parser)
    add_options(parser)

    return parser

def add_workload_options(parser: argparse.ArgumentParser) -> None:
    workload_options = parser.add_argument_group('workload-options')

    workload_options.add_argument(
        '-args', '--arguments', 
        nargs='*', 
        help='arguments for the workload separated by space'
    )

def add_options(parser: argparse.ArgumentParser) -> None:
    options = parser.add_argument_group('options')

    options.add_argument(
        '-m', '--metric',
        nargs='*',
        default='wall-time',
        choices=['wall-time', 'cpu', 'gpu', 'memory'],
        help='list of metrics separated by space'
    )

    options.add_argument(
        '-it', '--iteration',
        nargs=1,
        type=int,
        default=1,
        help='define the number of iterations to run the workload (default: 1)'
    )

    options.add_argument(
        '-cmp', '--compare',
        nargs=1,
        type=int,
        help='compare current version with n previous versions'
    )

    options.add_argument(
        '-cmp2', '--compare-two',
        nargs=2,
        help='compare two specific versions'
    )

    options.add_argument(
        '-cmpw', '--compare-with',
        nargs=1,
        help='compare current version with a specific version'
    )

    options.add_argument(
        '-rfmt', '--report-format',
        nargs='*',
        choices=['json', 'csv', 'html'],
        help='report formats separated by space'
    )

    options.add_argument(
        '-vfmt', '--visual-format',
        nargs='*',
        choices=['table', 'chart', 'graph'],
        help='visualization formats separated by space'
    )

    options.add_argument(
        '-h', '--help',
        action='help',
        help='show this help message and exit'
    )
