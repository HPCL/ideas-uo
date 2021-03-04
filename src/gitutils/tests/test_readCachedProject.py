import os
from gitutils.tests.testutils import *
from gitutils.utils import *

from patterns.fetcher import Fetcher

def test_readCachedProject(capsys, caplog):
    fetcher = Fetcher(project_name='ideas-uo')
    try:
        success = fetcher.fetch()
    except Exception as e:
        success = err("Could not load ideas-uo cached project: %s" % str(e))
    assert success is True