import subprocess
import logging
import json
import jmespath

try:
    xrange = xrange
except NameError:  # python3
    xrange = range

from prometheus_client.metrics_core import GaugeMetricFamily, \
    CounterMetricFamily

_logger = logging.getLogger(__name__)

_allowed_selectors = ["src_port", "dst_port", "src", "dst"]


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
    try:
        pipes = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        std_out, std_err = pipes.communicate()

        if pipes.returncode != 0:
            _logger.error("return code non-zero: {}".format(std_err))
            if retry < 1 and context.process:
                _logger.error("Gathering process information requires root "
                              "privileges, auto disabling process gathering.")
                context.process = False
                return get_socket_stats(context, retry=retry + 1)
        return json.loads(std_out)
    except IOError as e:
        _logger.error("Failed to run ss2", e)


def find_flow(definitions, labels):
    def test(flow, item):
        if item not in flow:
            return True
        if item not in labels:
            return False
        if isinstance(flow[item], int):
            return flow[item] == labels[item]
        if isinstance(flow[item], set) or isinstance(flow[item], xrange):
            return labels[item] in flow[item]
        if (item == "src_port" or item == "dst_port") and ":" in flow[item]:
            split = flow[item].split(":")
            maximum = int(split[1])
            minimum = int(split[0])
            return maximum >= labels[item] >= minimum
        return flow[item] == labels[item]

    for flow_definition in definitions:
        for flow in flow_definition["flows"]:
            if all([test(flow, x) for x in _allowed_selectors]):
                return flow_definition, flow
    return None, None


class TCPFlowContext(object):

    def __init__(self, config, flow):
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

    def create(self, context, metric):
        value = self.path.search(context.flow)
        if value is not None:
            all_labels = [context.flow_class, context.flow_name] + \
                         [str(x) for x in context.label_values]
            metric.add_metric(all_labels, value)


class TCPMetric(Metric):

    tcp_label_names = ["src", "src_port", "dst", "dst_port"]
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
        return [x.search(flow) for x in TCPMetric.tcp_label_paths]


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
            "tmem": TCPMetric("meminfo.t"),
            "wmem": TCPMetric("meminfo.w"),
        }

    def metrics(self):
        metrics = {
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

            # https://github.com/torvalds/linux/commit/cd9b266095f422267bddbec88f9098b48ea548fc,  # noqa
            "notsent_bytes": GaugeMetricFamily(
                "sockpuppet_tcp_notsent_bytes",
                "the amount of bytes in the write queue that were not yet "
                "sent. This is only likely to work with a linux >= 4.6.",
                labels=self.metric_definitions["notsent_bytes"].label_names),

            # idiag_tmem, see: man sock_diag
            "tmem": GaugeMetricFamily(
                "sockpuppet_tcp_tmem_bytes",
                "The amount of data in send queue",
                labels=self.metric_definitions["tmem"].label_names),

            # idiag_wmem
            "wmem": GaugeMetricFamily(
                "sockpuppet_tcp_wmem_bytes",
                "The amount of data that is queued by TCP"
                "but not yet sent.",
                labels=self.metric_definitions["wmem"].label_names),
        }
        return metrics

    def collect(self):
        stats = get_socket_stats(self.context)
        if stats:
            for flow in stats["TCP"]["flows"]:
                for metric in self.process_tcp_flow(flow):
                    yield metric

    def process_tcp_flow(self, flow):
        context = TCPFlowContext(self.config, flow)
        metrics = self.metrics()
        for name, definition in self.metric_definitions.items():
            metric = metrics[name]
            if context.should_collect():
                definition.create(context, metric)
                yield metric
