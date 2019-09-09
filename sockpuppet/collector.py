import subprocess
import logging
import json
import jmespath

from prometheus_client.metrics_core import GaugeMetricFamily

_logger = logging.getLogger(__name__)

_allowed_selectors = ["src_port", "dst_port"]


class SSContext:
    def __init__(self, tcp=False, udp=False, process=False):
        self.tcp = tcp
        self.udp = udp
        self.process = process


def get_socket_stats(context, retry=0):
    args = []
    args += ["-a"]
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


class Metric(object):

    @property
    def label_names(self):
        return ["class", "flow"]


class TCPMetric(Metric):

    def __init__(self, path):
        self.path = jmespath.compile(path)
        self.tcp_label_names = ["src", "src_port", "dest", "dst_port"]
        self.tcp_label_paths = [
                    jmespath.compile("src"),
                    jmespath.compile("src_port"),
                    jmespath.compile("dst"),
                    jmespath.compile("dst_port"),
                ]

    @property
    def label_names(self):
        return super(TCPMetric, self).label_names + self.tcp_label_names

    def create(self, config, metric_family, flow):
        value = self.path.search(flow)
        if value is not None:
            label_values = [str(x.search(flow)) for x in
                            self.tcp_label_paths]
            labels = dict(zip(self.tcp_label_names, label_values))
            matching_def, matching_flow = find_flow(
                config.flow_definitions,
                labels
            )
            if matching_flow:
                class_value = matching_def["class"]
                flow_value = matching_flow["flow"]
                all_labels = [class_value, flow_value] + label_values
                metric_family.add_metric(all_labels, value)


class SockPuppetCollector(object):

    def __init__(self, config):
        self.context = SSContext(tcp=True, process=True)
        self.config = config
        self.metric_definitions = {
            "rtt": TCPMetric("tcp_info.rtt")
        }
        self.metric_registry = {
            "rtt": GaugeMetricFamily(
                "sockpuppet_tcp_rtt",
                "TCP Round Trip Time",
                labels=self.metric_definitions["rtt"].label_names)
        }

    def poll(self):
        stats = get_socket_stats(self.context)
        if stats:
            for flow in stats["TCP"]["flows"]:
                self.process_tcp_flow(flow)

    def collect(self):
        for value in self.metric_registry.values():
            yield value

    def process_tcp_flow(self, flow):
        for name, definition in self.metric_definitions.items():
            metric_family = self.metric_registry[name]
            definition.create(self.config, metric_family, flow)
