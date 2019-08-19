"""Program that invokes functions from other modules."""

import cyberbrain
import foo

cyberbrain.init()
x = foo.func_in_foo()
cyberbrain.register(x)
