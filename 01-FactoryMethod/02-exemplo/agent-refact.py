import abc
import json
import os
import sys
import time

import psutil
from lib.thread import StoppableThread

DEFAULT_GRACE_PERIOD = 1.0


def _cpu_and_men_usage(processes):
    """
    Compute the current CPU and memory (MB) usage for a group of processes.
    """
    cpu_usage = 0
    mem_usage_mb = 0

    for process in processes:
        cpu_usage += process.cpu_percent()
        mem_usage_mb += process.memory_info().rss >> 20  # from bytes to Mb

    return cpu_usage, mem_usage_mb


class MetricsGetter(abc.ABC):
    """
    Metrics getter interface.

    parameters
    ----------
    pid : int
        ID of the monitored process.
    """

    def __init__(self, pid):
        self._process = psutil.Process(pid)
        self._start_time = time.time()

    def _processes(self):
        """
        Iterate through the monitored process and all of its children.
        """
        yield self._process
        yield from self._process.children(recursive=True)

    @abc.abstractmethod
    def get_metrics(self):
        """
        Return a group of metrics as a dictionary.
        """
        pass


class CurMetricsGetter(MetricsGetter):
    """
    Metrics getter that computes the current CPU and memory usage.
    """

    def get_metrics(self):
        cpu, mem = _cpu_and_men_usage(self._processes())
        return {"cpu_usage": cpu, "mem_usage_mb": mem}


class AggMetricsGetter(MetricsGetter):
    """
    Metrics getter that computes the average CPU usage and max memory usage of a given process.
    """

    def _expanding_avg(self, cur_avg, n_measure, cur_val):
        return (cur_avg * (n_measure - 1) + cur_val) / n_measure

    def get_metrics(self):
        self.n_measure = getattr(self, "n_measure", 0) + 1

        cpu_usage, mem_usage = _cpu_and_men_usage(self._processes())

        cur_max_men = getattr(self, "max_mem", 0)
        cur_avg_cpu = getattr(self, "avg_cpu", 0)

        self.avg_cpu = self._expanding_avg(cur_avg_cpu, self.n_measure, cur_avg_cpu)
        self.max_mem = max(cur_max_men, mem_usage)

        return {"max_men_usage_mb": self.max_mem, "avg_cpu_usage": self.avg_cpu}


class Writer(abc.ABC):
    """
    Define metrics writer interface.
    """

    @abc.abstractmethod
    def write(self, metrics):
        """
        Take as argument an metrics dictionary and write it somewhere.
        """
        pass

    def init(self):
        """
        Initialise the writer.
        """
        pass

    def flush(self):
        """
        Perform any cleaning necessary before going out of scope.
        """
        pass


class StdoutWriter(Writer):
    """
    Streams the metrics to stdout.
    """

    def write(self, metrics):
        sys.stdout.write(json.dumps(metrics) + "\n")
        sys.stdout.flush()


class LogWriter(Writer):
    """
    Write the most up to date value to stdout at once.
    """

    def write(self, metrics):
        self._metrics = metrics

    def flush(self):
        metrics = getattr(self, "_metrics", {})
        json.dump(metrics, sys.stdout)
        sys.stdout.flush()


class Agent(StoppableThread):
    """
    Base class for a resource monitoring agent.
    """

    def __init__(self, *, pid=None, sleep=1):
        super().__init__()
        self._sleep = sleep
        self._pid = pid or os.getpid()
        self._metrics_getter = self.make_metrics_getter(self._pid)
        self._writer = self.make_writer()

    def setup(self):
        self._writer.init()

    def mainloop(self):
        metrics = self._metrics_getter.get_metrics()
        self._writer.write(metrics)

        time.sleep(self._sleep)

    def teardown(self):
        self._writer.flush()

    # ======================================
    # =========== OVERWRITE ================
    # ======================================
    def make_writer(self):
        """
        Make the writer object used to write metrics somewhere. It should return an object that
        implements the interface defined by `Writer`.
        """
        return StdoutWriter()

    @abc.abstractmethod
    def make_metrics_getter(self, pid):
        """
        Make the metrics getter object to get generate the metrics monitored by the agent.
        It should return an object that implements the interface defined by `MetricsGetter`.
        """
        pass


class StreamAgent(Agent):
    """
    Monitor the resource usage of a given moment and stream the values to stdout.
    """

    def make_metrics_getter(self, pid):
        return CurMetricsGetter(pid)


class LogAgent(Agent):
    """
    Monitor the resource usage of a given process and logs their aggregates.
    """

    def make_metrics_getter(self, pid):
        return AggMetricsGetter(pid)

    def make_writer(self):
        return LogWriter()


if __name__ == "__main__":
    print("Using streaming agent.")
    print("-" * 20)
    agent = StreamAgent()
    agent.start()
    time.sleep(5)

    agent.stop()
    agent.wait()

    print()
    print("Using log agent.")
    print("-" * 20)
    agent = LogAgent()
    agent.start()
    time.sleep(5)

    agent.stop()
    agent.wait()
