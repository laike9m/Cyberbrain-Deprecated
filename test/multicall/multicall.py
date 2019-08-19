"""Multiple calls in one logical line."""

import cyberbrain

cyberbrain.init()


def f(*args, **kwargs):
    pass


x = {f(x=1), f(y=2)}


cyberbrain.register(x)
