import threading

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

