from gitutils.utils import *
from patterns.visualizer import Visualizer


def test_connectToDatabase(capsys, caplog):
    success = False
    try:
        vis = Visualizer('spack')
        vis.get_data()
        success = True
    except Exception as e:
        success = err("Could not connect to database: %s" % str(e))
    assert success
