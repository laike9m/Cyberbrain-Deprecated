"""Variable managing utilities."""

import copy
import inspect
import itertools

from collections import defaultdict, UserDict


class Data(UserDict):
    """A class that holds variable values in a trace event."""

    def __init__(self, frame):
        super().__init__()
        self._scan_namespaces(frame)
        del frame

    def __getitem__(self, name):
        return self.data[name]

    def _scan_namespaces(self, frame):
        """Records variables from bottom to top."""
        for name, value in itertools.chain.from_iterable(
            [frame.f_locals.items(), frame.f_globals.items()]
        ):
            # TODO: exclude other stuff we don't need.
            if inspect.ismodule(value):
                continue
            self.data[name] = value
