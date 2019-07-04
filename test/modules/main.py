"""Program that invokes functions from other modules."""

import cyberbrain
import foo

cyberbrain.init()
foo.func_in_foo()
cyberbrain.register()
