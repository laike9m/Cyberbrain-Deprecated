"""Tests method call."""

import cyberbrain


class MyClass:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def increment(self):
        self.x += 1
        self.y += 1


cyberbrain.init()
inst = MyClass(1, 2)
inst.increment()

cyberbrain.register(inst)
