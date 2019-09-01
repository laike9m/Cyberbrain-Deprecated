"""Example program in design doc."""

import cyberbrain


def func_f(bar):
    x = len(bar)  # g
    return x  # h


def func_c(baa):
    baa.append(None)  # d
    baa.append("?")  # e


def func_a(foo):
    ba = [foo]  # b
    func_c(ba)  # c
    foo = func_f(ba)  # f
    cyberbrain.register(foo)  # target


cyberbrain.init()
fo = 1  # start
func_a(fo)  # a
