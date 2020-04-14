import json
import os
import time
import sys

import psutil
from lib.thread import StoppableThread

DEFAULT_GRACE_PERIOD = 5.0


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


class Agent(StoppableThread):
    def __init__(self, *, pid=None, sleep=1):
        super().__init__()
        self._sleep = sleep
        self._pid = pid or os.getpid()
        self._process = psutil.Process(self._pid)

    def _get_metrics(self):
        processes = [self._process] + self._process.children(recursive=True)

        cpu, mem = _cpu_and_men_usage(processes)
        return {"cpu_usage": cpu, "mem_usage_mb": mem}

    def mainloop(self):
        metrics = self._get_metrics()
        sys.stdout.write(json.dumps(metrics) + "\n")
        sys.stdout.flush()

        time.sleep(self._sleep)


if __name__ == "__main__":
    print("Using streaming agent.")
    print("-" * 20)
    agent = Agent()
    agent.start()

    time.sleep(5)

    agent.stop()
    agent.wait()
