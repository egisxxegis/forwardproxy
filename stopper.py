import os

MARKER_FILENAME = "stop.no"


def allow_running():
    with open(MARKER_FILENAME, "w") as f:
        f.write("This file indicates that the process is allowed to run.")


def disallow_running():
    if os.path.exists(MARKER_FILENAME):
        os.remove(MARKER_FILENAME)


def is_running_allowed():
    return os.path.exists(MARKER_FILENAME)
