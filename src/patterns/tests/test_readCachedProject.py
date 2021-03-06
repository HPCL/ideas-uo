from gitutils.tests.testutils import *
from gitutils.utils import *
os.environ['PYTEST_RUNNING'] = 'true'

from patterns.fetcher import Fetcher

def test_readCachedProject(capsys, caplog):
    fetcher = Fetcher(project_name='testrepo')
    try:
        success = fetcher.fetch()
    except Exception as e:
        success = err("Could not load ideas-uo cached project: %s" % str(e))
    assert success is True