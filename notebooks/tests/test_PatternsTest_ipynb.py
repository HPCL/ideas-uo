from gitutils.utils import execute
import os
os.environ['PYTEST_RUNNING'] = 'true'
exit_status = 0

def test_convertTestPatternsNotebook(capsys,caplog):
    command = f'jupyter nbconvert --to script --output-dir=notebooks/tests ' \
              f'notebooks/PatternsTest.ipynb'.split()
    print(command)
    status = execute(command)
    assert exit_status == status,\
        ("Unexpected exit code " + str(status))

def test_runTestPatterns(capsys, caplog):
    inputfile = os.path.join('notebooks','tests','PatternsTest.py')
    command = f'python {inputfile}'.split()
    print(command)
    status = execute(command)
    assert exit_status == status,\
        ("Unexpected exit code " + str(status))