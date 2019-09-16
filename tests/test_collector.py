#!/usr/bin/env python
# -*- coding: utf-8 -*-
import imp

from sockpuppet import cli

try:
    import unittest.mock as mock
except ImportError:
    import mock as mock

from sockpuppet.collector import SockPuppetCollector, find_flow

__author__ = "Will Szumski"
__copyright__ = "Will Szumski"
__license__ = "apache"


def make_flow(src="192.168.1.1", dst="192.168.1.2", src_port=1,
              dst_port=8888):
    return {
        "src": src,
        "dst": dst,
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


def flow_sample1():
    return {
        "src": "192.168.246.132",
        "src_port": 51056,
        "retrans": 0,
        "dst": "10.42.0.4",
        "cong_algo": "cubic",
        "dst_port": 6800,
        "meminfo": {
            "r": 0,
            "t": 0,
            "w": 0,
            "f": 0
        },
        "iface_idx": 0,
        "inode": 1823686,
        "tcp_info": {
            "delivery_rate": 1095216791572,
            "retrans": 0,
            "data_segs_in": 99,
            "rto": 235.0,
            "segs_in": 1245672,
            "rtt": 34.194,
            "retransmits": 0,
            "bytes_received": 365946358,
            "last_ack_sent": 0,
            "rcv_space": 71459,
            "rcv_mss": 1344,
            "max_pacing_rate": 18446744073709551615,
            "ca_state": 0,
            "min_rtt": 1768060259,
            "segs_out": 1126025,
            "advmss": 1398,
            "state": "established",
            "last_ack_recv": 4038,
            "snd_wscale": 7,
            "pmtu": 1450,
            "busy_time": 1108102138157,
            "bytes_acked": 202480195,
            "rcv_ssthresh": 247929,
            "total_retrans": 1217,
            "last_data_recv": 4038,
            "unacked": 0,
            "fackets": 0,
            "sndbuf_limited": 0,
            "sacked": 0,
            "reordering": 4,
            "pacing_rate": 550271,
            "rttvar": 20.87,
            "snd_cwnd": 7,
            "last_data_sent": 4054,
            "null": 0,
            "rcv_wscale": 7,
            "probes": 0,
            "notsent_bytes": 262154,
            "data_segs_out": 276,
            "snd_ssthresh": 6,
            "lost": 0,
            "ato": 40.0,
            "rwnd_limited": 9581030802091972122,
            "rcv_rtt": 194.25,
            "delivery_rate_app_limited": 0,
            "snd_mss": 1344,
            "opts": [
                "ts",
                "sack"
            ]
        }
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


def test_find_flow_with_dst_range_obj():
    config_range = """
from sockpuppet.collector import xrange
flow_definitions = [
    {
        "class": "example",
        "flows": [
            {
                "flow": "in",
                "src_port": xrange(1235,65536)
            },
            {
                "flow": "out",
                "dst_port": xrange(1,1235)
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
            side_effect=lambda _: make_tcp_flows(
                [make_flow(dst_port=1, dst="192.168.1.2")]))
def test_end_to_end_dst_set(_mock):
    config_basic = """
flow_definitions = [
    {
        "class": "https",
        "flows": [
            {
                "flow": "https-inbound",
                "src_port": 1,
                "dst": {"192.168.1.1", "192.168.1.2"}
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
            side_effect=lambda _: make_tcp_flows(
                [flow_sample1()]))
def test_end_to_end_sample_1(_mock):
    config = cli.load_config("../config/config_sample_1.py")
    collector = SockPuppetCollector(config)
    items = list(collector.collect())
    for i in items:
        for sample in i.samples:
            assert sample.labels["flow"] == "ceph-mds"
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


def test_example_config_parses():
    cli.load_config("../config/config_example.py")


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
