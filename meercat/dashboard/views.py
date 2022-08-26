import datetime
import json
import requests

import configparser

from django.http import HttpResponse
from django.template import loader
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

import pandas as pd

import re

import sys
sys.path.insert(1, '/shared/soft/ideas_db/ideas-uo/src')
sys.path.insert(1, '../src')
from gitutils.github_api import GitHubAPIClient

from database.models import Project, ProjectRole, Commit, Diff, Issue, PullRequest, PullRequestIssue, Comment, EventPayload, CommitTag
from database.utilities import comment_pullrequest, get_repo_owner
from dashboard.utilities import list_project_files

import subprocess
import os, warnings
warnings.filterwarnings('ignore')
from patterns.visualizer import Visualizer

def not_authorized(request):
    return render(request, 'dashboard/not_authorized.html')

# Index view - should list all projects
@login_required
def index(request):

    if request.user.is_staff:
        return redirect('staff_index')

    devProjects =  Project.objects.filter(project_role__user=request.user, project_role__role='DEV')
    devProjects = sorted(devProjects, key=lambda d: d.name, reverse=False)
    
    PMProjects = Project.objects.filter(project_role__user=request.user, project_role__role='PM')
    PMProjects = sorted(PMProjects, key=lambda d: d.name, reverse=False)
    
    context = {'devProjects': devProjects, 'PMProjects': PMProjects}
 
    return render(request, 'dashboard/index.html', context)

@login_required
def staff_index(request):

    projects = list(Project.objects.all())
    projects = sorted(projects, key=lambda d: d.name, reverse=False)

    return render(request, 'dashboard/staff_index.html', {'projects': projects})

@login_required
def subscriptions(request):

    if request.method == 'POST':
        request.user.profile.subscriptions = json.loads(request.POST['subscriptions'] or "{}")
        print(request.user.profile.subscriptions)
        request.user.profile.save()

    projects = Project.objects.filter(project_role__user=request.user)
    
    files = {}
    project_names = []
    for project in projects:
        project_names.append(project.name)
        files[project.name] = list_project_files(project)

    subscriptions = request.user.profile.subscriptions

    context = {
        'files': files,
        'project_names': project_names,
        'subscriptions': subscriptions,
    }

    return render(request, 'dashboard/subscriptions.html', context)


@login_required
def whitelist(request, *args, **kwargs):
    pid = 30
    if kwargs['pk']:
        pid = int(kwargs['pk'])

    if not hasAccessToProject(request.user, pid):
        return redirect('not_authorized')

    project = Project.objects.get(id=pid)

    if ProjectRole.objects.filter(project=project, user=request.user).exists():
        project_role = ProjectRole.objects.get(project=project, user=request.user)
    else:
        messages.error('Sorry, we could not get your whitelist')
        return redirect('project', pk=pid)

    project_owner = project.source_url.split('/')[-2] #Owner always has index -2. HTTPS urls are of the form https://github.com/owner/repo.git
    whitelist = project_role.whitelist 

    if whitelist is None:
        whitelist = ""

    context = {'project_owner': project_owner, 'project': project, 'whitelist': whitelist}

    return render(request, 'dashboard/whitelist.html', context)

# Project view - should list general project info
def project(request, *args, **kwargs):
    print("PROJECT")
    print( kwargs['pk'] )


    pid = 30
    if kwargs['pk']:
        pid = int(kwargs['pk'])

    if not hasAccessToProject(request.user, pid):
        return redirect('not_authorized')

    template = loader.get_template('dashboard/project.html')

    project = list(Project.objects.all().filter(id=pid).all())[0]

    # chose wether to display whitelist button if user is staff
    show_whitelist = True
    if request.user.is_staff:
        has_project_role = ProjectRole.objects.filter(project=project, user=request.user).exists()
        if not has_project_role:
            show_whitelist = False

    prs = list(PullRequest.objects.all().filter(project=project).all())
    prs = sorted(prs, key=lambda d: d.number, reverse=True)

    commits = list(Commit.objects.all().filter(project=project).all())
    commits = sorted(commits, key=lambda d: d.datetime, reverse=True)

    issues = list(Issue.objects.all().filter(project=project).all())
    issues = sorted(issues, key=lambda d: d.number, reverse=True)

    print("Done loading db data.  Now checking repo contents...")

    # TODO: these are super slow for some projects (spack)

    pythonloc = countlinespython(r'../'+project.name)
    print(".")
    fortranloc = countlinesfortran(r'../'+project.name)
    print("..")
    cloc = countlinesc(r'../'+project.name)
    print("...")
    files = countfiles(r'../'+project.name)
    print("....")


    #TODO: should be able to remove this
    with open('../anl_test_repo/folder1/arithmetic.py', 'r') as f:
        lines = f.readlines()
        f.close()


    context = {'show_whitelist': show_whitelist, 'project':project,'prs':prs, 'commits':commits, 'issues':issues, 'pythonloc':pythonloc, 'fortranloc':fortranloc, 'cloc':cloc, 'files':files, 'file':''.join(lines).replace('\\','\\\\').replace('\n', '\\n').replace('\'','\\\'')}

    return HttpResponse(template.render(context, request))


# PR list view - list all the PRs for project
@login_required
def prlist(request, *args, **kwargs):
    print("PRLIST")
    template = loader.get_template('dashboard/prlist.html')

    pid = 30
    #if request.GET.get('pid'):
    #    pid = int(request.GET.get('pid'))
    if kwargs['pk']:
        pid = int(kwargs['pk'])

        
    if not hasAccessToProject(request.user, pid):
        return redirect('not_authorized')

    project = list(Project.objects.all().filter(id=pid).all())[0]

    prs = list(PullRequest.objects.all().filter(project=project).all())
    prs = sorted(prs, key=lambda d: d.number, reverse=True)

    context = {'project':project,'prs':prs}

    return HttpResponse(template.render(context, request))


# Pull Request view - show the assistant for specific PR
@login_required
def pr(request, *args, **kwargs):
    print("PR")
    template = loader.get_template('dashboard/pr.html')

    prid = 2250
    #if request.GET.get('pr'):
    #    prid = int(request.GET.get('pr'))
    if kwargs['pk']:
        prid = int(kwargs['pk'])

    if not hasAccessToPR(request.user, prid):
        return redirect('not_authorized')

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    commits = list(Commit.objects.all().filter(hash__in=[committag.sha for committag in set(pr.commits.all())]))

    issues = list(Issue.objects.all().filter(url__in=[pri.issue.url for pri in PullRequestIssue.objects.all().filter(pr=pr).all()]))

    labels = pr.labels.all()

    #Find any issue that this PR closed
    closed_issue = None
    issue_number = re.search(r'#\d+', pr.description)
    if issue_number:
        print(issue_number.group())
        print( pr.project.source_url.replace('.git', '/issues/'+issue_number.group()[1:]) )
        closed_issue_list = list(Issue.objects.all().filter(url=pr.project.source_url.replace('.git', '/issues/'+issue_number.group()[1:])))
        if len(closed_issue_list) > 0:
            closed_issue = closed_issue_list[0]


    #issues = list(Issue.objects.all().filter(project=list(Project.objects.all().filter(name='FLASH5').all())[0], state='closed'))
    #for issue in issues:
    #    comments = list(Comment.objects.all().filter(issue=issue))

    diffs = list(Diff.objects.all().filter(commit__in=[c for c in commits]))
    filenames = [d.file_path for d in diffs]
    #get just unique filenames
    filenames_set = set(filenames)
    filenames = list(filenames_set)

    events = list(EventPayload.objects.all().filter(pr_number=pr.number))

    comments = list(Comment.objects.all().filter(pr=pr))

    #switch local repo to the branch for this PR
    if len(commits) > 0:
        branch = commits[0].branch.split()[-1]
        print("PRA Switch branches to: "+branch)
        proj_name = pr.project.name
        cmd = f'cd ../{proj_name} ; git checkout {branch}'
        print(cmd)
        try:
            os.system(cmd)
            result = subprocess.check_output(cmd, shell=True)
            print(result)
        except:
            return ['', [f'Failure to checkout branch {cmd}']]

    context = {'pr':pr, 'commits':commits, 'issues':issues, 'filenames':filenames, 'events':events, 'comments':comments,'closed_issue':closed_issue, 'labels':labels}

    return HttpResponse(template.render(context, request))


# Pull Request view - show the assistant for specific PR
def archeology(request, *args, **kwargs):

    template = loader.get_template('dashboard/archeology.html')

    # Get PR id
    prid = 0
    if kwargs['pk']:
        prid = int(kwargs['pk'])

    if not hasAccessToPR(request.user, prid):
        return redirect('not_authorized')

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    # Get filename
    filename = ''
    if request.GET.get('filename'):
        filename = request.GET.get('filename')

    # Get diffs for file
    diffs = Diff.objects.all().filter(commit__project=pr.project, file_path=filename).all()

    # Get commits, authors for those (diffs)
    authors = set([d.commit.author for d in diffs])

    table = [{'author':author, 'type':'commit','link':'more info'} for author in authors]




    context = {'pr':pr, 'filename': filename, 'authors':table}

    return HttpResponse(template.render(context, request))


