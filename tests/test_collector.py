#!/usr/bin/env python
# -*- coding: utf-8 -*-
import imp

from sockpuppet.collector import SockPuppetCollector

__author__ = "Will Szumski"
__copyright__ = "Will Szumski"
__license__ = "apache"


config_basic = """
flow_definitions = [
    {
        "class": "https",
        "flows": [
            {
                "flow": "https-inbound",
                "src_port": "443"
            },
            {
                "flow": "https-outbound",
                "dst_port": "443"
            },
        ],
    },
]
"""


def mock_module(code):
    module = imp.new_module('mymodule')
    exec(code, module.__dict__)
    return module


def test_poll():
    config = mock_module(config_basic)
    collector = SockPuppetCollector(config)
    collector.collect()
