#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This is a skeleton file that can serve as a starting point for a Python
console script. To run this script uncomment the following line in the
entry_points section in setup.cfg:

    console_scripts =
     fibonacci = sockpuppet.cli:run

Then run `python setup.py install` which will install the command `fibonacci`
inside your current environment.
Besides console scripts, the header (i.e. until _logger...) of this file can
also be used as template for Python modules.

Note: This skeleton file can be safely removed if not needed!
"""
from __future__ import division, print_function, absolute_import

import imp

import argparse
import sys
import logging
import time

from prometheus_client.core import REGISTRY
from prometheus_client import start_http_server


from sockpuppet import __version__
from sockpuppet.collector import SockPuppetCollector

__author__ = "Will Szumski"
__copyright__ = "Will Szumski"
__license__ = "apache"

_logger = logging.getLogger(__name__)


def check_port(value):
    try:
        ivalue = int(value)
        if ivalue <= 0:
            raise ValueError()
        if ivalue > 65535:
            raise ValueError()
        return ivalue
    except ValueError:
        raise argparse.ArgumentTypeError(
            "%s isn't a valid port number" % value)


def check_file(value):
    try:
        load_config(value)
        return value
    except (ValueError, IOError):
        raise argparse.ArgumentTypeError(
            "cannot open config file: %s" % value)


def load_config(path):
    return imp.load_source('config', path)


def parse_args(args):
    """Parse command line parameters

    Args:
      args ([str]): command line parameters as list of strings

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description="Prometheus Socket Statistics exporter")
    parser.add_argument(
        '--version',
        action='version',
        version='sockpuppet {ver}'.format(ver=__version__))
    parser.add_argument(
        '--port',
        dest="port",
        help="listening port",
        type=check_port,
        metavar="PORT",
        default=30000)
    parser.add_argument(
        '--listen-address',
        dest="address",
        help="listening address",
        metavar="ADDR",
        default="127.0.0.1")
    parser.add_argument(
        '--config-path',
        dest="config_path",
        help="config_path",
        type=check_file,
        metavar="PATH",
        default="/etc/sockpuppet/config.py"),
    parser.add_argument(
        '-v',
        '--verbose',
        dest="loglevel",
        help="set loglevel to INFO",
        action='store_const',
        const=logging.INFO)
    parser.add_argument(
        '-vv',
        '--very-verbose',
        dest="loglevel",
        help="set loglevel to DEBUG",
        action='store_const',
        const=logging.DEBUG)
    return parser.parse_args(args)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=loglevel, stream=sys.stdout,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")


def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """
    args = parse_args(args)
    setup_logging(args.loglevel)
    _logger.info("Listening on: {}:{}".format(args.address, args.port))
    start_http_server(args.port, addr=args.address)
    config = load_config(args.config_path)
    collector = SockPuppetCollector(config=config)
    REGISTRY.register(collector)
    while True:
        time.sleep(10)


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