# File explorer
#localhost:8080/dashboard/filex/25?branch=master&filename=path  where 25 is test_anl id and path is to file
def file_explorer(request, *args, **kwargs):

    template = loader.get_template('dashboard/file_explorer.html')


    # Get PR id
    prid = 0
    if kwargs['pk']:
        prid = int(kwargs['pk'])

    #simulate project info
    project_info = {
        26: {'docstring_kind': 'robodoc', 'docstring_mandatory': {'NAME': False, 'SYNOPSIS': False, 'DESCRIPTION': False, 'ARGUMENTS':False},
            'testing_kind': 'custom', 'main':'master'},  #flash5
        30: {'docstring_kind': 'numpy', 'docstring_mandatory':{},
            'testing_kind': 'pytest', 'main':'main'}     #anl_test_repo
    }
    project_callers = {}  #needs to be set somewhere global

    project_callers[30] =  { #needs to be part of project profile
         ('check_fum', 'folder1/arithmetic.py'): [],
         ('concat',
          'folder2/strings.py'): [('folder2/test_strings.py', 'test_concat', 'test')],
         ('count', 'folder2/strings.py'): [],
         ('foo',
          'folder3/more_functions.py'): [('folder2/strings.py', 'fum', 'code')],
         ('fum',
          'folder2/strings.py'): [('folder1/arithmetic.py', 'check_fum', 'code')],
         ('list_sub', 'folder1/arithmetic.py'): [],
         ('sub',
          'folder1/arithmetic.py'): [('folder1/arithmetic.py', 'list_sub', 'code'),
          ('folder1/test_arithmetic.py', 'test_sub', 'test')],
         ('test_concat', 'folder2/test_strings.py'): [],
         ('test_sub', 'folder1/test_arithmetic.py'): []
         } 

    def get_callers(sig, file_name, call_dict):
        end_name = sig.find('(')
        if end_name==-1:
            print(f'get_callers warning: did not find ( in {sig}')
            return []
        name = sig[:end_name].strip()
        if (name, filename) not in call_dict:
            print(f'get_callers warning: did not find {(name,filename)} in call_dict')
            return []
        return call_dict[(name, filename)]

    #only need this if missing entry in project_callers
    def get_tests(filename, signature, extension, testing_kind):
        if extension == '.py' and testing_kind in ['pytest']:
            return ''
        return ''

    project = list(Project.objects.all().filter(id=prid).all())[0]  #get project name

    # Get branch
    branch = ''
    if request.GET.get('branch'):
        branch = request.GET.get('branch')

    #Refresh repo

    #Switch to branch

    # Get filename
    filename = ''
    if request.GET.get('filename'):
        filename = request.GET.get('filename')

    # Get file type
    import os, mimetypes
    name, extension = os.path.splitext(filename)
    if not extension:
        extension = mimetypes.guess_extension(filename)

    docstring_kind = project_info[prid]['docstring_kind'] if prid in project_info else 'Unknown'
    testing_kind = project_info[prid]['testing_kind'] if prid in project_info else 'Unknown'

    # read file so can get signatures and doc strings

    with open('../'+project.name+'/'+filename, 'r') as f:
        lines = f.readlines()
        f.close()

    def get_py_signature(lines, i):
        if not lines[i].startswith('def '): return i, ''
        j = i
        while not lines[i].strip().endswith(':'):
            i += 1
            if i >= len(lines):
                print(f'get_signature warning: no colon found for {lines[j]}')
                return i, ''
        return i, ''.join([line for line in lines[j:i+1]]).strip('\n')[4:]

    def get_py_doc_string(lines, i):
        #skip over white space
        while lines[i].strip()=='':
            i+=1
        #check for triple quotes
        if lines[i].strip() not in ["'''", '"""']: return (i, [], [['No docstring found',i]])  #did not find
        doc_start = i
        i+=1  #move beyond opening quotes
        docstring = []
        issue = []
        while i<len(lines):
            if lines[i].strip() in ["'''", '"""']: break  #found end

            #keep adding lines
            docstring.append(lines[i])
            i += 1
        else:
            issue = [['No end found to docstring', doc_start]]

        return (i, docstring, issue)
        
    def check_py_numpy_param_match(signature:str, doc:list, doc_start:int):
        doc_string = ''.join(doc)
        import docstring_parser

        '''
          Parameters
          ----------
          x: int, real, complex
             first operand
          y: int, real, complex
             second operand
          round: positive int, optional
             If None, does no rounding. Else rounds the result to places specified, e.g., 2.
        '''
        parsed_doc = docstring_parser.numpydoc.parse(doc_string)
        params = parsed_doc.params
        param_names = [p.arg_name for p in params]
        param_types = [p.type_name for p in params]

        #for google
        '''

            Args:
                param1 (int): The first parameter.
                param2 (str): The second parameter.

            parsed_doc = docstring_parser.google.parse(doc)
            params = parsed_doc.params
            param_names = [p.arg_name for p in params]
            param_types = [p.type_name for p in params]
        '''

        arg_names = get_py_signature_args(signature)

        #check if 2 lists match up
        check = [p==a for p,a in zip(param_names,arg_names)]
        if not all(check):
            return [[f'mismatch. ARGUMENTS: {param_names}', doc_start]]
        return []

    def get_py_signature_args(signature):
        i = signature.find('(')
        if i==-1:
            print(f'get_py_signature_args found no starting ( in {signature}')
            return []
        j = signature.find(')')
        if j==-1:
            print(f'get_py_signature_args found no ending ) in {signature}')
            return []
        raw_args = signature[i+1:j].split(',')
        arg_names = []
        for raw in raw_args:
          i = raw.find(':')
          if i==-1:
            arg_names.append(raw.strip())
          else:
            arg_names.append(raw[:i].strip())
        return arg_names

    def check_robodoc_mandatory(mandatory:dict, doc_lines:list) -> list:
        #mandatory {'NAME': False, 'SYNOPSIS': False, 'DESCRIPTION': False, 'ARGUMENTS':False}

        mandatory_sections = mandatory.copy()
        issues = []
        j = 0
        while j<len(doc_lines):
            for section in mandatory_sections.keys():
                if doc_lines[j].find(section) != -1:
                    if mandatory_sections[section]:
                        #duplicate section
                        issues.append(f'{section} appears twice')
                    else:
                        mandatory_sections[section] = True  #all good
            j+=1  #keep looking

        for key,val in mandatory_sections.items():
            if not val: issues.append(f'mandatory {key} missing')

        return ['Mandatory sections present'] if not issues else issues

    def check_py_numpy_mandatory(mandatory:list, doc_lines:list) -> list:
        #doc_string = ''.join(doc)
        #import docstring_parser

        '''
          Parameters
          ----------
          x: ...
        '''
        found = []
        i = 0
        while i<len(doc_lines):
            for man in mandatory:
                if lines[i].strip()==man and lines[i+1].strip()=='-'*len(man):
                    #found section - is it empty?
                    if lines[i+2].strip() != '':
                        found.append((man, True))
                    else:
                        found.append((man, False))  #empty section
                    i += 2
                    break
            else:
                #did not break so move 1 line ahead
                i += 1

        issues = []
        for man in mandatory:
            ct = found.count((man,True))
            cf = found.count((man,False))
            if (ct+cf)==0:
                issues.append(f'Missing mandatory section {man}')
            elif ct==1 and cf==0:
                continue #looks good
            elif ct==0 and cf==1:
                issues.append(f'Mandatory section {man} empty')
                continue
            elif (ct+cf)>1:
                issues.append(f'Mandatory section {man} appears twice')
                continue

        return issues

    def check_f90_robodoc_param_match(signature, doc_lines) -> str:
        assert isinstance(signature, str)
        assert isinstance(doc_lines, list)

        '''
        !! ARGUMENTS
        !!  blkcnt - number of blocks
        !!  blklst : block list
        !!  nstep - current cycle number
        !!  dt,ds - current time step length (2 args)
        !!  stime - current simulation time
        '''

        #first find the ARGUMENTS section
        j = 0
        while j<len(doc_lines):
            k = doc_lines[j].find('ARGUMENTS')
            if k != -1: break  #found it
            j+=1  #keep looking
        else:
            #Get here if while condition is false
            return ['ARGUMENTS heading not found in docstring']

        #found ARGUMENTS section - now get arguments
        all_headers = ['NAME','SYNOPSIS','DESCRIPTION','PARAMETERS','RESULT','EXAMPLE','SIDE EFFECTS', 'NOTES','SEE ALSO']
        param_names = []
        param_types = []
        j += 1  #move beyond ARGUMENTS line
        while j<len(doc_lines):

            #check if ends by a non-comment line
            if not doc_lines[j].startswith('!!'):
                break

            #check if get to new section (so end of ARGUMENTS)
            line = doc_lines[j][2:].strip()  #remove !! and padding
            if line in all_headers:
                break

            #check if - or : in line. If so, argument name is defined
            hyphen = line.find(' - ')
            index = line.find(' : ') if hyphen == -1 else hyphen  #try colon if do not find hyphen 

            #if not found, keep moving along
            if index == -1:
                j += 1
                continue  #looking for - to signal arg name

            #record arg name(s) found
            arg_name = line[:index].strip()
            for aname in arg_name.split(','):  #can have more than one name preceding hyphen
                param_names.append(aname)
            j += 1

        #have param_names - now get actual params from sig
        i = signature.find('(')
        j = signature.find(')')
        assert i != -1 and j != -1

        #build list of actual params
        arg_names = [arg.strip() for arg in signature[i+1:j].split(',')]

        #check if 2 lists match up
        check = [p==a for p,a in zip(param_names,arg_names)]
        if not all(check):
            return [f'mismatch. ARGUMENTS: {param_names}']
        return ['ARGUMENTS match']

    def get_robodoc_string_plus_sig(lines, i):
        assert lines[i].startswith('!!****if*')  or lines[i].startswith('!!****f*')#assumes lines[i] is beginning of docstring

        #returns
        #   i: index of last line of signature
        #   doc: list of lines of docstring preceding signature
        #   sig: signature as string with no \n or &, e.g., 'foo(a,b,c)'
        #   issue: string that describes issues found while parsing

        j = i
        i+=1  #move past header
        #found header now look for ending
        while not lines[i].startswith('!!**') and lines[i].startswith('!!'):
            i+=1  #move to next
            if i>=len(lines):
                return i-1, lines[j:i-1], '', [f'No end found for docstring starting with {lines[j]}']
        #found non comment line - assume ending
        i+=1  #move past ending
        doc = lines[j:i]

        #now look for subroutine
        while not lines[i].startswith('subroutine '):
            i += 1
            if i >= len(lines):
                return i-1, doc, '', [f'No subroutine found for docstring {lines[j]}']
        j = i
        while not lines[i].strip().endswith(')'):
            i += 1
            if i >= len(lines):
                return i-1, doc, ' '.join(lines[j:j+1]).strip('\n').replace('&', ' ')[10:], [f'No closing ) for subroutine {lines[j]}']

        #looks good!
        return i, doc, ' '.join(lines[j:i+1]).strip('\n').replace('&', ' ')[10:], []

    ###################################
    # Start main code

    # handle flash5

    # robodoc guidelines taken from https://flash.rochester.edu/site/flashcode/user_support/robodoc_standards_F3/

    if extension == '.F90' and docstring_kind == 'robodoc':
        function_info = []
        i = 0
        while i<len(lines):

            #look for docstring
            if lines[i].startswith('!!****f*') or lines[i].startswith('!!****if*'):
                i, doc_lines, sig_string, collection_issue = get_robodoc_string_plus_sig(lines, i)  #parses out both docstring and signature
                function_info.append((sig_string, doc_lines, collection_issue))
                

            #look for subroutine with missing docstring
            elif lines[i].startswith('subroutine '):
                #found subroutine while looking for docstring - so missing docstring
                j = i
                nodoc_issue = ['No docstring']
                while not lines[i].strip().endswith(')'):
                    i += 1
                    if i >= len(lines):
                        nodoc_issue.append(f'No ) found for {lines[j]} so added')
                        function_info.append((' '.join(lines[j:i]).strip('\n').replace('&', ' ')[10:]+')', [], nodoc_issue))
                        break
                if i>=len(lines): break
                #looks good
                function_info.append((' '.join(lines[j:i+1]).strip('\n').replace('&', ' ')[10:], [], nodoc_issue))  #no doc string

            i+=1  #keep looking

        #done looking for docstrings and subroutines in file. Now work on callers and docstring alignment and mandatory fields

        extended_info = []
        mandatories = project_info[prid]['docstring_mandatory']
        for sig, doc, issue in function_info:
            param_issues  = check_f90_robodoc_param_match(sig, doc) if doc else []
            mandatory_issues  = check_robodoc_mandatory(mandatories, doc) if doc else []
            supported = False 
            caller_list = []
            call_dict = {} if prid not in project_callers else project_callers[prid]
            if call_dict:
                supported = True
                caller_list = get_callers(sig, filename, call_dict)
            print(issue, param_issues, mandatory_issues)
            all_issues = issue + param_issues + mandatory_issues
            extended_info.append((sig, doc, all_issues, supported, caller_list))  #add in new issues, and caller info

        function_table = [{'signature_name': sig[:sig.find('(')], 'signature_params':sig[sig.find('('):].replace(',', ', '), 'docstring': ''.join(doc), 'result': issues, 'supported': supported, 'callers':callers} for sig, doc, issues, supported, callers in extended_info]

    elif extension == '.py' and docstring_kind == 'numpy':  #anl_test_repo
        function_info = []
        i = 0
        while i<len(lines):
            line = lines[i]
            sig_start = i
            i, signature = get_py_signature(lines,i)
            if not signature:
                i += 1  #move on and keep searching
                continue

            #is signature line - check for doc string
            issues = []
            sig_end = i
            i, doc, issue = get_py_doc_string(lines, sig_end+1)
            issues.append(issue)
            i += 1  #move beyond docstring

            if doc:
                param_issue = check_py_numpy_param_match(signature, doc)
                mandatory_issue = check_numpy_mandatory(['params', 'returns', 'raises'], doc)
                issues.append(param_issue)

            supported = False 
            caller_list = []
            call_dict = {} if prid not in project_callers else project_callers[prid]
            if call_dict:
                supported = True
                caller_list = get_callers(signature, filename, call_dict)

            function_info.append((signature, doc, issues, supported, caller_list))

        function_table = [{'signature_name': sig[:sig.find('(')], 'signature_params':sig[sig.find('('):].replace(',', ', '), 'docstring': ''.join(doc), 'result': ','.join([iss for iss in issues if iss]), 'supported': supported, 'callers':callers} for sig, doc, issues, supported, callers in function_info]

    else:
        function_table = []  #can't handle project yet


    # Build developer table

    diffs = Diff.objects.all().filter(commit__project=project, file_path=filename).all()

    #print(diffs)
    author_loc = {}

    for d in diffs:
        body = d.body
        author = d.commit.author
        loc_count = body.count('\n+') + body.count('\n-')
        if author in author_loc:
            author_loc[author] += loc_count 
        else:
            author_loc[author] = loc_count

    # Get commits, authors for those (diffs)

    info = [(d.commit.datetime, d.commit.author, d.commit.hash) for d in diffs]
    commit_messages = [d.commit.message for d in diffs]
    commit_hashes = [d.commit.hash for d in diffs]

    tags = CommitTag.objects.all().filter(sha__in=commit_hashes)

    prs = list(set(PullRequest.objects.all().filter(commits__in=tags)))  #all prs that go with file commits

    pr_messages = [(pr.number, pr.url, pr.title, pr.description) for pr in prs]

    '''
    print('pr_messages', '\n')
    for n, u, title, desc in pr_messages:
        print(n, ' ', u)
        print(title, ' ::: ', desc, '\n')
    '''
    pr_comments = list(Comment.objects.all().filter(pr__in=prs))

    print('comments','\n')
    for com in pr_comments:
        print(com.author, ' ', com.body, '\n')

    issues = list(Issue.objects.all().filter(url__in=[pri.issue.url for pri in PullRequestIssue.objects.all().filter(pr__in=prs).all()]))

    print('issues', issues, '\n')

    #issue_number = re.search(r'#\d+', pr.description)

    #closed_issue_list = list(Issue.objects.all().filter(url=project.source_url.replace('.git', '/issues/'+issue_number.group()[1:])))

    #issue_messsages = [(iss.title, iss.description) for iss in closed_issue_list]

    #issue_comments = list(Comment.objects.all().filter(issue__in=closed_issue_list))

    #print('issue comments', issue_comments)
    author_count = {}
    for date, author, link in info:
        if author in author_count:
            author_count[author] += 1
        else:
            author_count[author] = 1

    new_info = []
    authors = []
    for date, author, link in sorted(info, reverse=False):
        if author in authors: continue
        new_info.append((date, author, author_count[author], author_loc[author], link))
        authors.append(author)


    #see here for avoiding author alisases: https://towardsdatascience.com/string-matching-with-fuzzywuzzy-e982c61f8a84
    #combine counts for same author with different aliases.

    dev_table = [{'author':author, 'number_commits': count, 'lines': loc, 'most_recent_commit':date,'commit_link':link} for date, author, count, loc, link in new_info]

    # Build blame table


    '''
    cmd = f'cd ../{project.name} ; git blame {filename} > {filename[filename.rindex("/")+1:]}.blame'
    os.system(cmd)
    #result = subprocess.check_output(cmd, shell=True)

    #with open('../ideas-uo/anl_test_repo/arithmetic.py.patch', 'r') as f:
    with open('../'+project.name+'/'+filename[filename.rindex('/')+1:]+'.blame', 'r') as f:
        lines = f.readlines()
        f.close()
    os.remove('../'+project.name+'/'+filename[filename.rindex('/')+1:]+'.blame') 

    print(f'blame:\n{lines}')
    '''

    def compute_issue_url(pr):
        issue_tags = ['close', 'closes', 'closed', 'fix', 'fixes', 'fixed', 'resolve', 'resolves', 'resolved']
        description = pr.description.strip()
        for tag in issue_tags:
            if tag+' #' in description or tag+'#' in description:
                i = description.find('#')
                issnum = int(description[i+1:])
                issue_list = list(Issue.objects.all().filter(url=project.source_url.replace('.git', '/issues/'+issnum.group()[1:])))
                issue_url = issue_list[0].url
                return [tag, issue_url]
        return ['','']

    prs_table = sorted([{'number':pr.number, 'url':pr.url, 'issue_url': compute_issue_url(pr), 'notes':['Signature Change'] if pr.number==1279 else ["Work in Progress"], 'notes_kind':'Major' if pr.number==1279 else 'TBD'} for pr in prs], key=lambda d: d['number'])



    #diffs = Diff.objects.all().filter(file_path=filename).all()

    # List Issues

    #diffs = Diff.objects.all().filter(file_path=filename).all()

    context = {'file':filename,
                 'project': project,
                 'language': extension,
                 'documentation': docstring_kind,
                 'branch':branch,
                 'authors':dev_table,
                 'authors_len': len(dev_table),
                 'functions_supported': True if function_table else False,
                 'functions':function_table,
                 'prs':prs_table
                 }

    return HttpResponse(template.render(context, request))




