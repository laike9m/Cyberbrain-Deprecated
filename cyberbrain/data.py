"""Variable managing utilities."""

import copy
from collections import defaultdict


class DataContainer:
    """A class that holds variable values in a trace event."""

    # TODO: Should we flatten variables in different frames? Is there still a need to
    # keep the data - frame binding here?

    def __init__(self, frame):
        self._traverse_frames(frame)
        del frame

    def __getitem__(self, index):
        return self.frame_vars[index]

    def add(self, name, value):
        print(f"Adding {name}: {value}")

    def compare(self, other):
        """Compares with another data container and finds diffs."""

    def _traverse_frames(self, frame):
        """Records variables from bottom to top."""
        # TODO: use frame id to replace frame_level_up, and flatten frame_vars.
        self.frame_vars = defaultdict(dict)  # [frame_level_up][var_name]
        frame_level_up = 0
        while frame is not None:
            for var_name, var_value in frame.f_locals.items():
                try:
                    self.frame_vars[frame_level_up][var_name] = copy.deepcopy(var_value)
                except TypeError:
                    try:
                        self.frame_vars[frame_level_up][var_name] = copy.copy(var_value)
                    except TypeError:
                        self.frame_vars[frame_level_up][var_name] = var_value
            frame = frame.f_back
            frame_level_up += 1
