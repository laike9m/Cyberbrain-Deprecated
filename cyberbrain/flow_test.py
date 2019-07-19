"""Unit tests for flow."""

from .flow import Line, Call
from .utils import ID


def create_flow():
    """Creates the following execution flow.

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

    Assuming code all live in a single module.
    """
    # Creats nodes.
    node_start = Line("fo = 1")
    node_a = Call("func_a(fo)", {ID("fo"): ID("foo")})
    node_b = Line("ba = [foo]")
    node_c = Call("func_c(ba)", {ID("ba"): ID("baa")})
    node_d = Line("baa.append(None)")
    node_e = Line("baa.append('???')")
    node_f = Call("foo = func_f(baa)", {ID("baa"): ID("baaa")})
    node_g = Line("x = len(baaa)")
    node_h = Line("return x")
    node_target = Line("cyberbrain.register(foo)")

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
