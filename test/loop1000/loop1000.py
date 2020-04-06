"""Tests loop 1000 times."""

import cyberbrain

cyberbrain.init()


class MyClass:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def increment(self):
        self.x += 1
        self.y += 1


inst = MyClass(1, 2)

for _ in range(3):
    inst.increment()

cyberbrain.register(inst)
