# -*- coding: utf-8 -*-
'''
    pyvantagepro
    ------------

    The public API and command-line interface to PyVantagePro package.

    :copyright: Copyright 2012 Salem Harrache and contributors, see AUTHORS.
    :license: GNU GPL v3.

'''
import os
import argparse

from datetime import datetime

# Make sure the logger is configured early:
from . import VERSION
from .logger import active_logger
from .device import VantagePro2
from .utils import csv_to_dict
from .compat import stdout


NOW = datetime.now().strftime("%Y-%m-%d %H:%M")


def gettime_cmd(args, vp):
    """Gettime command."""
    print(f"{vp.gettime()} - {vp.timezone}")


def settime_cmd(args, vp):
    """Settime command."""
    old_time = vp.gettime()
    vp.settime(datetime.strptime(args.datetime, "%Y-%m-%d %H:%M"))
    print(f"Old value: {old_time} - {vp.timezone}")
    print(f"New value: {vp.gettime()} - {vp.timezone}")


def getinfo_cmd(args, vp):
    """Getinfo command."""
    info = f"Firmware date: {vp.firmware_date}\n"
    info += f"Firmware version: {vp.firmware_version}\n"
    info += f"Diagnostics: {vp.diagnostics}\n"
    print(info)


def getdata_cmd(args, vp):
    """Get real-time data command."""
    args.delim = bytes(args.delim, "utf-8").decode("unicode_escape")
    data = vp.get_current_data().to_csv(delimiter=args.delim)
    args.output.write(data)


def getarchives(args, vp):
    """Getarchive with progress bar if `args.debug` is True."""
    from .utils import ListDict
    if args.debug:
        return vp.get_archives(args.start, args.stop)

    from progressbar import ProgressBar, Percentage, Bar
    archives = ListDict()
    dates = []
    generator = vp._get_archives_generator(args.start, args.stop)
    widgets = ['Archives download: ', Percentage(), ' ', Bar()]
    pbar = ProgressBar(widgets=widgets, maxval=2600).start()
    for step, record in enumerate(generator):
        pbar.update(step)
        if record['Datetime'] not in dates:
            archives.append(record)
            dates.append(record['Datetime'])
    pbar.finish()

    if not archives:
        print("No new records were found")
    elif len(archives) == 1:
        print("1 new record was found")
    else:
        print(f"{len(archives)} new records were found")

    return archives.sorted_by('Datetime')


def getarchives_cmd(args, vp):
    """Getarchive command."""
    args.delim = bytes(args.delim, "utf-8").decode("unicode_escape")
    if args.start is not None:
        args.start = datetime.strptime(args.start, "%Y-%m-%d %H:%M")
    if args.stop is not None:
        args.stop = datetime.strptime(args.stop, "%Y-%m-%d %H:%M")
    args.output.write(getarchives(args, vp).to_csv(delimiter=args.delim))


def update_cmd(args, vp):
    """Update command."""
    # Create file if it doesn't exist
    open(args.db, 'a').close()  # Equivalent to `touch` in Python 3
    with open(args.db, 'r+', newline='') as file_db:
        db = csv_to_dict(file_db, delimiter=args.delim)
        args.start = None
        args.stop = None
        if len(db) > 0:
            db = db.sorted_by("Datetime", reverse=True)
            format = "%Y-%m-%d %H:%M:%S"
            start_date = datetime.strptime(db[0]['Datetime'], format)
            args.start = start_date
            items = getarchives(args, vp)
            file_db.write(items.to_csv(delimiter=args.delim, header=False))
        else:
            file_db.write(getarchives(args, vp).to_csv(delimiter=args.delim))


def get_cmd_parser(cmd, subparsers, help, func):
    """Make a subparser command."""
    parser = subparsers.add_parser(cmd, help=help, description=help)
    parser.add_argument('--timeout', default=10.0, type=float,
                        help="Connection link timeout")
    parser.add_argument('--debug', action="store_true", default=False,
                        help="Display log")
    parser.add_argument('url', action="store",
                        help="Specify URL for connection link. "
                             "E.g. tcp:iphost:port "
                             "or serial:/dev/ttyUSB0:19200:8N1")
    parser.set_defaults(func=func)
    return parser

