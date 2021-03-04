import sys, os


def err(msg):
    sys.stderr.write("***ERROR: %s" % msg)
    return False

def getGitCommandInstance():
    from gitutils.gitcommand import GitCommand
    return GitCommand()