# Refresh the GIT and GitHub data for a project (INTENTIONALLY ONLY WORKS FOR PROJECT ID 30)
@login_required
def refreshProject(request):
    print("REFRESH")

    pid = 30
    if request.GET.get('pid'):
        pid = int(request.GET.get('pid'))

    if not hasAccessToProject(request.user, pid):
        return redirect('not_authorized')

    project = list(Project.objects.all().filter(id=pid).all())[0]

    username = settings.DATABASES['default']['USER']
    password = settings.DATABASES['default']['PASSWORD']

    cmd = f'cd .. ; export PYTHONPATH=. ; nohup python3 ./src/gitutils/update_database.py {username} {password} {pid}'
    os.system(cmd)
    result = subprocess.check_output(cmd, shell=True)
    #print(result)
    
    resultdata = {
        'status':'success'
    }

    return HttpResponse(
        json.dumps(resultdata),
        content_type='application/json'
    )


# Refresh the GIT and GitHub data for a project (INTENTIONALLY ONLY WORKS FOR PROJECT ID 30)
@login_required
def createPatch(request):
    print("CREATE PATCH")

    prid = 2250
    if request.POST.get('pr'):
        prid = int(request.POST.get('pr'))

    if not hasAccessToPR(request.user, prid):
        return redirect('not_authorized')

    filename = 'folder1/arithmetic.py'
    if request.POST.get('filename'):
        filename = request.POST.get('filename')

    print(filename)
    print(filename.rindex('/'))
    print(filename[filename.rindex('/')+1:])

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    #project = list(Project.objects.all().filter(id=pid).all())[0]


    #TODO pull name from request and project from pr id

    #with open('../ideas-uo/anl_test_repo/folder1/arithmetic.py', 'w') as f:
    with open('../'+pr.project.name+'/'+filename, 'w') as f:
        f.write(request.POST.get('filecontents'))
        f.close()
    
    #cmd = f'cd ../ideas-uo/anl_test_repo ; git diff folder1/arithmetic.py > arithmetic.py.patch'
    cmd = f'cd ../'+pr.project.name+' ; git diff '+filename+' > '+filename[filename.rindex('/')+1:]+'.patch'
    os.system(cmd)
    #result = subprocess.check_output(cmd, shell=True)

    #with open('../ideas-uo/anl_test_repo/arithmetic.py.patch', 'r') as f:
    with open('../'+pr.project.name+'/'+filename[filename.rindex('/')+1:]+'.patch', 'r') as f:
        lines = f.readlines()
        f.close()
    os.remove('../'+pr.project.name+'/'+filename[filename.rindex('/')+1:]+'.patch')    

    #cmd = f'cd ../ideas-uo/anl_test_repo ; git checkout -- folder1/arithmetic.py'
    cmd = f'cd ../'+pr.project.name+' ; git checkout -- '+filename
    os.system(cmd)


    resultdata = {
        'status':'success',
        'filename':filename[filename.rindex('/')+1:]+'.patch',
        'patch': ''.join(lines)
    }

    return HttpResponse(
        json.dumps(resultdata),
        content_type='application/json'
    )


