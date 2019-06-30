"""A program that calls functions from Python stdlib and 3rd-party libs.

Since we've excluded events from files in installation path, we shouldn't receive any
events from stdlib or 3rd-party libs. Neither will C calls since they are not catched by
settrace (https://stackoverflow.com/q/16115027/2142577).
"""

from collections import Counter

import crayons
import cyberbrain


cyberbrain.init()
c = Counter()
c["red"] += 1
c["blue"] += 1
c["red"] += 1
c.most_common(10)
crayons.blue("blue")
cyberbrain.register()
