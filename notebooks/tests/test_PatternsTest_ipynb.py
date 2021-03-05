from src.gitutils.utils import execute
import os
os.environ['PYTEST_RUNNING'] = 'true'
exit_status = 0

def test_convertTestPatternsNotebook(capsys,caplog):
    command = "jupyter nbconvert --to script --output-dir=notebooks/tests notebooks/PatternsTest.ipynb".split()
    status = execute(command)
    assert exit_status == status,\
        ("Unexpected exit code " + str(status))

def test_runTestPatterns(capsys, caplog):
    command = "python notebooks/tests/PatternsTest.py".split()
    status = execute(command)
    assert exit_status == status,\
        ("Unexpected exit code " + str(status))