"""Unit tests for flow."""

from .flow import Line, Call
from .utils import ID


def create_flow():
    """Creates an execution flow.

    start
      |   b
     a+---+
      |   |
      |   |       d
      |  c+-------+
      |   |    g  |
         f+----+  |
          |    |  |
       target  h  e

    start  { type: Line, next: a, prev: None}
    a      { type: Call, next: None, prev: start, step_into: b, returned_from: None}
    b      { type: Line, next: c, prev: a}
    c      { type: Call, next: f, prev: b, step_into: d, returned_from: e}
    d      { type: Line, next: e, prev: c}
    e      { type: Line, next: c, prev: d}
    f      { type: Call, next: target, prev: b, step_into: g, returned_from: h}
    g      { type: Line, next: h, prev: f}
    h      { type: Line, next: f, prev: g}
    target { type: Line, next: None, prev: f}

    Assuming code live in a single module, like this:

    def func_f(bar):
        x = len(bar)              # g
        return x                  # h

    def func_c(baa):
        baa.append(None)          # d
        baa.append('???')         # e

    def func_a(foo):
        ba = [foo]                # b
        func_c(ba)                # c
        foo = func_f(ba)          # f
        cyberbrain.register(foo)  # target

    fo = 1                        # start
    func_a(fo)                    # a
    """
    # Common data
    functions = {
        "func_f": "<function func_f at 0x01>",
        "func_c": "<function func_c at 0x02>",
        "func_a": "<function func_a at 0x03>",
        "len": "<built-in function len>",
    }

    # Creates nodes.
    node_start = Line("fo = 1", data={**functions})
    node_a = Call(
        "func_a(fo)", arg_to_param={ID("fo"): ID("foo")}, data={"fo": 1, **functions}
    )
    node_b = Line("ba = [foo]", data={"foo": 1, **functions})
    node_c = Call(
        "func_c(ba)",
        arg_to_param={ID("ba"): ID("baa")},
        data={"foo": 1, "ba": [1], **functions},
    )
    node_d = Line("baa.append(None)", data={"baa": [1], **functions})
    node_e = Line("baa.append('???')", data={"baa": [1, None], **functions})
    node_f = Call(
        "foo = func_f(ba)",
        arg_to_param={ID("ba"): ID("bar")},
        data={"foo": 1, "ba": [1, None, "???"], **functions},
    )
    node_g = Line("x = len(bar)", data={"bar": [1, None, "???"], **functions})
    node_h = Line("return x", data={"bar": [1, None, "???"], "x": 3, **functions})
    node_target = Line(
        "cyberbrain.register(foo)", data={"foo": 3, "ba": [1, None, "???"], **functions}
    )

    # Builds relation.
    node_start.next = node_a
    node_a.build_relation(prev=node_start, step_into=node_b)
    node_b.build_relation(next=node_c, prev=node_a)
    node_c.build_relation(
        next=node_f, prev=node_b, step_into=node_d, returned_from=node_e
    )
    node_d.build_relation(next=node_e, prev=node_c)
    node_e.build_relation(next=node_c, prev=node_d)
    node_f.build_relation(
        next=node_target, prev=node_b, step_into=node_g, returned_from=node_h
    )
    node_g.build_relation(next=node_h, prev=node_f)
    node_h.build_relation(next=node_f, prev=node_g)
    node_target.build_relation(prev=node_f)


def test_traverse_flow():
    create_flow()