# Retrieves commit data for a specific PR
@login_required
def diffCommitData(request):
    print("Diff Commit DATA")

    print(request.POST.get('pr'))

    prid = 2250
    if request.POST.get('pr'):
        prid = int(request.POST.get('pr'))

    if not hasAccessToPR(request.user, prid):
        return redirect('not_authorized')

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    #Find all changed files related to the PR by getting all diffs from all commits in PR    
    commits = list(Commit.objects.all().filter(hash__in=[committag.sha for committag in set(pr.commits.all())]))

    print("Commits: "+str(len(commits)))

    diffs = list(Diff.objects.all().filter(commit__in=[c for c in commits]))
    filenames = [d.file_path for d in diffs]
    #Get just unique filenames
    filenames_set = set(filenames)
    filenames = list(filenames_set)

    #Now find all commits and diffs for the changed files in the past 60 days
    #date = datetime.datetime.now() - datetime.timedelta(days=60)
    date = pr.created_at - datetime.timedelta(days=60)
    enddate = pr.created_at + datetime.timedelta(days=1)
    diffcommits = []

    print(pr.created_at)
    print(date)

    filtereddiffs = Diff.objects.all().filter(commit__project=pr.project, commit__datetime__gte=date, commit__datetime__lte=enddate)
    for filename in filenames:
        diffcommits.append( {'filename': filename, 'commits':[{'commit':d.commit.hash, 'diff':d.body} for d in filtereddiffs.filter(file_path=filename)]} )

    prcommits = []
    for commit in commits:
        prcommits.append({'hash':commit.hash})

    docstring_results = first_responder_function(pr.project, pr)

    linter_results = []
    for filename in filenames:
        if filename.endswith('.py'): 
            output = os.popen('export PYTHONPATH=${PYTHONPATH}:'+os.path.abspath('../'+pr.project.name)+' ; cd ../'+pr.project.name+' ; pylint --output-format=json '+filename).read()
            linter_results.append( {'filename': filename, 'results':json.loads(output)} )

    
    #Build developer table
    author_loc = {}

    diffs = Diff.objects.all().filter(commit__project=pr.project, file_path__in=filenames).all()

    for d in diffs:
        body = d.body
        author = d.commit.author
        loc_count = body.count('\n+') + body.count('\n-')
        if author in author_loc:
            author_loc[author] += loc_count 
        else:
            author_loc[author] = loc_count

    # Get commits, authors for those (diffs)
    info = [(d.commit.datetime, d.commit.author, d.commit.hash) for d in diffs]
    commit_messages = [d.commit.message for d in diffs]
    commit_hashes = [d.commit.hash for d in diffs]

    author_count = {}
    for date, author, link in info:
        if author in author_count:
            author_count[author] += 1
        else:
            author_count[author] = 1

    new_info = []
    authors = []
    for date, author, link in sorted(info, reverse=False):
        if author in authors: continue
        new_info.append((date, author, author_count[author], author_loc[author], link))
        authors.append(author)

    #see here for avoiding author alisases: https://towardsdatascience.com/string-matching-with-fuzzywuzzy-e982c61f8a84
    #combine counts for same author with different aliases.
    dev_table = [{'author':author.username+' - '+author.email, 'number_commits': count, 'lines': loc, 'most_recent_commit':date.strftime('%Y-%m-%d, %H:%M %p'),'commit_link':link} for date, author, count, loc, link in new_info]

    resultdata = {
        'diffcommits':diffcommits,
        'prcommits':prcommits,
        'docstring_results':docstring_results,
        'linter_results':linter_results,
        'dev_table':dev_table,
        'source_url':pr.project.source_url[0:-4]
    }

    return HttpResponse(
        json.dumps(resultdata),
        content_type='application/json'
    )


