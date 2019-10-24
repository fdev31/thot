__all__ = ['run_in_thread', 'Task', 'GuiFeedback']

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=3)

def run_in_thread(proc, **kw):
    return asyncio.wrap_future(executor.submit(proc, **kw))

class Task:
    def __init__(self, fn, args):
        self.args = args
        self.fn = fn
        self.cond = Event()

    def wait(self):
        self.cond.wait()
        return self.result

    def run(self):
        self.result = self.fn(*self.args)
        self.cond.set()

class GuiFeedback:
    def __init__(self, fn):
        self.run = fn

