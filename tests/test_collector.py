#!/usr/bin/env python
# -*- coding: utf-8 -*-
import imp

try:
    import unittest.mock as mock
except ImportError:
    import mock as mock

from sockpuppet.collector import SockPuppetCollector, find_flow

__author__ = "Will Szumski"
__copyright__ = "Will Szumski"
__license__ = "apache"


def make_flow(src="192.168.1.1", dest="192.168.1.2", src_port=1,
              dst_port=8888):
    return {
        "src": src,
        "dst": dest,
        "src_port": src_port,
        "dst_port": dst_port,
        "inode": 582720,
        "iface_idx": 0,
        "retrans": 0,
        "meminfo": {
            "r": 0,
            "w": 0,
            "f": 4096,
            "t": 0
        },
        "tcp_info": {
            "state": "established",
            "ca_state": 0,
            "retransmits": 0,
            "probes": 0,
            "null": 0,
            "opts": [
                "ts",
                "sack"
            ],
            "snd_wscale": 8,
            "delivery_rate_app_limited": 1,
            "rto": 226.666,
            "ato": 40.0,
            "snd_mss": 1418,
            "rcv_mss": 1139,
            "unacked": 0,
            "sacked": 0,
            "lost": 0,
            "retrans": 0,
            "fackets": 0,
            "last_data_sent": 145067,
            "last_ack_sent": 0,
            "last_data_recv": 5484,
            "last_ack_recv": 6400,
            "pmtu": 1500,
            "rcv_ssthresh": 104416,
            "rtt": 23.44,
            "rttvar": 2.68,
            "snd_ssthresh": None,
            "snd_cwnd": 10,
            "advmss": 1448,
            "reordering": 3,
            "rcv_rtt": 15554.25,
            "rcv_space": 19531,
            "total_retrans": 0,
            "pacing_rate": 1209878,
            "max_pacing_rate": 18446744073709551615,
            "bytes_acked": 20540,
            "bytes_received": 45372,
            "segs_out": 570,
            "segs_in": 583,
            "notsent_bytes": 0,
            "min_rtt": 19257,
            "data_segs_in": 502,
            "data_segs_out": 83,
            "delivery_rate": 143978,
            "busy_time": 2053128,
            "rwnd_limited": 0,
            "sndbuf_limited": 0,
            "rcv_wscale": 8
        },
        "cong_algo": "cubic"
    }


def make_tcp_flows(flows):
    return {"TCP": {
        "flows": flows
    }}


def mock_module(code):
    module = imp.new_module('mymodule')
    exec(code, module.__dict__)
    return module


def test_find_flow_with_src_range():
    config_range = """
flow_definitions = [
    {
        "class": "example",
        "flows": [
            {
                "flow": "in",
                "src_port": "1:1234"
            },
            {
                "flow": "out",
                "dst_port": "1235:65535"
            },
        ],
    },
]
"""
    config = mock_module(config_range)
    labels_end = {
        "src_port": 1234,
    }
    labels_start = {
        "src_port": 1,
    }
    labels_out_of_range = {
        "src_port": 1337,
    }
    a, b = find_flow(config.flow_definitions, labels_start)
    assert a is not None
    assert b is not None
    a, b = find_flow(config.flow_definitions, labels_end)
    assert a is not None
    assert b is not None
    a, b = find_flow(config.flow_definitions, labels_out_of_range)
    assert a is None
    assert b is None


def test_find_flow_with_no_labels():
    config_range = """
flow_definitions = [
    {
        "class": "example",
        "flows": [
            {
                "flow": "in",
                "src_port": "1:1234"
            },
            {
                "flow": "out",
                "dst_port": "1235:65535"
            },
        ],
    },
]
"""
    config = mock_module(config_range)
    a, b = find_flow(config.flow_definitions, {})
    assert a is None
    assert b is None


def test_find_flow_with_int():
    config_range = """
flow_definitions = [
    {
        "class": "example",
        "flows": [
            {
                "flow": "in",
                "src_port": 1
            },
        ],
    },
]
"""
    config = mock_module(config_range)
    a, b = find_flow(config.flow_definitions, {"src_port": 1})
    assert a is not None
    assert b is not None


def test_find_flow_with_string():
    config_range = """
flow_definitions = [
    {
        "class": "example",
        "flows": [
            {
                "flow": "in",
                "src_port": "1"
            },
        ],
    },
]
"""
    config = mock_module(config_range)
    a, b = find_flow(config.flow_definitions, {"src_port": 1})
    assert a is None
    assert b is None


def test_find_flow_with_dst_range():
    config_range = """
flow_definitions = [
    {
        "class": "example",
        "flows": [
            {
                "flow": "in",
                "src_port": "1235:65535"
            },
            {
                "flow": "out",
                "dst_port": "1:1234"
            },
        ],
    },
]
"""
    config = mock_module(config_range)
    labels_end = {
        "dst_port": 1234,
    }
    labels_start = {
        "dst_port": 1,
    }
    labels_out_of_range = {
        "dst_port": 1337,
    }
    a, b = find_flow(config.flow_definitions, labels_start)
    assert a is not None
    assert b is not None
    a, b = find_flow(config.flow_definitions, labels_end)
    assert a is not None
    assert b is not None
    a, b = find_flow(config.flow_definitions, labels_out_of_range)
    assert a is None
    assert b is None


@mock.patch('sockpuppet.collector.get_socket_stats',
            side_effect=lambda _: make_tcp_flows([make_flow(src_port=1)]))
def test_end_to_end(_mock):
    config_basic = """
flow_definitions = [
    {
        "class": "https",
        "flows": [
            {
                "flow": "https-inbound",
                "src_port": 1
            },
        ]
    },
]
"""
    config = mock_module(config_basic)
    collector = SockPuppetCollector(config)
    items = list(collector.collect())
    assert len(items) == len(collector.metric_definitions)


@mock.patch('sockpuppet.collector.get_socket_stats',
            side_effect=lambda _: make_tcp_flows([make_flow(src_port=2)]))
def test_end_to_end_negative(_mock):
    config_basic = """
flow_definitions = [
    {
        "class": "https",
        "flows": [
            {
                "flow": "https-inbound",
                "src_port": 1
            },
        ]
    },
]
"""
    config = mock_module(config_basic)
    collector = SockPuppetCollector(config)
    items = list(collector.collect())
    assert len(items) == 0


def test_collect():
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
    config = mock_module(config_basic)
    collector = SockPuppetCollector(config)
    collector.collect()