@login_required
def getFile(request):

    print("Get File DATA")

    #print(request.POST.get('pr'))

    prid = 2250
    if request.POST.get('pr'):
        prid = int(request.POST.get('pr'))

    if not hasAccessToPR(request.user, prid):
        return redirect('not_authorized')

    filename = 'folder1/arithmetic.py'
    if request.POST.get('filename'):
        filename = request.POST.get('filename')

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]


    # Open and read the file
    with open('../'+pr.project.name+'/'+filename, 'r') as f:
        lines = f.readlines()
        f.close()

    # If python file or fortran file, get linter results
    linter_results = []
    #docstring_results = []

    if filename.endswith('.py'): 
        output = os.popen('export PYTHONPATH=${PYTHONPATH}:'+os.path.abspath('../'+pr.project.name)+' ; cd ../'+pr.project.name+' ; pylint --output-format=json '+filename).read()
        linter_results = json.loads(output)
        #docstring_results = first_responder_function(pr.project, pr)

    if filename.endswith('.F90'): 
        output = os.popen('fortran-linter ../'+pr.project.name+'/'+filename+' --syntax-only').read()
        linter_results = json.loads(output.split('../'+pr.project.name+'/'+filename))

    #print("LINTER RESULTS: "+str(linter_results))
    #print("DOC CHECKER RESULTS: "+str(docstring_results))



    resultdata = {
        'filecontents': ''.join(lines),
        'linter_results': linter_results
    }

    return HttpResponse(
        json.dumps(resultdata),
        content_type='application/json'
    )


@csrf_exempt
def githubBot(request):

    print("Callback from webhook bot on github")

    payload = json.loads(request.body)

    #print( str(payload) )

    print( "Action Type: " + str(payload['action']) )
    print( "Pull Request Number: " + str(payload['number']) )
    print( "Repository: " + str(payload['repository']['clone_url']) )
    print( "Draft: " + str(payload['pull_request']['draft']) )

    prnumber = str(payload['number'])

    if str(payload['action']) == 'opened':

        project = list(Project.objects.all().filter(source_url=str(payload['repository']['clone_url'])).all())[0]

        # Only post comments for anl_test_repo and FLASH5
        if project.id == 30 or project.id == 26:
            try:
                repo_name = project.name
                repo_owner = get_repo_owner(project)
                url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{prnumber}/comments"
                payload = { "body": "## MeerCat is working on this PR.  Please stay tuned." }
                headers = {
                    "Accept": "application/vnd.github+json",
                    "Authorization" : "token " + os.environ.get('MEERCAT_USER_TOKEN')
                }
                result = requests.post(url, headers=headers, data=json.dumps(payload))
            except:
                pass 

        #Need to refresh the database before 
        username = settings.DATABASES['default']['USER']
        password = settings.DATABASES['default']['PASSWORD']
        cmd = f'cd .. ; export PYTHONPATH=. ; nohup python3 ./src/gitutils/update_database.py {username} {password} {project.id}'
        os.system(cmd)
        result = subprocess.check_output(cmd, shell=True)

        pull_request = list(PullRequest.objects.all().filter(project=project.id, number=int(prnumber)).all())[0]

        #TODO: eventually only do this for new PRs (check payload for action type I think)

        if pull_request:

            comment = first_responder_function(pull_request.project, pull_request)[0]
            print("------------")
            if comment:
                # Only post comments for anl_test_repo and FLASH5
                if project.id == 30 or project.id == 26:
                    comment_pullrequest(pull_request, comment)
                    print("commented")
                else:
                    event = EventLog(
                        event_type=EventLog.EventTypeChoices.NOTIFICATION,
                        log=comment,
                        pull_request=pull_request,
                        datetime=datetime.today()
                    )
            else:
                event = EventLog(
                    event_type=EventLog.EventTypeChoices.NO_NOTIFICATION,
                    pull_request=pull_request,
                    datetime=datetime.today()            
                )
                print("don't bug me")

            print("------------")


    return HttpResponse(
        json.dumps({'results':'success'}),
        content_type='application/json'
    )


# Uses the Visualizer code to generate a graph.
# Works just for FLASH5 at the moment, but can be made to be more generic.
@login_required
def patternGraph1(request):
    print("PATTERN DATA")

    print( request.GET.get('start') )

    startdate = request.GET.get('start')
    enddate = request.GET.get('end')

    if startdate: 
        startdate = datetime.datetime.strptime(startdate, '%Y-%m-%d')
    else:
        startdate = datetime.datetime.fromtimestamp(0)

    if enddate: 
        enddate = datetime.datetime.strptime(enddate, '%Y-%m-%d')
    else:
        enddate = datetime.datetime.today()

    
    prid = 2250
    if request.GET.get('pr'):
        prid = int(request.GET.get('pr'))

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]
    commits = list(Commit.objects.all().filter(hash__in=[committag.sha for committag in pr.commits.all()]))
    diffs = list(Diff.objects.all().filter(commit__in=[c for c in commits]))
    filenames = [d.file_path for d in diffs]

    
    

    # Visualizer()
    # vis = Visualizer(project_name='FLASH5')
    # vis.get_data()

    #removed = vis.remove_external()
    # removed = vis.remove_files(filenames)

    # vis.hide_names = False

    #Setting year or range seems to break some graphs
    #if startdate.year == enddate.year:
    
    # TEMPORARILY VIEW ALL YEARS
    #vis.set_year(enddate.year)
    
    #vis.select_month_range()
    #else:    
    #    vis.select_year_range(startdate.year,enddate.year)

    #df = vis.plot_zone_heatmap(agg='mean')
    #df = vis.plot_top_N_heatmap(10, locc_metric='locc')
    
    # TEMPORARILY VIEW ALL YEARS
    #df = vis.plot_top_N_heatmap(10, time_range='year', locc_metric='change-size-cos')
    #df = vis.plot_top_N_heatmap(10, locc_metric='change-size-cos')

    resultdata = {
        #'filename': 'spack-zone-change-size-cos-map-Entire_project-mean.png',
        #'filename': 'FLASH5-top-10-locc-map-Entire_project.png',
        #'filename': 'FLASH5-top-10-change-size-cos-map-'+str(enddate.year)+'.png',
        'filename': 'FLASH5-top-10-change-size-cos-map-Entire_project.png',
    }

    return HttpResponse(
    	json.dumps(resultdata),
    	content_type='application/json'
    )


# Branches view (is this still needed)
@login_required
def branches(request):
    print("BRANCHES")
    template = loader.get_template('dashboard/branches.html')
    context = {}

    return HttpResponse(template.render(context, request))


# Returns branch data for anl_test_repo
# If this is still useful, need to make more generic
@login_required
def branchData(request):
    print("BRANCHES DATA")

    config = configparser.ConfigParser()
    config.read('../credentials.ini')

    GitHubAPIClient.set_credentials(username=config['github']['login'], token=config['github']['token'])

    GitHubAPIClient.check_credentials()

    data = GitHubAPIClient.fetch_events(owner='fickas', repository='anl_test_repo')

    df = pd.DataFrame(data)

    created_branches = []
    deleted_branches = []
    for i in range(len(df)):
        if df.loc[i, 'type'] == 'CreateEvent' and df.loc[i, 'payload']['ref_type'] == 'branch':
            created_branches.append(df.loc[i, 'payload']['ref'])
        if df.loc[i, 'type'] == 'DeleteEvent' and df.loc[i, 'payload']['ref_type'] == 'branch':
            deleted_branches.append(df.loc[i, 'payload']['ref'])

    open_branches = set(created_branches)-set(deleted_branches)
    feature_branches = list(open_branches-set(['main', 'development', 'staged']))



    branches = pd.DataFrame(columns=['Name', 'Author', 'Created', 'Deleted']).set_index('Name')

    for i in range(len(df)):
        if df.loc[i, 'type'] in ['CreateEvent', 'DeleteEvent'] and df.loc[i, 'payload']['ref_type'] == 'branch':
            name = df.loc[i, 'payload']['ref']
            author =  df.loc[i, 'actor']['login']
            date = df.loc[i, 'created_at']
            event_type = 'Created' if df.loc[i, 'type'] == 'CreateEvent' else 'Deleted'
            if name in branches.index.to_list():
                branches.loc[name, event_type] = date
                branches.loc[name, 'Author'] = author
            else:
                row = {'Author': author, 'Created': '', 'Deleted':''}
                branches.loc[name] = row
                branches.loc[name, event_type] = date

    #TODO: update this to only attempt to drop if keys exist, otherwise error is thrown.
    #branches = branches.drop(['main', 'staged', 'development']).fillna('None')

    #might be easier to use for javascript
    name_column = branches.index.to_list()
    author_column = branches['Author'].to_list()
    created_column = branches['Created'].to_list()
    deleted_column = branches['Deleted'].to_list()



    resultdata = {
        'open_branches': list(open_branches),
        'created_branches': created_branches,
        'deleted_branches': deleted_branches,
        'feature_branches': feature_branches,
        'name_column': name_column,
        'author_column': author_column,
        'created_column': created_column,
        'deleted_column': deleted_column
    }


    return HttpResponse(
    	json.dumps(resultdata),
    	content_type='application/json'
    )


