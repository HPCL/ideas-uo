import os
from gitutils.tests.testutils import *
from gitutils.utils import *

def test_instantiateGitCommand(capsys, caplog):
    try:
        gitcmd = getGitCommandInstance()
        if gitcmd != None:
            success = True
    except Exception as e:
        success = err("Could not instantiate GitCommand class: %s" % str(e))
    assert success is True

def test_cloneRepo(capsys, caplog):
    gitcmd = getGitCommandInstance()
    if os.path.exists('testrepo'):
        os.rmdir('testrepo')
    ret_code = gitcmd.cloneRepo('https://github.com/HPCL/testrepo.git')
    assert ret_code is True