def getperiod_cmd(args, vp):
    """Getperiod command."""
    print(f"{vp.getperiod()}")

def setperiod_cmd(args, vp):
    """Setperiod command."""
    old_period = vp.getperiod()
    vp.setperiod(args.period)
    print(f"Old value: {old_period}")
    print(f"New value: {args.period}")

def main():
    """Parse command-line arguments and execute VP2 command."""

    parser = argparse.ArgumentParser(
        prog='pyvantagepro',
        description='VantagePro 2 communication tools (New version)'
    )
    parser.add_argument(
        '--version', action='version',
        version=f'PyVantagePro version {VERSION}',
        help='Print PyVantagePro’s version number and exit.'
    )
    subparsers = parser.add_subparsers(title='The PyVantagePro commands')

    # gettime command
    get_cmd_parser('gettime', subparsers,
                   help='Print the current datetime of the station.',
                   func=gettime_cmd)

    # settime command
    subparser = get_cmd_parser('settime', subparsers,
                               help='Set the given datetime argument on the station.',
                               func=settime_cmd)
    subparser.add_argument('datetime', help=f'The chosen datetime value (like: "{NOW}")')

    # getinfo command
    get_cmd_parser('getinfo', subparsers,
                   help='Print VantagePro 2 information.',
                   func=getinfo_cmd)

    # getarchives command
    subparser = get_cmd_parser('getarchives', subparsers,
                               help='Extract archives data from the station '
                                    'between start datetime and stop datetime. '
                                    'By default the entire contents of the '
                                    'data archive will be downloaded.',
                               func=getarchives_cmd)
    subparser.add_argument('--output', action='store', default=stdout,
                           type=argparse.FileType('w'),
                           help='Filename where output is written')
    subparser.add_argument('--start', help=f'The beginning datetime record (like: "{NOW}")')
    subparser.add_argument('--stop', help=f'The stopping datetime record (like: "{NOW}")')
    subparser.add_argument('--delim', action='store', default=",",
                           help='CSV char delimiter')

    # getdata command
    subparser = get_cmd_parser('getdata', subparsers,
                               help='Extract real-time data from the station.',
                               func=getdata_cmd)
    subparser.add_argument('--output', action="store", default=stdout,
                           type=argparse.FileType('w'),
                           help='Filename where output is written')
    subparser.add_argument('--delim', action="store", default=",",
                           help='CSV char delimiter')

    # update command
    subparser = get_cmd_parser('update', subparsers,
                               help='Update CSV database records by automatically '
                                    'fetching new archive records.',
                               func=update_cmd)
    subparser.add_argument('--delim', action="store", default=",",
                           help='CSV char delimiter')
    subparser.add_argument('db', action="store", help='The CSV file database')

    # getperiod command
    get_cmd_parser('getperiod', subparsers,
                   help='Print the current archive period time of the station.',
                   func=getperiod_cmd)

    # setperiod command
    subparser = get_cmd_parser('setperiod', subparsers,
                               help='Set the given archive time period argument on the station.',
                               func=setperiod_cmd)
    subparser.add_argument('period', help='The chosen period value ( Values are 1, 5, 10, 15, 30, 60, and 120)')

    # Parse argv arguments
    args = parser.parse_args()

    if hasattr(args, 'func'):  # Check if a command function is associated
        if getattr(args, 'debug', False):  # Use getattr for optional args
            active_logger()
            vp = VantagePro2.from_url(args.url, args.timeout)
            args.func(args, vp)
        else:
            try:
                vp = VantagePro2.from_url(args.url, args.timeout)
                args.func(args, vp)
            except Exception as e:
                parser.error(f'{e}')
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