def countlines(start, lines=0, header=True, begin_start=None):
    #if header:
    #    print('{:>10} |{:>10} | {:<20}'.format('ADDED', 'TOTAL', 'FILE'))
    #    print('{:->11}|{:->11}|{:->20}'.format('', '', ''))

    # TODO: Currently only counds python code.

    for thing in os.listdir(start):
        thing = os.path.join(start, thing)
        if os.path.isfile(thing):
            if thing.endswith('.py'):
                with open(thing, 'r') as f:
                    newlines = f.readlines()
                    newlines = len(newlines)
                    lines += newlines

                    #if begin_start is not None:
                    #    reldir_of_thing = '.' + thing.replace(begin_start, '')
                    #else:
                    #    reldir_of_thing = '.' + thing.replace(start, '')

                    #print('{:>10} |{:>10} | {:<20}'.format(newlines, lines, reldir_of_thing))


    for thing in os.listdir(start):
        thing = os.path.join(start, thing)
        if os.path.isdir(thing):
            lines = countlines(thing, lines, header=False, begin_start=start)

    return lines


def countlinespython(start, lines=0, header=True, begin_start=None):

    for thing in os.listdir(start):
        thing = os.path.join(start, thing)
        if os.path.isfile(thing):
            if thing.endswith('.py'):
                with open(thing, 'r') as f:
                    newlines = f.readlines()
                    newlines = len(newlines)
                    lines += newlines

    for thing in os.listdir(start):
        if not thing.startswith('.git') and not thing.startswith('repos'):
            thing = os.path.join(start, thing)
            if os.path.isdir(thing):
                lines = countlinespython(thing, lines, header=False, begin_start=start)

    return lines


def countlinesfortran(start, lines=0, header=True, begin_start=None):

    for thing in os.listdir(start):
        thing = os.path.join(start, thing)
        if os.path.isfile(thing):
            if thing.endswith('.F90'):
                with open(thing, 'r') as f:
                    newlines = f.readlines()
                    newlines = len(newlines)
                    lines += newlines

    for thing in os.listdir(start):
        if not thing.startswith('.git') and not thing.startswith('repos'):
            thing = os.path.join(start, thing)
            if os.path.isdir(thing):
                lines = countlinesfortran(thing, lines, header=False, begin_start=start)

    return lines

def countlinesc(start, lines=0, header=True, begin_start=None):

    for thing in os.listdir(start):
        thing = os.path.join(start, thing)
        if os.path.isfile(thing):
            if thing.endswith('.c') or thing.endswith('.h') or thing.endswith('.cpp'):
                with open(thing, 'r') as f:
                    try:
                        newlines = f.readlines()
                        newlines = len(newlines)
                        lines += newlines
                    except:
                        pass    

    for thing in os.listdir(start):
        if not thing.startswith('.git') and not thing.startswith('repos'):
            thing = os.path.join(start, thing)
            if os.path.isdir(thing):
                lines = countlinesc(thing, lines, header=False, begin_start=start)

    return lines

def countfiles(start, files=0, header=True, begin_start=None):

    # TODO: Counts all files

    for thing in os.listdir(start):
        thing = os.path.join(start, thing)
        if os.path.isfile(thing):
            files += 1

    for thing in os.listdir(start):
        if not thing.startswith('.git') and not thing.startswith('repos'):
            thing = os.path.join(start, thing)
            if os.path.isdir(thing):
                files = countfiles(thing, files, header=False, begin_start=start)

    return files


def hasAccessToProject(user, project_id):
    if user.is_staff:
        return True

    return ProjectRole.objects.filter(user__id=user.id, project=project_id).exists()

def hasAccessToPR(user, pr_id):
    if user.is_staff:
        return True

    project_id = PullRequest.objects.get(id=pr_id).project.id
    return ProjectRole.objects.filter(user__id=user.id, project=project_id).exists()

#localhost:8080/dashboard/firstresponder/26?prid=17
def firstresponder(request, *args, **kwargs):

    #template = loader.get_template('dashboard/firstresponder.html')


    # Get PR id
    if kwargs['pk']:
        proj_id = int(kwargs['pk'])
    else:
        return HttpResponse(
            json.dumps('Missing project'),
            content_type='application/json'
            )

    project_info = get_project_info(proj_id)

    if project_info==None:
        return HttpResponse(
            json.dumps(f'Project id missing from project_info {proj_id}'),
            content_type='application/json'
            )

    proj_list = list(Project.objects.all().filter(id=proj_id).all())
    if not proj_list:
        return HttpResponse(
            json.dumps(f'Unknown project {proj_id}'),
            content_type='application/json'
            )

    proj_object = proj_list[0]

    #proj_name = 

    if request.GET.get('prid'):
        pr_id = request.GET.get('prid')
    else:
        return HttpResponse(
            json.dumps(f'Missing Pull Request number'),
            content_type='application/json'
            )

    pr_list = list(PullRequest.objects.all().filter(id=pr_id).all())
    if not pr_list:
        return HttpResponse(
            json.dumps(f'Illegal Pull Request number {pr_id}'),
            content_type='application/json'
            )

    pr_object = pr_list[0]

    pr_info = first_responder_function(proj_object, pr_object)

    return HttpResponse(
        json.dumps(pr_info),
        content_type='application/json'
        )

