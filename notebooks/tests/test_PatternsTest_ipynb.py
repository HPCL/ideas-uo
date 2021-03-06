from gitutils.utils import execute
import os
os.environ['PYTEST_RUNNING'] = 'true'
exit_status = 0

from os.path import abspath, dirname, join
package_path = abspath(dirname(dirname(__file__)))
print(f"PatternsTest: I am running in {os.getcwd()} and package path is {package_path}!")
os.system(f'ls -r {package_path}')

def test_convertTestPatternsNotebook(capsys,caplog):
    inputfile = abspath(join(package_path, 'PatternsTest.ipynb'))
    command = f'jupyter nbconvert --to script --output-dir={package_path}/tests {inputfile}'.split()
    print(command)
    status = execute(command)
    assert exit_status == status,\
        ("Unexpected exit code " + str(status))

def test_runTestPatterns(capsys, caplog):
    inputfile = abspath(join(package_path,'tests','PatternsTest.py'))
    command = f'python {inputfile}'.split()
    print(command)
    status = execute(command)
    assert exit_status == status,\
        ("Unexpected exit code " + str(status))