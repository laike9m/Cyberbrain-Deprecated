"""Unit tests for flow."""

from . import backtrace
from .flow import Node, Flow
from .utils import ID
from .frame_id import FrameID


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

    start  { next: a, prev: None}
    a      { next: None, prev: start, step_into: b, returned_from: None}
    b      { next: c, prev: a}
    c      { next: f, prev: b, step_into: d, returned_from: e}
    d      { next: e, prev: c}
    e      { next: c, prev: d}
    f      { next: target, prev: b, step_into: g, returned_from: h}
    g      { next: h, prev: f}
    h      { next: f, prev: g}
    target { next: None, prev: f}

    Assuming code live in a single module, like this:

    def func_f(bar):
        x = len(bar)              # g
        return x                  # h

    def func_c(baa):
        baa.append(None)          # d
        baa.append('?')           # e

    def func_a(foo):
        ba = [foo]                # b
        func_c(ba)                # c
        foo = func_f(ba)          # f
        cyberbrain.register(foo)  # target

    cyberbrain.init()
    fo = 1                        # start
    func_a(fo)                    # a
    """
    # Common data
    functions = {
        ID("func_f"): "<function func_f at 0x01>",
        ID("func_c"): "<function func_c at 0x02>",
        ID("func_a"): "<function func_a at 0x03>",
        ID("len"): "<built-in function len>",
    }

    # Creates nodes.
    node_start = Node(FrameID.create("line"), code_str="fo = 1", data={**functions})
    node_a = Node(
        FrameID.create("call"),
        code_str="func_a(fo)",
        arg_to_param={ID("fo"): ID("foo")},
        data={ID("fo"): 1, **functions},
    )
    node_b = Node(
        FrameID.create("line"), code_str="ba = [foo]", data={ID("foo"): 1, **functions}
    )
    node_c = Node(
        FrameID.create("call"),
        code_str="func_c(ba)",
        arg_to_param={ID("ba"): ID("baa")},
        data={ID("foo"): 1, ID("ba"): [1], **functions},
    )
    node_d = Node(
        FrameID.create("line"),
        code_str="baa.append(None)",
        data={ID("baa"): [1], **functions},
    )
    node_e = Node(
        FrameID.create("line"),
        code_str="baa.append('?')",
        data={ID("baa"): [1, None], **functions},
    )
    node_f = Node(
        FrameID.create("call"),
        code_str="foo = func_f(ba)",
        arg_to_param={ID("ba"): ID("bar")},
        data={ID("foo"): 1, ID("ba"): [1, None, "?"], **functions},
    )
    node_g = Node(
        FrameID.create("line"),
        code_str="x = len(bar)",
        data={ID("bar"): [1, None, "?"], **functions},
    )
    node_h = Node(
        FrameID.create("line"),
        code_str="return x",
        data={ID("bar"): [1, None, "?"], ID("x"): 3, **functions},
    )
    node_target = Node(
        FrameID.create("line"),
        code_str="cyberbrain.register(foo)",
        data={ID("foo"): 3, ID("ba"): [1, None, "?"], **functions},
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

    return Flow(start=node_start, target=node_target)


def test_traverse_flow():
    flow = create_flow()
    backtrace.trace_flow(flow)
