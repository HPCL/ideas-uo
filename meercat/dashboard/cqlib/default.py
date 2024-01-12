
import os, sys
import json

from django.conf import settings
from database.models import Project


def splitall(path):
    allparts = []
    while 1:
        head, tail = os.path.split(path)
        if head == path:  # sentinel for absolute paths
            allparts.insert(0, head)
            break
        elif tail == path: # sentinel for relative paths
            allparts.insert(0, tail)
            break
        else:
            path = head
            allparts.insert(0, tail)
    return allparts


doc_extensions_to_check = ['.F90', '.cpp', '.c', '.h', '.py']  #might add more types later
filenames_to_check = []

#Auxilliary function used by check_file_documentation.
#General idea is that some files do not have checking unabled so skip over them.
#Returns one of two tuples:
#   (True, '') meaning it is checkable or
#   (False, msg:str) meaning not checkable with msg description of why

def is_file_checkable(lines:list, path:str) -> tuple:

  #return (False, f"File extension currently not checkable.")
  return (True, '')

"""#Need directory structure for checking private files

Assume MeerCat calls this function.

#Directory Structure

For some projects, it may be necessary to find files or folders not directly on the file path. It is expected that MeerCat will call this function and pass in a portion of the repo directory structure. Not the content, just folder and file names in a tree like structure.
If this function is not called, then it is assumed that checking a specific project's documentation does not require knowing more than what is on the path. In this case, `dir_struct` defaults to `None`.
"""

dir_struct = None  #assume MeerCat will set this with function below if needed by a project

#One of two public functions
def set_directory_structure(structure):
  global dir_struct
  dir_struct = structure
  return None

def find_file_or_folder(starting_folder:list , target:str, the_type:str):
  assert starting_folder
  assert the_type in ['file', 'folder']

  def iterative_search(current_folder, path_so_far):
        for the_dict in current_folder:
          if the_type=='folder':
            if the_dict['isFile']==False and the_dict['name']==target:
              return (current_folder, path_so_far)
          else:
            if the_dict['isFile']==True and the_dict['name']==target:
              return (current_folder, path_so_far)

        #did not find in this folder. Do search.
        for the_dict in current_folder:
          if the_dict['isFile']==False:
            answer = iterative_search(the_dict['contents'], f'{path_so_far}/{the_dict["name"]}')
            if answer[0]: return answer
            continue
        return ([], '')  #not found on path_so_far
  
  answer = iterative_search(starting_folder, '')
  return answer


def contains_folder(dir_struct, folder):
  return find_file_or_folder(dir_struct, folder, 'folder')

def contains_file(dir_struct, file):
  return find_file_or_folder(dir_struct, file, 'file')

"""##Look for end of path, assumed to be folder"""

def find_folder_on_path(root_structure:list, path:str):
  components = splitall(path)
  current_structure = root_structure
  path_so_far = ''
  for dir in components:
    folder,path = contains_folder(current_structure, dir)
    if not folder:
      #the current dir is not in current_structure
      return (current_structure, path_so_far)
    else:
      #the current dir is in current_structure so find it
      path_so_far += f'/{dir}'
      for the_dict in folder:
        if the_dict['isFile']==False and the_dict['name']==dir:
          current_structure = the_dict['contents']
          break
      else: assert False, 'Should not get here.'
  return (current_structure, path_so_far)


"""# Main checking function

Input is simply file, in form of a list of lines/strings and the path to the file, starting with `source/`.

The return value is a list of following form:

[{},{}]

"""

