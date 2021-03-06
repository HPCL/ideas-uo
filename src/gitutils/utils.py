import sys
from subprocess import call
from tempfile import TemporaryFile

def err(msg):
    sys.stderr.write("***ERROR: %s" % msg)
    return False


"""
The following two methods are based on the Recipy project:
https://github.com/recipy/recipy
Licence: Apache License Version 2.0, January 2004 http://www.apache.org/licenses/
"""
# Copyright (c) 2016 University of Edinburgh. (indicated in each function)
def execute(command, stdout=None, stderr=None) -> int:
    # Copyright (c) 2016 University of Edinburgh. (this method)
    """
    Run a command via the operating system.
    :param command: Command to run plus any arguments
    :type command: list of str or unicode
    :param stdout: File for standard output stream
    :type stdout: file
    :param stderr: File for standard error stream
    :type stderr: file
    :return: exit code
    :rtype: int
    :raises OSError: if there are problems running the command
    """
    print((" ".join(command)))
    return_code = call(command, stdout=stdout, stderr=stderr)
    return return_code


def execute_and_capture(command):
    # Copyright (c) 2016 University of Edinburgh. (this method)
    """
    Run a command via the operating system and capture and return
    standard output and standard error.
    :param command: Command to run plus any arguments
    :type command: list of str or unicode
    :return: (exit code, standard output and error)
    :rtype: (int, str or unicode)
    :raises OSError: if there are problems running the command
    """
    with TemporaryFile(mode='w+', suffix="log") as stdouterr:
        result = execute(command, stdout=stdouterr, stderr=stdouterr)
        stdouterr.seek(0)
        log = stdouterr.readlines()
    return (result, log)
