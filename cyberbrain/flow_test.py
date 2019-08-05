"""Unit tests for flow."""

from . import backtrace, format
from .flow import Node, Flow
from .basis import ID
from .basis import FrameID


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
    e      { prev: d}
    f      { next: target, prev: b, step_into: g, returned_from: h}
    g      { next: h, prev: f}
    h      { prev: g}
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

    GLOBAL_FRAME = (0,)
    FUNC_A_FRAME = (0, 0)
    FUNC_C_FRAME = (0, 0, 0)
    FUNC_F_FRAME = (0, 0, 1)

    # Common data
    functions = {
        ID("func_f", GLOBAL_FRAME): "<function func_f at 0x01>",
        ID("func_c", GLOBAL_FRAME): "<function func_c at 0x02>",
        ID("func_a", GLOBAL_FRAME): "<function func_a at 0x03>",
        ID("len", GLOBAL_FRAME): "<built-in function len>",
    }

    # Creates nodes.
    node_start = Node(GLOBAL_FRAME, code_str="fo = 1", data={**functions})
    node_a = Node(
        GLOBAL_FRAME,
        code_str="func_a(fo)",
        param_to_arg={ID("foo", FUNC_A_FRAME): {ID("fo", GLOBAL_FRAME)}},
        data={ID("fo", GLOBAL_FRAME): 1, **functions},
    )
    node_b = Node(
        FUNC_A_FRAME,
        code_str="ba = [foo]",
        data={ID("foo", FUNC_A_FRAME): 1, **functions},
    )
    node_c = Node(
        FUNC_A_FRAME,
        code_str="func_c(ba)",
        param_to_arg={ID("baa", FUNC_C_FRAME): {ID("ba", FUNC_A_FRAME)}},
        data={ID("foo", FUNC_A_FRAME): 1, ID("ba", FUNC_A_FRAME): [1], **functions},
    )
    node_d = Node(
        FUNC_C_FRAME,
        code_str="baa.append(None)",
        data={ID("baa", FUNC_C_FRAME): [1], **functions},
    )
    node_e = Node(
        FUNC_C_FRAME,
        code_str="baa.append('?')",
        data={ID("baa", FUNC_C_FRAME): [1, None], **functions},
        data_before_return={ID("baa", FUNC_C_FRAME): [1, None, "?"], **functions},
    )
    node_f = Node(
        FUNC_A_FRAME,
        code_str="foo = func_f(ba)",
        param_to_arg={ID("bar", FUNC_F_FRAME): {ID("ba", FUNC_A_FRAME)}},
        data={
            ID("foo", FUNC_A_FRAME): 1,
            ID("ba", FUNC_A_FRAME): [1, None, "?"],
            **functions,
        },
    )
    node_g = Node(
        FUNC_F_FRAME,
        code_str="x = len(bar)",
        data={ID("bar", FUNC_F_FRAME): [1, None, "?"], **functions},
    )
    node_h = Node(
        FUNC_F_FRAME,
        code_str="return x",
        data={
            ID("bar", FUNC_F_FRAME): [1, None, "?"],
            ID("x", FUNC_F_FRAME): 3,
            **functions,
        },
        data_before_return={
            ID("bar", FUNC_F_FRAME): [1, None, "?"],
            ID("x", FUNC_F_FRAME): 3,
            **functions,
        },
    )
    node_target = Node(
        FUNC_A_FRAME,
        code_str="cyberbrain.register(foo)",
        data={
            ID("foo", FUNC_A_FRAME): 3,
            ID("ba", FUNC_A_FRAME): [1, None, "?"],
            **functions,
        },
    )

    # Builds relation.
    node_start.next = node_a
    node_a.build_relation(prev=node_start, step_into=node_b)
    node_b.build_relation(next=node_c, prev=node_a)
    node_c.build_relation(
        next=node_f, prev=node_b, step_into=node_d, returned_from=node_e
    )
    node_d.build_relation(next=node_e, prev=node_c)
    node_e.build_relation(prev=node_d)
    node_f.build_relation(
        next=node_target, prev=node_c, step_into=node_g, returned_from=node_h
    )
    node_g.build_relation(next=node_h, prev=node_f)
    node_h.build_relation(prev=node_g)
    node_target.build_relation(prev=node_f)

    return Flow(start=node_start, target=node_target)


def test_traverse_flow():
    flow = create_flow()
    backtrace.trace_flow(flow)
    format.generate_output(flow)