#This is one of two public functions that make up library API
def check_file(proj_object, settings, filename:str):
  #assert isinstance(lines, list)
  #assert all([isinstance(x,str) for x in lines])
  #assert isinstance(path,str)

  results = []

  if filename.endswith(".py"):
      rawresults = []
      try:
          print("CHECKING PY FILE")
          # output = os.popen('export PYTHONPATH=${PYTHONPATH}:'+os.path.abspath(str(settings.REPOS_DIR)+'/'+pr.project.name)+' ; cd '+str(settings.REPOS_DIR)+'/'+pr.project.name+' ; '+str(settings.REPOS_DIR)+'/meercat/env/bin/pylint --output-format=json '+filename).read()
          output = os.popen(
              "export PYTHONPATH=${PYTHONPATH}:"
              + os.path.abspath(str(settings.REPOS_DIR) + "/" + proj_object.name)
              + " ; cd "
              + str(settings.REPOS_DIR)
              + "/"
              + proj_object.name
              + " ; . ../meercat/meercat-env/bin/activate ; pylint --output-format=json "
              + filename
          ).read()

          rawresults = json.loads(output)
      except Exception as e:
          pass

      results = []
      for result in rawresults: 
          if 'Unnecessary parens after' not in result['message'] and 'doesn\'t conform to snake_case naming style' not in result['message'] and 'More than one statement on a single line' not in result['message'] and 'Missing function or method docstring' not in result['message'] and 'Formatting a regular string which' not in result['message'] and 'Unnecessary semicolon' not in result['message'] and 'Trailing whitespace' not in result['message'] and 'Bad indentation' not in result['message'] and 'Line too long' not in result['message']:
              results.append(result)


  if filename.endswith(".F90"):
      output = os.popen(
          "export PYTHONPATH=${PYTHONPATH}:"
          + os.path.abspath(str(settings.REPOS_DIR) + "/" + proj_object.name)
          + " ; cd "
          + str(settings.REPOS_DIR)
          + "/"
          + proj_object.name
          + " ; . ../meercat/meercat-env/bin/activate ; fortran-linter "
          + str(settings.REPOS_DIR)
          + "/"
          + proj_object.name
          + "/"
          + filename
          + " --syntax-only"
      ).read()
      #linter_results.append( {"filename": filename, "results": output.split(str(settings.REPOS_DIR) + "/" + pr.project.name + "/" + filename)} )
      results = []
      for result in output.split(
          str(settings.REPOS_DIR) + "/" + proj_object.name + "/" + filename + ":"
      ):
          if result and len(result) > 0:
              try:
                  if 'Use new syntax TYPE' not in result and 'Types should be lowercased' not in result and 'Replace .' not in result and 'At least one space before comment' not in result and 'Exactly one space after' not in result and 'Missing space' not in result and 'Single space' not in result and 'Trailing whitespace' not in result and 'Line length' not in result:
                      results.append(
                          {
                              "column": 0,
                              "line": int(result.split(":")[0]),
                              "message": result.strip().split("\n")[-1].split(": ")[1],
                              "type": result.strip().split("\n")[-1].split(": ")[0],
                          }
                      )
              except:
                  pass


  if filename.endswith(".c"):
      output = os.popen(
          "export PYTHONPATH=${PYTHONPATH}:"
          + os.path.abspath(str(settings.REPOS_DIR) + "/" + proj_object.name)
          + " ; cd "
          + str(settings.REPOS_DIR)
          + "/"
          + proj_object.name
          + " ; . ../meercat/meercat-env/bin/activate ; cpplint --filter=-whitespace "
          + str(settings.REPOS_DIR)
          + "/"
          + proj_object.name
          + "/"
          + filename
          + " 2>&1"
      ).read()
      # linter_results.append( {'filename': filename, 'results':output.split('../'+pr.project.name+'/'+filename+':')} )

      results = []
      for result in output.split(
          str(settings.REPOS_DIR) + "/" + proj_object.name + "/" + filename + ":"
      ):
          if result and len(result) > 0:
              try:
                  if 'Include the directory when naming header' not in result and 'Using C-style cast.' not in result:
                      results.append(
                          {
                              "column": 0,
                              "line": int(result.split(":")[0]),
                              "message": result.split(":")[1].split("  [")[0].strip(),
                              "type": result.split(":")[1]
                              .split("  [")[1]
                              .split("] ")[0],
                          }
                      )
              except:
                  pass
  return results

