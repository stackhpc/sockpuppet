import subprocess
import logging
import json
import jmespath

from prometheus_client.metrics_core import GaugeMetricFamily

_logger = logging.getLogger(__name__)

# TODO: move this to a config file
flow_definitions = [
    {
        "class": "vpn",
        "flows": [
            {
                "flow": "vpn-inbound",
                "src_port": "1194"
            },
            {
                "flow": "vpn-outbound",
                "dst_port": "1194"
            },
        ],
    },
    # run this on the compute nodes
    {
        "class": "ceph",
        "flows": [
            {
                "flow": "ceph-mon",
                "dst_port": "6789",
            },
            {
                "flow": "ceph-mds",
                "dst_port": "6800",
            },
            # By default, Ceph OSD Daemons bind to the first available ports
            # on a Ceph Node beginning at port 6800
            {
                "flow": "ceph-osd-outbound",
                "dst_port": "6800:7300",
            },
            {
                "flow": "ceph-osd-inbound",
                "src_port": "6800:7300"
            },
        ]
    },
    # run this on the monitor nodes
    {
        "class": "ceph",
        "flows": [
            {
                "flow": "ceph-mon-inbound",
                "src_port": "6789",
            },
            {
                "flow": "ceph-mon-outbound",
                "dst_port": "6789",
            },
        ]
    },
    # run this on the mds nodes
    {
        "class": "ceph",
        "flows": [
            {
                "flow": "ceph-mds-inbound",
                "dst_port": "6800",
            },
            {
                "flow": "ceph-mds-outbound",
                "src_port": "6800",
            },
        ]
    },
    # class
    {
        "class": "https",
        "flows": [
            {
                "flow": "ceph-mds-inbound",
                "dst_port": "443:443",
            },
            {
                "flow": "ceph-mds-outbound",
                "src_port": "443:443",
            },
        ]
    },
]

_allowed_selectors = ["src_port", "dst_port"]


class SSContext:
    def __init__(self, tcp=False, udp=False, process=False):
        self.tcp = tcp
        self.udp = udp
        self.process = process


def get_socket_stats(context, retry=0):
    args = []
    if context.tcp:
        args += ["-t"]
    if context.udp:
        args += ["-u"]
    if context.process:
        args += ["-p"]
    cmd = ["ss2"] + args
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        _logger.error("return code non-zero: {}".format(result.stderr))
        if retry < 1 and context.process:
            _logger.error("Gathering process information requires root "
                          "privileges, auto disabling process gathering.")
            context.process = False
            return get_socket_stats(context, retry=retry + 1)
        else:
            return
    return json.loads(result.stdout)


def find_flow(definitions, labels):
    def test(flow, item):
        if item not in flow:
            return True
        if (item == "src_port" or item == "dst_port") and ":" in flow[item]:
            split = flow[item].split(":")
            maximum = split[0]
            minimum = split[1]
            return maximum >= labels[item] >= minimum
        return flow[item] == labels[item]

    for flow_definition in definitions:
        for flow in flow_definition["flows"]:
            if all([test(flow, x) for x in _allowed_selectors]):
                return flow_definition, flow
    return None, None


def _create_labels(definitions, name):
    for definition in definitions:
        if definition["name"] == name:
            # add mandatory labels
            return ["class", "flow"] + list(definition["label_names"])

#class TCPMetric(object):
#    def __init__(self):

class SockPuppetCollector(object):

    def __init__(self):
        self.context = SSContext(tcp=True, process=True)
        self.metric_definitions = [
            {
                "name": "rtt",
                "path": jmespath.compile("tcp_info.rtt"),
                "create": self.basic_gauge,
                "label_names": ["src", "src_port", "dest", "dst_port"],
                "label_paths": [
                    jmespath.compile("src"),
                    jmespath.compile("src_port"),
                    jmespath.compile("dst"),
                    jmespath.compile("dst_port"),
                ]
            }
        ]
        self.metric_registry = {
            "rtt": GaugeMetricFamily(
                "sockpuppet_tcp_rtt",
                "TCP Round Trip Time",
                labels=_create_labels(self.metric_definitions, "rtt"))
        }

    def basic_gauge(self, gauge, value, labels):
        gauge.add_metric(labels, value)

    def poll(self):
        stats = get_socket_stats(self.context)
        if stats:
            for flow in stats["TCP"]["flows"]:
                self.process_tcp_flow(flow)

    def collect(self):
        for value in self.metric_registry.values():
            yield value

    def process_tcp_flow(self, flow):
        for definition in self.metric_definitions:
            value = definition["path"].search(flow)
            if value is not None:
                create = definition["create"]
                metric_name = definition["name"]
                metric = self.metric_registry[metric_name]
                label_names = definition["label_names"]
                label_values = [str(x.search(flow)) for x in
                                definition["label_paths"]]
                labels = dict(zip(label_names, label_values))
                matching_def, matching_flow = find_flow(
                    flow_definitions,
                    labels
                )
                if matching_flow:
                    # Add mandatory labels
                    class_name = matching_def["class"]
                    flow_name = matching_flow["flow"]
                    all_labels = [class_name, flow_name] + label_values
                    create(metric, value, all_labels)
