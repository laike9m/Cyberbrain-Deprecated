"""Program that contains list comprehension.

For now, list comprehensions should not be treated as a call, but a line, though it
triggers a "call" event.

Main reasons:
1. Hard to visualize and trace, since list comprehensions is essentially packing
   a loop into one line.
2. Usually the logic is simple. Function calls can exist in list comprehension,
   like [f(i) for i in range(3)], but it's fine to assume f and i affects the generated
   list.
"""

import cyberbrain

cyberbrain.init()

x = [1 for i in range(3)]

cyberbrain.register(x)
