import subprocess
import logging
import json
import jmespath

from prometheus_client.metrics_core import GaugeMetricFamily, \
    CounterMetricFamily

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


class TCPFlowContext(object):

    def __init__(self, config, metric_family, flow):
        self.metric_family = metric_family
        self.flow = flow
        self.label_values = TCPMetric.get_label_values(flow)

        labels = dict(zip(TCPMetric.tcp_label_names, self.label_values))
        matching_def, matching_flow = find_flow(
            config.flow_definitions,
            labels
        )
        if matching_flow:
            self.flow_class = matching_def["class"]
            self.flow_name = matching_flow["flow"]
        else:
            self.flow_class = None
            self.flow_name = None

    def should_collect(self):
        return self.flow_class and self.flow_name


class Metric(object):

    def __init__(self, path):
        self.path = jmespath.compile(path)

    @property
    def label_names(self):
        return ["class", "flow"]

    def create(self, context):
        value = self.path.search(context.flow)
        if value is not None:
            all_labels = [context.flow_class, context.flow_name] + \
                         context.label_values
            context.metric_family.add_metric(all_labels, value)


class TCPMetric(Metric):

    tcp_label_names = ["src", "src_port", "dest", "dst_port"]
    tcp_label_paths = [
        jmespath.compile("src"),
        jmespath.compile("src_port"),
        jmespath.compile("dst"),
        jmespath.compile("dst_port"),
    ]

    @property
    def label_names(self):
        return super(TCPMetric, self).label_names + self.tcp_label_names

    @staticmethod
    def get_label_values(flow):
        return [str(x.search(flow)) for x in TCPMetric.tcp_label_paths]


class SockPuppetCollector(object):

    def __init__(self, config):
        self.context = SSContext(tcp=True, process=True)
        self.config = config
        self.metric_definitions = {
            "rtt": TCPMetric("tcp_info.rtt"),
            "rcv_rtt": TCPMetric("tcp_info_rcv_rtt"),
            "bytes_acked": TCPMetric("tcp_info.bytes_acked"),
            "bytes_received": TCPMetric("tcp_info.bytes_received"),
            "notsent_bytes": TCPMetric("tcp_info.notsent_bytes"),

        }
        self.metric_registry = {
            "rtt": GaugeMetricFamily(
                "sockpuppet_tcp_rtt",
                "The smooth round trip time of delays between sent packets "
                "and received ACK",
                labels=self.metric_definitions["rtt"].label_names),

            "rcv_rtt": GaugeMetricFamily(
                "sockpuppet_tcp_rcv_rtt",
                "Time to receive one full window",
                labels=self.metric_definitions["rcv_rtt"].label_names),

            "bytes_acked": CounterMetricFamily(
                "sockpuppet_tcp_bytes_acked",
                "Number of bytes that have been sent and acknowledged",
                labels=self.metric_definitions["bytes_acked"].label_names),

            "bytes_received": CounterMetricFamily(
                "sockpuppet_tcp_bytes_received",
                "Number of bytes that have been received",
                labels=self.metric_definitions["bytes_received"].label_names),

            "notsent_bytes": CounterMetricFamily(
                "sockpuppet_tcp_notsent_bytes",
                "the amount of bytes in the write queue that were not yet "
                "sent",
                labels=self.metric_definitions["notsent_bytes"].label_names),
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
            metric = self.metric_registry[name]
            context = TCPFlowContext(self.config, metric, flow)
            if context.should_collect():
                definition.create(context)