def first_responder_function(proj_object, pr_object):

    proj_name = proj_object.name  #get project name
    proj_id = proj_object.id
    project_info = get_project_info(proj_id)  #see functions at end
    if project_info==None:
        return ['', [f'Project id missing from project_info {proj_id}']]

    if 'docstring_kind' in project_info:
        docstring_kind = project_info['docstring_kind']
    else:
        return ['', [f"Can't find docstring_kind"]]

    #get set up on right feature branch
    commits_list = list(Commit.objects.all().filter(hash__in=[committag.sha for committag in pr_object.commits.all()]))
    if not commits_list:
        return ['', [f'No commits found']]

    commit_messages = [c.message for c in commits_list]

    branch = commits_list[0].branch
    cmd = f'cd ../{proj_name} ; git checkout {branch}'
    try:
        os.system(cmd)
    except:
        return ['', [f'Failure to checkout branch {cmd}']]

    #get all files in PR
    diffs = list(Diff.objects.all().filter(commit__in=[c for c in commits_list]))
    filenames = [d.file_path for d in diffs]
    #Get just unique filenames
    filenames_set = set(filenames)
    filenames = list(filenames_set)
    file_lines = []
    for filename in filenames:
        name, extension = os.path.splitext(filename)
        if (extension and extension in project_info['extensions']) or (not extension and filename in project_info['filenames']):
            with open('../'+proj_name+'/'+filename, 'r') as f:
                lines = f.readlines()
                f.close()
            file_lines.append((filename, name,  extension, lines))
        else:
            print(f'Uncheckable currently: {filename}')
            file_lines.append((filename, name,  extension, None))

    #Gather info on each file in file_lines
    all_files = []
    for path, name, extension, lines in file_lines:

        if not lines:
            continue  #no lines to check for file

        #check cases of language cross doc type

        if proj_id==26:  #Flash5
            function_info = []
            i = 0  #start at top of file
            while i<len(lines):

                #look for robodoc docstring  (*if* says internal)
                if lines[i].startswith('!!****f*') or lines[i].startswith('!!****if*'):
                    doc_start = i
                    i, doc_lines, doc_fields, sig_string, params, collection_issue = get_f90_robodoc_string_plus_sig(lines, i)  #parses out both docstring and signature, i last line of doc
                    function_info.append((sig_string, doc_lines, doc_fields, doc_start, collection_issue))

                #look for doxygen
                elif lines[i].startswith('!>'):
                    doc_start = i
                    i, doc_lines, doc_fields, sig_string, params, collection_issue = get_f90_doxygen_string_plus_sig(lines, i)  #parses out both docstring and signature, i last line of doc
                    function_info.append((sig_string, params, doc_lines, doc_fields, doc_start, collection_issue))
                    
                #look for subroutine with missing docstring
                elif lines[i].startswith('subroutine '):
                    params = []
                    doc_lines = []
                    doc_fields = []
                    doc_start = 0
                    #found subroutine while looking for docstring - so missing docstring
                    sub_start = i
                    nodoc_issue = [['No docstring', i]]

                    #deal with multi-line signature - uses & as line continuation
                    while not lines[i].strip().endswith(')'):
                        i += 1
                        if i >= len(lines):
                            nodoc_issue.append([f'No ) found for {lines[j]} so added', sub_start])
                            raw = ' '.join(lines[sub_start:i]).replace('&', ' ')[10:]+')'
                            full = ' '.join(raw.split())
                            function_info.append((full, params, doc_lines, doc_fields, doc_start, nodoc_issue))
                            break
                    if i>=len(lines): break

                    #found good signature
                    raw = ' '.join(lines[sub_start:i]).replace('&', ' ')[10:]
                    full = ' '.join(raw.split())
                    function_info.append((full, params, doc_lines, doc_fields, doc_start, nodoc_issue))  #no doc string

                i+=1  #keep looking through file

            #done looking for docstrings and subroutines in file. Now work on docstring alignment and mandatory fields
            print(f'done scan: {function_info}')

            extended_info = []
            mandatories = set(project_info['docstring_mandatory'])  #what are set of mandatory fields?
            for sig, params, doc, fields, doc_start, issue in function_info:
                if not doc:
                    extended_info.append((sig, params, doc, fields, doc_start, issue))  #no doc string found
                    continue
                #found docstring
                residue = mandatories - set(fields)
                mandatory_issues = [[f'Missing mandatory fields: {residue}' if residue else '', doc_start]]
                param_issues  = check_param_match(sig, params, doc_start)
                all_issues = issue + param_issues + mandatory_issues
                print(f'all_issues: {all_issues}')
                extended_info.append((sig, params, doc, fields, doc_start, all_issues))  #add in new issues

            file_table = [{'signature_name': sig[:sig.find('(')].strip(),
                          'signature_params':sig[sig.find('('):],
                          'docstring': ''.join(doc),
                          'doc_fields': fields,
                          'doc_start': doc_start,
                          'result': issues} for sig, params, doc, fields, doc_start, issues in extended_info]

            print(f'file_table: {file_table}')


        elif proj_id==30:  #anl_test_repo
            function_info = []  #find all the functions in the file and record info on each of them
            i = 0

            #find function signature then look for docstring following
            while i<len(lines):
                sig_start = i
                i, sig_name, sig_params = get_py_signature(lines,i)
                if not sig_name:
                    i += 1  #move on and keep searching
                    continue
                #print(f'found function: {sig_name}')
                #is signature line - check for doc string
                sig_end = i
                doc, doc_start, doc_end, fields, doc_params, issues = get_py_doc_string(lines, sig_end+1)
                
                #after demo, pass in sig_params to check. test_info will have to expand.
                test_info = find_pytest_files(proj_name, path, sig_name)  #returns list of triples (path, file_name, i)

                #get ready to move test function to repo
                #cd '..'
                #proj_name in os.listdir()

                #import importlib
                #proj = importlib.import_module(proj_name, '')

                #proj.bin.meercat_test_functions.find_pytest_files(proj_name, path, sig_name)

                mandatories = project_info['docstring_mandatory']
                param_issues = check_py_numpy_param_match(sig_params, doc_params, doc_start) if doc else []
                mandatory_issues  = check_py_numpy_mandatory(mandatories, fields, doc_start) if doc else []
                all_issues = issues + param_issues + mandatory_issues
                function_info.append((sig_name, sig_params, (doc, doc_start, doc_end, fields, doc_params), test_info, all_issues))
                #print(f'function_info: {function_info}')

                i += 1  #move beyond docstring

            file_table = [{'signature_name': sig,
                          'signature_params':params,
                          'docstring': doc_info,
                          'test_info': test_info,
                          'result': all_issues} for sig, params, doc_info, test_info, all_issues in function_info]

            #done with py and numpy parsing case
        else:
            print(f'failed on {docstring_kind} and {extension}')
            file_table = []  #can't handle project yet

        all_files.append((name+extension, file_table))

    #all_files:
    #   name, file_table
    #       {'signature_name': sig, 'signature_params':params, 'docstring': doc_info, 'result': all_issues}
    #       {'signature_name': sig, 'signature_params':params, 'docstring': doc_info, 'result': all_issues}
    #       ...
    #       where doc_info = (doc, doc_start, doc_end, fields, doc_params)
    if all_files:
        k = 0
        n = len(all_files)
        for name,ft in all_files:
            for sig_dict in ft:
                if sig_dict['result']:
                    k += 1
                    break

        message = f'''# The MeerCat Pull-Request Assistant has information for you

## {k} out of {n} files in this PR were found to have issues.

## We have suggestions for adding tags.

## We have suggestions for adding more people to the discussion.

[Please see the Pull-Request Assistant page for more detail.](http://sansa.cs.uoregon.edu:8888/dashboard/pr/{pr_object.id})
    '''
    else:
        message = f'''# The MeerCat Pull-Request Assistant has information for you

## No files in this PR were analyzed.

## We have suggestions for adding tags.

## We have suggestions for adding more people to the discussion.

[Please see the Pull-Request Assistant page for more detail.](http://sansa.cs.uoregon.edu:8888/dashboard/pr/{pr_object.id})
    '''
    return [message, all_files]


#### Simulating global data about projects

def get_project_info(project_id):
    #simulate project info
    project_info = {
        26: {'docstring_kind': 'robodoc',
             'docstring_mandatory': [],
            'testing_kind': 'custom',
             'main':'master',
            'filenames':[],
            'extensions':['.F90']},  #flash5

        30: {'docstring_kind': 'numpy',
             'docstring_mandatory':['Parameters', 'Returns', 'Raises'],
            'testing_kind': 'pytest',
             'main':'main',
            'filenames':[],
            'extensions':['.py', '.F90']}     #anl_test_repo
    }
    return project_info[project_id] if project_id in project_info else None

#call with, e.g., 'anl_test_repo', 'folder1/arithmetic.py', 'sub'
def find_pytest_files(proj_name, file_path, function_name):
    #for full pytest dir setup see https://docs.pytest.org/en/7.1.x/explanation/goodpractices.html#conventions-for-python-test-discovery
    #here just assuming test files are in folder on file_path
    import os
    full_path = f'../{proj_name}/{file_path}'
    found_asserts = []
    while(True):
        head,tail = os.path.split(full_path)  #head now has containing dir for file
        if not head: break
        if tail==proj_name: break  #don't check above the repo
        all = os.listdir(head)  #files and folders
        #look for pytest files in dir
        for item in all:
            if os.path.isdir(item): continue  #skip over dirs
            name,extension = os.path.splitext(item)
            if 'test' in name and extension=='.py':
                print(f'found: {head}, {name}')
                with open(head+'/'+name+extension, 'r') as f:
                    lines = f.readlines()
                    f.close()
                i = 0
                while i<len(lines):
                    if lines[i].startswith('def test_'):
                        i+=1
                        while i<len(lines) and lines[i] != '\n':
                            if lines[i].strip().startswith('assert') and f' {function_name}(' in lines[i]:
                                j = head.find(f'{proj_name}/')
                                path = head[j+len(proj_name)+1:]
                                found_asserts.append((path, name+extension, i))
                            i += 1
                    i+=1
        full_path = head
    return found_asserts



def get_callers(sig, file_name):
    project_callers[30] =  { #needs to be part of project profile
     ('check_fum', 'folder1/arithmetic.py'): [],
     ('concat',
      'folder2/strings.py'): [('folder2/test_strings.py', 'test_concat', 'test')],
     ('count', 'folder2/strings.py'): [],
     ('foo',
      'folder3/more_functions.py'): [('folder2/strings.py', 'fum', 'code')],
     ('fum',
      'folder2/strings.py'): [('folder1/arithmetic.py', 'check_fum', 'code')],
     ('list_sub', 'folder1/arithmetic.py'): [],
     ('sub',
      'folder1/arithmetic.py'): [('folder1/arithmetic.py', 'list_sub', 'code'),
      ('folder1/test_arithmetic.py', 'test_sub', 'test')],
     ('test_concat', 'folder2/test_strings.py'): [],
     ('test_sub', 'folder1/test_arithmetic.py'): []
     } 
    end_name = sig.find('(')
    if end_name==-1:
        print(f'get_callers warning: did not find ( in {sig}')
        return []
    name = sig[:end_name].strip()
    if (name, filename) not in project_callers:
        print(f'get_callers warning: did not find {(name,filename)} in project_callers')
        return []
    return project_callers[(name, filename)]


