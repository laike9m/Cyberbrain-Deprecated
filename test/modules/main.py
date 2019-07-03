"""Program that invokes functions from other modules."""

import foo

import cyberbrain


cyberbrain.init()
foo.func_in_foo()
cyberbrain.register()
