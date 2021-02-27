from gitutils.utils import *
from patterns.visualizer import Visualizer


def test_instantiateVisualizer(capsys, caplog):
    try:
        vis = Visualizer('spack')
        if vis:
            success = True
    except Exception as e:
        success = err("Could not instantiate Visualizer('spack') class: %s" % str(e))
    assert success