#### Utility functions for parsing files and other things
def get_py_signature(lines, i):
    '''!
    @param lines - a file as a list of strings
    @param i - the line to check within lines (0 origin)
    @return returns a triple of values: i is last line of signature (same as input if no signature); string name, empty if no signature found; list of params
    @details looks for line starting with "def ". If found then keeps moving through lines looking for closing colon, i.e., ":". The name and list of params returned has
     the def and colon removed. If the : is not found before reachining end of the file (lines) then the function will be ignored, i.e.,
     an empty string will be returned and the value of i will be one past the last line.
    @callgraph
    @callergraph
    '''
    if not lines[i].startswith('def '): return i, '', []
    j=i
    while not lines[i].strip().endswith(':'):
        i += 1
        if i >= len(lines):
            print(f'get_signature warning: no colon found for {lines[j]}')
            return i, '', []
    raw = ''.join([line for line in lines[j:i+1]]).strip('\n')[4:]
    full = ' '.join(raw.split())
    name = raw[:raw.find('(')].strip()
    args = raw[raw.find('(')+1:raw.find(')')].strip().split(',')
    return i, name, args

def get_py_doc_string(lines, i):
    #return doc, doc_start, doc_end, fields, doc_params, issues
    #skip over white space
    while lines[i].strip()=='':
        i+=1
    #check for triple quotes
    if lines[i].strip() not in ["'''", '"""']: return '', i, i, [], [],[['No docstring found',i]]  #did not find
    doc_start = i
    fields = []
    params = []
    i+=1  #move beyond opening quotes
    issues = []
    numpy_fields = ['Parameters', 'Returns', 'Yields', 'Raises', 'See Also', 'Notes', 'Examples']
    while i<len(lines):
        if lines[i].strip() in ["'''", '"""']:
            doc_end = i
            break  #found end

        #check for field
        if lines[i].strip() in numpy_fields and i+1 < len(lines) and all([c=='-' for c in lines[i+1].strip()]):
            field = lines[i].strip()
            fields.append(field)
            i += 2  #skip over field and -------

            #check for Parameters field in particular
            if field == 'Parameters':
                while i<len(lines):

                    if lines[i].strip() in numpy_fields and i+1 < len(lines) and all([c=='-' for c in lines[i+1].strip()]):
                        break  #found next field

                    if lines[i].strip() in ["'''", '"""']:
                        break  #found end

                    if ':' in lines[i]:
                        param = lines[i].strip()[:lines[i].find(':')].replace(':','').strip()
                        params.append(param)
                        print(f': appending param {param}')
                        i += 1
                        continue

                    if lines[i].strip().isalnum() and lines[i].strip()[0].isalpha():
                        param = lines[i].strip()
                        print(f'naked appending param {param}')
                        params.append(param)
                        i += 1
                        continue

                    i += 1  #keep looking

                if i>=len(lines):
                    issues.append([f'Missing end to docstring', doc_start])
                    doc = lines[doc_start:]
                    return doc, doc_start, i-1, fields, params, issues
                else:
                    continue  #broke out
        i += 1

    #end outer while
    if i >= len(lines):
        #fell out of while
        issues.append([f'Missing end to docstring', doc_start])
        doc_end = i

    doc = lines[doc_start:doc_end+1]

    return doc, doc_start, doc_end, fields, params, issues

def check_py_numpy_param_match(sig_args, doc_args, doc_start):
    issue = []
    #check if 2 lists match up
    residue1 = [x for x in doc_args if x not in sig_args]  #more params than arg names?
    residue2 = [x for x in sig_args if x not in doc_args]  #more args than param names?
    print((sig_args, doc_args, residue1, residue2))
    if residue1:
        issue.append([f'doc arguments missing actual arguments: {residue1}', doc_start])
    if residue2:
        issue.append([f'actual arguments missing doc arguments: {residue2}', doc_start])
    return issue


def check_py_numpy_mandatory(mandatories, fields, doc_start):
    issues = []
    #check if 2 lists match up
    residue1 = set(mandatories)  - set(fields)
    if residue1:
        issues.append([f'mandatory fields missing: {residue1}', doc_start])

    return issues

def get_f90_robodoc_string_plus_sig(lines, i):
    assert lines[i].startswith('!!****if*')  or lines[i].startswith('!!****f*')#assumes lines[i] is beginning of docstring

    #parameters
    #   lines: list of lines (strings) to search
    #   i: index in lines to start search

    #Assumes
    #   assumes lines[i] is start of robodoc string in Fortran

    #returns
    #   i: index of last line of signature
    #   doc: list of lines of docstring preceding signature (maybe empty)
    #   sig: signature as string with no \n or &, e.g., 'foo(a,b,c)'
    #   issue: list of strings that describe issues found while parsing

    j = i
    i+=1  #move past header
    #found header now look for ending
    while not lines[i].startswith('!!**') and lines[i].startswith('!!'):
        i+=1  #move to next
        if i>=len(lines):
            return i-1, lines[j:i-1], '', [(f'No end found for docstring', j)]
    #found non comment line - assume ending
    i+=1  #move past ending
    doc = lines[j:i]

    #now look for subroutine
    while not lines[i].startswith('subroutine '):
        i += 1
        if i >= len(lines):
            return i-1, doc, '', [(f'No subroutine found for docstring', j)]
    j = i
    while lines[i].find(')') == -1:
        i += 1
        if i >= len(lines):
            return i-1, doc, ' '.join(lines[j:j+1]).strip('\n').replace('&', ' ')[10:], [(f'No closing ) for subroutine', j)]

    #looks good!
    raw_sig = ' '.join(lines[j:i+1]).strip('\n').replace('&', ' ')[10:]
    return i, doc, raw_string[:, raw_string.find(')')], []

'''
!> A generic assertion, tests a given logical expression. (The short, concise description)

!> If it evaluates to .false.,
!> print the fail message and possibly stop execution. (A more detailed description)
!> 
!> @param test The logical expression to test. (Explanation of individual arguments)
!> @param failmsg The message to print on fail. If omitted, a generic message is printed.
!> Can be modified with a prefix (see assertSetMsgPrefix)
!> @param doStop Controls whether to stop execution. If doStop .true., 
!> the program is stopped. If .false., only the fail message is printed
!> and bookkeeping is done for delayed stopping (see assertStopOnFailed).
!> If given, overrides the default behaviour  set by assertSetStopMode.

!> @see assertStopOnFailed (References to other routines)
!> @see assertSetStopMode
!> @see assertSetMsgPrefix

!> @author H.-J. Klingshirn (Author information)
!> @version 1.0 (Version information)
'''

def check_param_match(signature, params) -> str:
    assert isinstance(signature, str)
    assert isinstance(doc_lines, list)

    '''
    !! ARGUMENTS
    !!  blkcnt - number of blocks
    !!  blklst : block list
    !!  nstep - current cycle number
    !!  dt,ds - current time step length (2 args)
    !!  stime - current simulation time
    '''

    #first find the ARGUMENTS section
    j = 0
    while j<len(doc_lines):
        k = doc_lines[j].find('ARGUMENTS')
        if k != -1: break  #found it
        j+=1  #keep looking
    else:
        #Get here if while condition is false
        return [('ARGUMENTS heading not found in docstring', doc_start)]
    arg_start = j
    #found ARGUMENTS section - now get arguments
    all_headers = ['NAME','SYNOPSIS','DESCRIPTION','RESULT','EXAMPLE','SIDE EFFECTS', 'NOTES','SEE ALSO']
    param_names = []
    param_types = []
    j += 1  #move beyond ARGUMENTS line
    while j<len(doc_lines):

        #check if ends by a non-comment line
        if not doc_lines[j].startswith('!!'):
            break

        #check if get to new section (so end of ARGUMENTS)
        line = doc_lines[j][2:].strip()  #remove !! and padding
        if line in all_headers:
            break

        #check if - or : in line. If so, argument name is defined
        hyphen = line.find(' - ')
        index = line.find(' : ') if hyphen == -1 else hyphen  #try colon if do not find hyphen 

        #if not found, keep moving along
        if index == -1:
            j += 1
            continue  #looking for - to signal arg name

        #record arg name(s) found
        arg_name = line[:index].strip()
        for aname in arg_name.split(','):  #can have more than one name preceding hyphen
            param_names.append(aname)
        j += 1

    #have param_names - now get actual params from sig
    i = signature.find('(')
    j = signature.find(')')
    assert i != -1 and j != -1

    #build list of actual params
    arg_names = [arg.strip() for arg in signature[i+1:j].split(',')]

    #check if 2 lists match up
    issues = []
    for p,a in zip(param_names,arg_names):
        if p==a: continue
        issues.append((f'mismatch. ARGUMENTS: {(p,a)}', doc_start+arg_start))
    return issues


def write_pr_info_to_file(proj_id):
    return []






