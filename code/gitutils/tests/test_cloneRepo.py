import os
from code.gitutils.tests.testutils import *

def test_instantiateGitCommand(capsys, caplog):
    try:
        gitcmd = getGitCommandInstance()
        if gitcmd != None:
            success = True
    except Exception as e:
        success = err("Could not instantiate GitCommand class: %e" % e.message)
    assert success is True

def test_cloneRepo(capsys, caplog):
    gitcmd = getGitCommandInstance()
    if os.path.exists('tmprepo'):
        os.rmdir('tmprepo')
    ret_code = gitcmd.cloneRepo('https://github.com/HPCL/tmprepo.git')
    assert ret_code is True