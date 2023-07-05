

import os, sys

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


doc_extensions_to_check = ['.F90', '.dox', '.c', '.py']  #might add more types later, e.g., .md files
filenames_to_check = []

#Auxilliary function used by check_file_documentation.
#General idea is that some files do not have checking unabled so skip over them.
#Returns one of two tuples:
#   (True, '') meaning it is checkable or
#   (False, msg:str) meaning not checkable with msg description of why

def is_file_documentation_checkable(lines:list, path:str) -> tuple:

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

test_struct = [
    {'isFile':True, 'name':'file1'},
    {'isFile':True, 'name':'file2'},
    {'isFile':False, 'name':'source', 'contents':[
        {'isFile':True, 'name':'file3'},
        {'isFile':True, 'name':'file4'},
        {'isFile':False, 'name':'Foo', 'contents':[
            {'isFile':True, 'name':'file7'}
        ]},
        {'isFile':False, 'name':'Fum', 'contents':[
            {'isFile':True, 'name':'file8'},
            {'isFile':False, 'name':'Fie', 'contents':[
              {'isFile':True, 'name':'file9'}
            ]},
        ]},
    ]},
    {'isFile':False, 'name':'folder1', 'contents':[
        {'isFile':True, 'name':'file5'},
        {'isFile':True, 'name':'file6'},
        {'isFile':False, 'name':'Foe', 'contents':[
            {'isFile':True, 'name':'file10'},
            {'isFile':False, 'name':'Fud', 'contents':[
              {'isFile':True, 'name':'file11'}
            ]},
      ]},
    ]},
]


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

The return value is a dictionary of following form:

<pre>
'file_status': 'checkable' or 'uncheckable: msg' or 'checkable but no documentation'
'missing_fields': list of fields as strings
'problem_fields' = [(msg:str, line:str, line_number:int),  ...] where msg describes problem.
'bogus_fields': e.g., [('@internal', line:str, line_number:int), ...] where @internal should not be in this file.
</pre>

For the MeerCat message that goes along with `'uncheckable: msg'` or `'checkable but no documentation'`, might use something like *"Please see Flash-X/docs/doxygen/UnitTemplate/ for templates on setting up Doxygen documentation."*
"""

#This is one of two public functions that make up library API
def check_file_documentation(lines:list, path:str):
  assert isinstance(lines, list)
  assert all([isinstance(x,str) for x in lines])
  assert isinstance(path,str)

  return check_file_documentation_aux(dir_struct, lines, path)  #adds dir_struct

def check_file_documentation_aux(dir_struct, lines:list, path:str):
  assert isinstance(lines, list)
  assert all([isinstance(x,str) for x in lines])
  assert isinstance(path,str)

  global units  #list of known units in Flash-X

  results_dict = {
      'file_status': 'checkable',
      'missing_fields': [],
      'missing_file_fields': [],
      'missing_subroutine_fields': [],
      'problem_fields': [],
      'bogus_fields': [],
  }

  checkable, msg = is_file_documentation_checkable(lines, path)  #returns tuple: (bool, msg)
  if not checkable:
    results_dict['file_status'] = f'uncheckable: {msg}'
    return results_dict

  results_dict['file_status'] = f'uncheckable: No documentation checker library available.'
  return results_dict
