import sys


def err(msg):
    sys.stderr.write("***ERROR: %s" % msg)
    return False