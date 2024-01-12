import datetime
import json
import requests
import os
import importlib
import configparser
import sys

from django.http import HttpResponse
from django.template import loader
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

import pandas as pd
import math
import re

import openai

sys.path.insert(1, "/shared/soft/ideas-uo/src")
sys.path.insert(1, "../src")
from gitutils.github_api import GitHubAPIClient

from database.models import (
    PRAFeedback,
    SupportSubmission,
    Project,
    ProjectRole,
    Commit,
    Diff,
    Issue,
    PullRequest,
    Profile,
    PullRequestIssue,
    Comment,
    EventPayload,
    CommitTag,
    PullRequestLabel,
    Label,
    EventLog,
    FileMetric,
)
from database.utilities import comment_pullrequest, get_repo_owner
from dashboard.forms import SupportSubmissionForm
from dashboard.utilities import (
    list_project_files,
    python_doxygen_template,
    fortran_doxygen_template,
    gmail_send_message,
    save_debug_event,
    dox_script,
)
from dashboard.author_merger_tool import AuthorMergerTool
from dashboard.lib import default as default_docchecker
from dashboard.cqlib import default as default_linter

import subprocess
import os, warnings

warnings.filterwarnings("ignore")
from patterns.visualizer import Visualizer


def not_authorized(request):
    return render(request, "dashboard/not_authorized.html")


# Index view - should list all projects
@login_required
def index(request):

    if request.user.is_staff:
        return redirect("staff_index")

    devProjects = Project.objects.filter(
        project_role__user=request.user, project_role__role="DEV"
    )
    devProjects = sorted(devProjects, key=lambda d: d.name, reverse=False)

    PMProjects = Project.objects.filter(
        project_role__user=request.user, project_role__role="PM"
    )
    PMProjects = sorted(PMProjects, key=lambda d: d.name, reverse=False)

    context = {"devProjects": devProjects, "PMProjects": PMProjects}

    return render(request, "dashboard/index.html", context)


@login_required
def recommender_feedback(request):
    if request.method == "POST":
        try:
            feedback = PRAFeedback(
                thumbs = request.POST.get("thumbs") == "thumb-up",
                message = request.POST.get("message"),
                user = request.user,
                filepath = request.POST.get("filepath"),
                type = request.POST.get("type"),
                pullrequest = PullRequest.objects.get(id=request.POST.get("prid"))
            )
            feedback.save()

            return HttpResponse(json.dumps({"success": "true"}), content_type="application/json")
        except Exception as e:
            return HttpResponse(json.dumps({"success": "false", "message": str(e)}), content_type="application/json")


@login_required
def support(request):

    if request.method == "POST":
        incompleteForm = SupportSubmissionForm(request.POST, request.FILES)
        if incompleteForm.is_valid():
            # Complete form data and save
            form = incompleteForm.save(commit=False)
            form.user = request.user
            form.datetime = datetime.datetime.today()
            form.save()

            # Send email message
            # Get human-readable form for supportType and feature
            supportType = SupportSubmission.SupportTypeChoices(
                request.POST["supportType"]
            ).label
            feature = SupportSubmission.SiteFeatureChoices(
                request.POST["feature"]
            ).label
            body = f"Hello, Admin,\n\n{request.user.profile.gh_login} submitted a supoprt request via MeerCAT. Here is the submitted data:\n\n"
            body += f"Support type: {supportType}\n"
            body += f"Feature being used: {feature}\n"
            body += f'Description: {request.POST["description"]}\n'
            gmail_send_message(
                subject="Support request submitted",
                body=body,
                image=request.FILES.get("image", None),
            )

            messages.success(request, "Thank you, we received your feedback.")
            return redirect("support")
        else:
            messages.error(
                request,
                "Something failed. Please try again later or contact the MeerCAT team.",
            )
            save_debug_event(
                "Support form could not submit invalid data",
                json=incompleteForm.errors.as_json(),
                request=request,
            )

    form = SupportSubmissionForm()
    return render(request, "dashboard/support.html", {"form": form})


@login_required
def staff_index(request):

    projects = list(Project.objects.all())
    projects = sorted(projects, key=lambda d: d.name, reverse=False)

    return render(request, "dashboard/staff_index.html", {"projects": projects})


@login_required
def subscriptions(request):

    if request.method == "POST":
        request.user.profile.subscriptions = json.loads(
            request.POST["subscriptions"] or "{}"
        )
        print(request.user.profile.subscriptions)
        request.user.profile.save()
        messages.success(request, 'Your subscriptions were saved successfullly')

    projects = Project.objects.filter(project_role__user=request.user)

    if request.user.is_staff:
        projects = Project.objects.all()

    files = {}
    project_names = []
    for project in projects:
        project_names.append(project.name)
        try:
            files[project.name] = list_project_files(project.name)
        except:
            pass

    subscriptions = request.user.profile.subscriptions

    context = {
        "files": files,
        "project_names": project_names,
        "subscriptions": subscriptions,
    }

    return render(request, "dashboard/subscriptions.html", context)

@login_required
def recommender(request):

    proj_list = list(Project.objects.all().filter(id=int(request.GET.get('project','0'))).all())
    proj_object = proj_list[0]

    print('RECOMMENDER: '+request.GET.get('filename',''))
    url = "https://meercat.cs.uoregon.edu:8099/p/"+proj_object.name+'/'+request.GET.get('filename','')
    print('RECOMMENDER URL: '+url)
    result = requests.get(url)
    #print('RECOMMENDER RESULTS: '+json.dumps(result.json()))

    result_data = []
    if result.status_code == 200:
        result_data = result.json()

    return HttpResponse(json.dumps(result_data), content_type="application/json")

# localhost:8080/dashboard/firstresponder/30?prid=17479
def firstresponder(request, *args, **kwargs):

    # template = loader.get_template('dashboard/firstresponder.html')

    # Get PR id
    if kwargs["pk"]:
        proj_id = int(kwargs["pk"])
    else:
        return HttpResponse(
            json.dumps("Missing project"), content_type="application/json"
        )

    proj_list = list(Project.objects.all().filter(id=proj_id).all())
    if not proj_list:
        return HttpResponse(
            json.dumps(f"Unknown project {proj_id}"), content_type="application/json"
        )

    proj_object = proj_list[0]

    if request.GET.get("prid"):
        pr_id = request.GET.get("prid")
    else:
        return HttpResponse(
            json.dumps(f"Missing Pull Request number"), content_type="application/json"
        )

    pr_list = list(PullRequest.objects.all().filter(id=pr_id).all())
    if not pr_list:
        return HttpResponse(
            json.dumps(f"Illegal Pull Request number {pr_id}"),
            content_type="application/json",
        )

    pull_object = pr_list[0]

    message, all_contexts = first_responder_function(proj_object, pull_object)

    print(f'{message = }')
    print(f'all_contexts[0] = {all_contexts}')

    return HttpResponse(json.dumps([message,all_contexts]), content_type="application/json")


def first_responder_function(proj_object, pull_object):
    proj_name = proj_object.name  # get project name
    proj_id = proj_object.id

    # get set up on right feature branch
    commits_list = list(
        Commit.objects.all().filter(
            hash__in=[committag.sha for committag in pull_object.commits.all()]
        )
    )
    # assert commits_list, f"No commits found for {proj_id}"

    commit_messages = [c.message for c in commits_list]

    try:
        branch = commits_list[0].branch.split()[-1]
        cmd = f"cd {settings.REPOS_DIR}/{proj_name} ; git checkout --force {branch}"

        import os
        os.system(cmd)
    except:
        # assert False, f"Failure to checkout branch {cmd}"
        pass

    # get all files in PR
    diffs = list(Diff.objects.all().filter(commit__in=[c for c in commits_list]))
    filenames = [d.file_path for d in diffs]
    # Get just unique filenames
    filenames_set = set(filenames)
    filenames = list(filenames_set)

    all_contexts = {}

    for filename in filenames:
        print("CHECKING FILE: "+filename)
        # Need to see if file exists because it could have been renamed in another commit in same PR.
        if os.path.isfile(str(settings.REPOS_DIR) + "/" + proj_object.name + "/" + filename):
            context = file_explorer_handler(proj_object, filename, branch)
            all_contexts[filename] = context
    
    '''
    context = dict(supports_callgraph= False,  #none yet
                    supports_test_hunt= False, #none yet
                    file=filename,
                    branch= branch,
                    project= proj_object.name,
                    complete_ignore',
                    context['documentation'] = documentation_status
                    context['dev_table'] = dev_table
                    context['function_table'] = subroutine_table
                    context['number_of_functions'] = len(subroutine_table)
                    context['pull_requests'] = pr_links_table
                    context['linting_table'] = None
    '''

    '''
    documentation_status:
    'ignore_status'
    'check_status'
    'doc_status'
    'problem_lines'  [(msg, line)]
    '''

    #Find the files with documentation problems, i.e., that have the field 'problem_lines'
    doc_problems = 0
    doc_missing = 0
    checkable = 0
    no_library = False
    all_files = len(all_contexts.items())
    for filename,context in all_contexts.items():
        # documentation_status = context['documentation']  #a dictionary - see above
        # if 'problem_lines' in documentation_status:
        #     doc_problems.append([filename, documentation_status['problem_lines']]) 
        documentation_status = context['documentation_lib']  #a dictionary - see above
        if len(documentation_status['problem_fields']) > 0 or len(documentation_status['missing_fields']) > 0 or ('missing_file_fields' in documentation_status and len(documentation_status['missing_file_fields']) > 0) or  ('missing_subroutine_fields' in documentation_status and len(documentation_status['missing_subroutine_fields']) > 0):
            doc_problems += 1 
        elif 'no Doxygen' in documentation_status['file_status']:
            doc_missing += 1 
        elif 'No documentation checker library available' in documentation_status['file_status']:
            no_library = True

        if documentation_status['should_have_doc']:
            checkable += 1

    have = "have"
    if checkable-doc_missing == 1:
        have = "has"
    doc_message =  f"""## Out of {all_files} file{'s'[:all_files^1]} in this PR, {checkable} should have doxygen documentation.  {checkable-doc_missing} {have} doxygen documentation."""

    if checkable-doc_missing > 0:
        have = "have"
        if doc_problems == 1:
            have = "has"
        doc_message +=f"""
## Out of {checkable-doc_missing} file{'s'[:(checkable-doc_missing)^1]} with doxygen documentation, {doc_problems} file{'s'[:doc_problems^1]} {have} issues."""
    
    if no_library:
        doc_message =  f"""No documentation library available."""



    # Use metrics to compute average (and get live results for just the files in PR branch)
    '''linter_metrics = list(FileMetric.objects.all().filter(metric_type=FileMetric.MetricTypeChoices.LINTING, project=proj_object, branch='main'))
    numerator = 0
    denominator = 0
    average = 0
    for metric in linter_metrics:
        if metric.result_json:
            if len(metric.result_json) > 0:
                denominator += 1
                numerator += len(metric.result_json)
    if denominator > 0:
        average = (numerator/denominator)            
        print("AVERAGE PROBLEMS: "+ str(numerator/denominator))
    average = math.floor(average)'''

    linter_problems = 0;
    average = 0;
    for filename in filenames:
        #results = file_linter(proj_object, filename)
        results = default_linter.check_file(proj_object, settings, filename)
        average += len(results)
        if len(results) > 0:
            linter_problems += 1
    print("TOTAL PROBLEMS OVER AVERAGE: "+ str(linter_problems))
    if linter_problems > 0:
        average = round(average/linter_problems)  


    message = f"""## The MeerCat Pull-Request Assistant has information for you

{doc_message}

## Out of {all_files} file{'s'[:all_files^1]} in this PR, {linter_problems} file{'s'[:linter_problems^1]} {'has' if linter_problems == 1 else 'have'} code quality errors. The average is {average} error{'' if average == 1 else 's'}.

[Please see the Pull-Request Assistant page for more detail.](https://meercat.cs.uoregon.edu/dashboard/pr/{pull_object.id}) (right-click to open in new tab)
    """

    # pr_file_intersection = comute_pr_file_intersection(proj_object, filenames)
    # return [message, all_files, pr_file_intersection]
    return [message, all_contexts]

def file_explorer_handler(proj_object, filename, branch ):
    print(f'entering file_explorer_handler with {filename =}')
    ignore_extensions  = proj_object.documentation_ignore_extensions
    ignore_filenames =  proj_object.documentation_ignore_filenames


    context = dict(supports_callgraph= False,  #none yet
                    supports_test_hunt= False, #none yet
                    file=filename,
                    branch= branch,
                    project= dict(id=proj_object.name, name=proj_object.name),

        )

    name, extension = os.path.splitext(filename)
    #check ignorelist of allowable extensions. If no extension, check for allowed filenames.
    #If can't find, then assume file should not be checked for documentation.
    if (extension and (extension in ignore_extensions)) or \
       (not extension and (filename in ignore_filenames)):
        context['complete_ignore'] = True
        return context

    try:
        with open(
            str(settings.REPOS_DIR) + "/" + proj_object.name + "/" + filename, "r") as f:
            lines = f.readlines()
            f.close()
    except:
        lines = []        


    # THIS IS WHERE WE CALL THE FLASHX LIBRARY TODO: NEED TO ONLY CALL IT IF FLASHX OR ANL_TEST_REPO THOUGH
    # TODO: Replace with something like: modules = map(__import__, ['sys, 'os'])
    # Or my_module = importlib.import_module('os.path')
    # Or mod_name,file_ext = os.path.splitext(os.path.split(filepath)[-1])
    #    my_module = imp.load_source(mod_name, filepath)

    if proj_object.documentation_library and len(proj_object.documentation_library) > 0:
        docchecker = importlib.import_module('dashboard.lib.'+proj_object.documentation_library)
        docchecker.set_directory_structure(repo_structure(str(settings.REPOS_DIR) + "/" + proj_object.name))
        documentation_status_lib = docchecker.check_file_documentation(lines, filename)
        #elif proj_object.id == 35 or proj_object.id == 26 and proj_object.id == 30 and:
        #flashx.set_directory_structure(repo_structure(str(settings.REPOS_DIR) + "/" + proj_object.name))
        #documentation_status_lib = flashx.check_file_documentation(lines, filename)
    else:    
        default_docchecker.set_directory_structure(repo_structure(str(settings.REPOS_DIR) + "/" + proj_object.name))
        documentation_status_lib = default_docchecker.check_file_documentation(lines, filename)

    #TODO: Remove this! This is the old checker.  Keep it for non-flashx projects for now.
    documentation_status = check_documentation(proj_object, filename, lines)

    dev_table = create_dev_table(proj_object, filename)

    subroutine_table = create_subroutine_table(proj_object, filename, lines)

    pr_links_table = create_pr_links_table(proj_object, filename)

    # linting is done elsewhere and stored in linter_results
    # linting_table = create_linting_table(proj_object, lines)

    context['documentation'] = documentation_status
    context['documentation_lib'] = documentation_status_lib
    context['dev_table'] = dev_table
    context['function_table'] = subroutine_table
    context['number_of_functions'] = len(subroutine_table)
    context['pull_requests'] = pr_links_table
    context['linting_table'] = None

    return context

#dict(ignore_status, check_status doc_status, problem_lines [(msg, line), (msg, line)] )
def check_documentation(proj_object, filename, lines):
    name, extension = os.path.splitext(filename)

    doctypes = proj_object.doctypes

    return_dict = dict()

    return_dict['ignore_status'] = False   #probably should remove this field. Assuming False to even call this function.

    #go through combinations of language-doctype

    if not doctypes or extension not in doctypes:
        return_dict['check_status'] = False
        return return_dict

    def check_flashx_documentation(filename, lines):
        placeholders = ['<missing details>', '<missing param info>']  #need to get from Jared
        problem_lines = []
        if lines[0].strip().startswith('!!*'):
            problem_lines.append(('File still in Robodoc format. See project documentation for converting to Doxygen', 1))
            return problem_lines

        found_copyright = False
        for line in lines:
            if '@copyright' in line:
                found_copyright = True
                break

        if not found_copyright:        
            if len(lines[0].strip()) > 0:
                problem_lines.append(('File missing @copyright', 1))
            else:    
                problem_lines.append(('File missing @copyright', 2))
            return problem_lines

        for i,line in enumerate(lines):
            for placeholder in placeholders:
                if placeholder in line:
                    problem_lines.append(('Placeholder needs to be filled in.', (i+1)))
                    break

        for i,line in enumerate(lines):
            if '<Insert ' in line or '<insert ' in line:
                problem_lines.append(('Please fill in tag.', (i+1)))

        for i,line in enumerate(lines):
            if '__AUTO_INSERT_' in line:
                problem_lines.append(('Should have been handled by Doxygen script.', (i+1)))

        return problem_lines

    #handle flash-x specially
    if extension == '.F90' and doctypes[extension] == 'flash-x':
        return_dict['check_status'] = True
        problem_lines = check_flashx_documentation(filename, lines)
        return_dict['doc_status'] = True
        if problem_lines:
            return_dict['doc_status'] = False
            return_dict['problem_lines'] = problem_lines
        return return_dict

    #Generic check for doxygen
    if extension == '.F90' and doctypes[extension] == 'doxygen':
        return_dict['check_status'] = True
        for line in lines:
            if line.startswith('!! @'):
                return_dict['doc_status'] = True
                break
        if not return_dict['doc_status']:
            return_dict['doc_status'] = False
            return_dict['problem_lines'] = [("Please see project documentation for converting to Doxygen", 0)]
        return return_dict
    
    #find index of first line after signature
    def parse_python_def(k):
        while k<len(lines):
            if ')' in lines[k]:  #simply look for closing paren
                return k+1
            k += 1
        return k

    #Make sure every signature is followed by ''' comments.
    #Not currently checking for type, e.g., numpy, google. Just docstring.

    if extension == '.py' and doctypes[extension] == 'docstring':
        return_dict['check_status'] = True
        problem_lines = []
        i = 0
        while i<len(lines):
            if lines[i].startswith('def'):
                j = parse_python_def(i)  # j is line after signature

                #skip over white space
                while lines[j].strip() == "":
                    j += 1
                    if j>=len(lines):
                        break

                # check for triple quotes
                if j<len(lines) and lines[j].strip() in ["'''", '"""']:
                    i = j+1
                    continue
                else:
                    problem_lines.append(("Missing docstring", j))
                    i += 1
            else:
                i += 1
        if problem_lines:
            return_dict['doc_status'] = False
            return_dict['problem_lines'] = problem_lines
        else:
            return_dict['doc_status'] = True
        return return_dict 

    #others go here eventually,, e.g., c-doxygen, etc.

    #Special case for Hypre
    if extension == '.h' and doctypes[extension] == 'hypre':
        if not name.startswith('HYPRE_'):
            return_dict['check_status'] = False
            return return_dict
        problem_lines = []
        i = 0
        while i<len(lines):
            if lines[i].strip().endswith(';'):
                interface = i
                j = i - 1

                #look backward for end of comment
                while lines[j].strip() == "" or lines[j].strip().endswith(','):  #handle multi-line defs
                    j -= 1
                    if j<0:
                        break

                # check for triple quotes
                if j>=0 and lines[j].strip().endswith('**/'):
                    i = interface + 1
                    continue
                else:
                    problem_lines.append(("Missing Doxygen header", interface))
                    i = interface + 1
            else:
                i += 1

        if problem_lines:
            return_dict['doc_status'] = False
            return_dict['problem_lines'] = problem_lines
        else:
            return_dict['doc_status'] = True
        return return_dict

    #if not currently checking combo
    return_dict['check_status'] = False
    return return_dict

def create_dev_table(proj_object, filename):
    # Build developer table

    diffs = (
        Diff.objects.all()
        .filter(commit__project=proj_object, file_path=filename)
        .all()
    )

    #compute lines of code for each author
    author_loc = {}
    for d in diffs:
        body = d.body
        author = d.commit.author
        loc_count = body.count("\n+") + body.count("\n-")
        if author in author_loc:
            author_loc[author] += loc_count
        else:
            author_loc[author] = loc_count

    # Get commits, authors for those (diffs)

    info = [(d.commit.datetime, d.commit.author, d.commit.hash) for d in diffs]
    commit_messages = [d.commit.message for d in diffs]
    commit_hashes = [d.commit.hash for d in diffs]

    tags = CommitTag.objects.all().filter(sha__in=commit_hashes)  #used later for prs

    #how many commits per author
    author_count = {}
    for date, author, link in info:
        if author in author_count:
            author_count[author] += 1
        else:
            author_count[author] = 1

    new_info = []
    authors = []
    for date, author, link in sorted(info, reverse=False):
        if author in authors:
            continue
        new_info.append((date, author, author_count[author], author_loc[author], link))
        authors.append(author)

    # see here for avoiding author alisases: https://towardsdatascience.com/string-matching-with-fuzzywuzzy-e982c61f8a84
    # combine counts for same author with different aliases.

    dev_table = [
        {
            "author": author.username+' - '+author.email,
            "number_commits": count,
            "lines": loc,
            "most_recent_commit": date.strftime("%Y-%m-%d, %H:%M %p"),
            "commit_link": link,
        }
        for date, author, count, loc, link in new_info
    ]

    return dev_table

def create_pr_links_table(proj_object, filename):

    diffs = (
        Diff.objects.all()
        .filter(commit__project=proj_object, file_path=filename)
        .all()
    )

    commit_hashes = [d.commit.hash for d in diffs]

    tags = CommitTag.objects.all().filter(sha__in=commit_hashes)

    prs = list(
        set(PullRequest.objects.all().filter(commits__in=tags))
    )  # all prs that go with file commits

    return [(pr.number, pr.url, pr.title, pr.id) for pr in prs]


def create_subroutine_table(proj_object, filename, lines):

    name, extension = os.path.splitext(filename)

    functions = []

    #F90
    if extension == '.F90':
        for line in lines:
            if line.startswith('subroutine'):
                functions.append(line)
        return functions
    
    #Python
    if extension == '.py':
        for line in lines:
            if line.startswith('def'):
                functions.append(line)
        return functions

    #others go here eventually,, e.g., c, etc.
    if extension == '.h' or extension == '.H':
        #will be looking for function interfaces only - ends with ;
        i = 0
        while i<len(lines):
            if lines[i].strip().endswith(';'):
                #search backwards for start
                end = i
                j = i - 1
                while j>= 0 and lines[j].strip() != '':  #assumes blank line preceding definition
                    j -= 1
                start = j+1
                if 'struct ' not in lines[start]:  #make sure do not capture structs
                    functions.append(lines[start])
                i = end + 1
            else:
                i += 1
        return functions

    if extension == '.c':
        #will be looking for functions only - not structs
        i = 0
        while i<len(lines):
            if '{' in lines[i]:
                #search backwards for start
                end = i
                j = i
                while j>= 0 and '(' not in lines[j] and 'struct ' not in lines[j]:
                    j -= 1
                if j<0: assert False, f'Did not find start of function or structure in {lines[:end]}'
                if 'struct ' in lines[j]:
                    i = end + 1
                    continue  #hope this continues while loop

                #found beginning of function def
                functions.append(lines[j])
                i = end + 1
            else:
                i += 1
        return functions

    #if not currently checking extension
    return []

def file_linter(proj_object, filename):

    results = []

    if filename.endswith(".py"):
        rawresults = []
        try:
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
                    if 'Replace .' not in result and 'At least one space before comment' not in result and 'Exactly one space after' not in result and 'Missing space' not in result and 'Single space' not in result and 'Trailing whitespace' not in result and 'Line length' not in result:
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

# Project view - should list general project info
def project(request, *args, **kwargs):
    print("PROJECT")
    print(kwargs["pk"])

    pid = 30
    if kwargs["pk"]:
        pid = int(kwargs["pk"])

    if not hasAccessToProject(request.user, pid):
        return redirect("not_authorized")

    template = loader.get_template("dashboard/project.html")

    project = list(Project.objects.all().filter(id=pid).all())[0]

    # chose wether to display whitelist button if user is staff
    show_whitelist = True
    if request.user.is_staff:
        has_project_role = ProjectRole.objects.filter(
            project=project, user=request.user
        ).exists()
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

    pythonloc = countlinespython(str(settings.REPOS_DIR) + "/" + project.name)
    print(".")
    fortranloc = countlinesfortran(str(settings.REPOS_DIR) + "/" + project.name)
    print("..")
    cloc = countlinesc(str(settings.REPOS_DIR) + "/" + project.name)
    print("...")
    files = countfiles(str(settings.REPOS_DIR) + "/" + project.name)
    print("....")

    # TODO: should be able to remove this
    """with open(settings.REPOS_DIR+'anl_test_repo/folder1/arithmetic.py', 'r') as f:
        lines = f.readlines()
        f.close()
    """

    context = {
        "show_whitelist": show_whitelist,
        "project": project,
        "prs": prs,
        "commits": commits,
        "issues": issues,
        "pythonloc": pythonloc,
        "fortranloc": fortranloc,
        "cloc": cloc,
        "files": files,
    }
    #'file':''.join(lines).replace('\\','\\\\').replace('\n', '\\n').replace('\'','\\\'')

    return HttpResponse(template.render(context, request))


# PR list view - list all the PRs for project
@login_required
def prlist(request, *args, **kwargs):
    print("PRLIST")
    template = loader.get_template("dashboard/prlist.html")

    pid = 30
    # if request.GET.get('pid'):
    #    pid = int(request.GET.get('pid'))
    if kwargs["pk"]:
        pid = int(kwargs["pk"])

    if not hasAccessToProject(request.user, pid):
        return redirect("not_authorized")

    project = list(Project.objects.all().filter(id=pid).all())[0]

    prs = list(PullRequest.objects.all().filter(project=project).all())
    prs = sorted(prs, key=lambda d: d.number, reverse=True)

    context = {"project": project, "prs": prs}

    return HttpResponse(template.render(context, request))


# Pull Request view - show the assistant for specific PR
@login_required
def pr(request, *args, **kwargs):
    print("PR")
    template = loader.get_template("dashboard/pr.html")

    prid = 2250
    # if request.GET.get('pr'):
    #    prid = int(request.GET.get('pr'))
    if kwargs["pk"]:
        prid = int(kwargs["pk"])

    if not hasAccessToPR(request.user, prid):
        return redirect("not_authorized")

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    commits = list(
        Commit.objects.all().filter(
            hash__in=[committag.sha for committag in set(pr.commits.all())]
        )
    )

    issues = list(
        Issue.objects.all().filter(
            url__in=[
                pri.issue.url
                for pri in PullRequestIssue.objects.all().filter(pr=pr).all()
            ]
        )
    )

    labels = pr.labels.all()

    # TODO: If commits are empty, try to download commits
    if len(commits) <= 0:
        for committag in pr.commits.all():
            print(committag.sha)

    # Find any issue that this PR closed
    closed_issue = None
    issue_numbers = re.findall(r"#\d+", pr.description)
    for issue_number in issue_numbers:
        print(issue_number)
        print(
            pr.project.source_url.replace(".git", "/issues/" + issue_number[1:])
        )
        closed_issue_list = list(
            Issue.objects.all().filter(
                url=pr.project.source_url.replace(
                    ".git", "/issues/" + issue_number[1:]
                )
            )
        )
        if len(closed_issue_list) > 0:
            closed_issue = closed_issue_list[0] #TODO: get rid of this 
            issues = issues + closed_issue_list

    # issues = list(Issue.objects.all().filter(project=list(Project.objects.all().filter(name='FLASH5').all())[0], state='closed'))
    # for issue in issues:
    #    comments = list(Comment.objects.all().filter(issue=issue))

    diffs = list(Diff.objects.all().filter(commit__in=[c for c in commits]))
    filenames = [d.file_path for d in diffs]
    # get just unique filenames
    filenames_set = set(filenames)
    filenames = list(filenames_set)

    events = list(EventPayload.objects.all().filter(pr_number=pr.number))

    comments = list(Comment.objects.all().filter(pr=pr))

    # switch local repo to the branch for this PR
    branch = "Unable to analyze any files in this branch"
    if len(commits) > 0:
        branch = commits[0].branch.split()[-1]
        print("PRA Switch branches to: " + branch)
        proj_name = pr.project.name
        cmd = f"cd {settings.REPOS_DIR}/{proj_name} ; git checkout --force {branch}"
        print(cmd)
        try:
            os.system(cmd)
            #result = subprocess.check_output(cmd, shell=True)
            #print(result)
        except Exception as e:
            return [e, [f"Failure to checkout branch {cmd}"]]

    context = {
        "pr": pr,
        "prid": prid,
        "branch": branch,
        "commits": commits,
        "issues": issues,
        "filenames": filenames,
        "events": events,
        "comments": comments,
        "closed_issue": closed_issue,
        "labels": labels,
    }

    return HttpResponse(template.render(context, request))


def save_subscriptions(request):
    
    if request.method == "POST":
        try:
            profile = Profile.objects.get(user=request.user)
            profile.subscriptions = json.loads(request.POST.get("subscriptions"))
            profile.save()

            return HttpResponse(json.dumps({"success": "true"}), content_type="application/json")
        except Exception as e:
            return HttpResponse(json.dumps({"success": "false", "message": str(e)}), content_type="application/json")


# For logging generic events
def logEvent(request, *args, **kwargs):

    # Get PR id
    prid = 0
    if request.POST.get("pr"):
        prid = int(request.POST.get("pr"))

    #if not hasAccessToPR(request.user, prid):
    #    return redirect("not_authorized")

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    comments = request.POST.get("comments")

    event = EventLog(
        event_type=EventLog.EventTypeChoices.FEATURE,
        log=comments,
        pull_request=pr,
        datetime=datetime.datetime.today(),
    )
    event.save()

    resultdata = {"status": "success"}
    return HttpResponse(json.dumps(resultdata), content_type="application/json")

#*********  DELETE THIS?
# Pull Request view - show the assistant for specific PR
def archeology(request, *args, **kwargs):

    template = loader.get_template("dashboard/archeology.html")

    # Get PR id
    prid = 0
    if kwargs["pk"]:
        prid = int(kwargs["pk"])

    if not hasAccessToPR(request.user, prid):
        return redirect("not_authorized")

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    # Get filename
    filename = ""
    if request.GET.get("filename"):
        filename = request.GET.get("filename")

    # Get diffs for file
    diffs = (
        Diff.objects.all().filter(commit__project=pr.project, file_path=filename).all()
    )

    # Get commits, authors for those (diffs)
    authors = set([d.commit.author for d in diffs])

    table = [
        {"author": author, "type": "commit", "link": "more info"} for author in authors
    ]

    context = {"pr": pr, "filename": filename, "authors": table}

    return HttpResponse(template.render(context, request))


# Refresh the GIT and GitHub data for a project
@login_required
def refreshProject(request):
    print("REFRESH")

    pid = 30
    if request.GET.get("pid"):
        pid = int(request.GET.get("pid"))

    if not hasAccessToProject(request.user, pid):
        return redirect("not_authorized")

    project = list(Project.objects.all().filter(id=pid).all())[0]

    username = settings.DATABASES["default"]["USER"]
    password = settings.DATABASES["default"]["PASSWORD"]

    try:
        # cmd = f'cd /shared/soft/ideas_db/ideas-uo/meercat/.. ; export PYTHONPATH=. ; nohup python3 ./src/gitutils/update_database.py {username} {password} {pid}'
        cmd = f"cd {settings.REPOS_DIR} ; . meercat/meercat-env/bin/activate ; export PYTHONPATH=. ; nohup python3 ./src/gitutils/update_database.py {username} {password} {pid}"
        # os.system(cmd)
        result = subprocess.check_output(cmd, shell=True)
        # print(result)

        resultdata = {"status": "success"}
    except Exception as e:
        resultdata = {"status": str(e)}

    return HttpResponse(json.dumps(resultdata), content_type="application/json")


# Refresh the GIT and GitHub data for a project
@login_required
def createPatch(request):
    print("CREATE PATCH")

    prid = 2250
    if request.POST.get("pr"):
        prid = int(request.POST.get("pr"))

    if not hasAccessToPR(request.user, prid):
        return redirect("not_authorized")

    filename = "folder1/arithmetic.py"
    if request.POST.get("filename"):
        filename = request.POST.get("filename")

    print(filename)
    print(filename.rindex("/"))
    print(filename[filename.rindex("/") + 1 :])

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    # project = list(Project.objects.all().filter(id=pid).all())[0]

    # with open('../ideas-uo/anl_test_repo/folder1/arithmetic.py', 'w') as f:
    with open(
        str(settings.REPOS_DIR) + "/" + pr.project.name + "/" + filename, "w"
    ) as f:
        f.write(request.POST.get("filecontents"))
        f.close()

    # cmd = f'cd ../ideas-uo/anl_test_repo ; git diff folder1/arithmetic.py > arithmetic.py.patch'
    cmd = (
        f"cd "
        + str(settings.REPOS_DIR)
        + "/"
        + pr.project.name
        + " ; git diff "
        + filename
        + " > "
        + filename[filename.rindex("/") + 1 :]
        + ".patch"
    )
    os.system(cmd)
    # result = subprocess.check_output(cmd, shell=True)

    # with open('../ideas-uo/anl_test_repo/arithmetic.py.patch', 'r') as f:
    with open(
        str(settings.REPOS_DIR)
        + "/"
        + pr.project.name
        + "/"
        + filename[filename.rindex("/") + 1 :]
        + ".patch",
        "r",
    ) as f:
        lines = f.readlines()
        f.close()
    os.remove(
        str(settings.REPOS_DIR)
        + "/"
        + pr.project.name
        + "/"
        + filename[filename.rindex("/") + 1 :]
        + ".patch"
    )

    # cmd = f'cd ../ideas-uo/anl_test_repo ; git checkout -- folder1/arithmetic.py'
    cmd = (
        f"cd "
        + str(settings.REPOS_DIR)
        + "/"
        + pr.project.name
        + " ; git checkout -- "
        + filename
    )
    os.system(cmd)

    resultdata = {
        "status": "success",
        "filename": filename[filename.rindex("/") + 1 :] + ".patch",
        "patch": "".join(lines),
    }

    return HttpResponse(json.dumps(resultdata), content_type="application/json")


# Retrieves commit data for a specific PR
@login_required
def diffCommitData(request):
    print("Diff Commit DATA")

    print(request.POST.get("pr"))

    prid = 2250
    if request.POST.get("pr"):
        prid = int(request.POST.get("pr"))

    if not hasAccessToPR(request.user, prid):
        return redirect("not_authorized")

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    # Find all changed files related to the PR by getting all diffs from all commits in PR
    commits = list(
        Commit.objects.all().filter(
            hash__in=[committag.sha for committag in set(pr.commits.all())]
        )
    )

    print("Commits: " + str(len(commits)))

    diffs = list(Diff.objects.all().filter(commit__in=[c for c in commits]))
    filenames = [d.file_path for d in diffs]
    # Get just unique filenames
    filenames_set = set(filenames)
    filenames = list(filenames_set)

    # Now find all commits and diffs for the changed files in the past 60 days
    # date = datetime.datetime.now() - datetime.timedelta(days=60)
    date = pr.created_at - datetime.timedelta(days=60)
    enddate = pr.created_at + datetime.timedelta(days=1)
    diffcommits = []

    print(pr.created_at)
    print(date)

    filtereddiffs = Diff.objects.all().filter(
        commit__project=pr.project,
        commit__datetime__gte=date,
        commit__datetime__lte=enddate,
    )
    for filename in filenames:
        if os.path.isfile(str(settings.REPOS_DIR) + "/" + pr.project.name + "/" + filename):
            diffcommits.append(
                {
                    "filename": filename,
                    "commits": [
                        {"commit": d.commit.hash, "diff": d.body}
                        for d in filtereddiffs.filter(file_path=filename)
                    ],
                }
            )

    prcommits = []
    for commit in commits:
        prcommits.append({"hash": commit.hash})

    message, docstring_results = first_responder_function(pr.project, pr)


    linter_results = []
    for filename in filenames:
        #results = file_linter(pr.project, filename)
        results = default_linter.check_file(pr.project, settings, filename)
        linter_results.append({"filename": filename, "results": results})


    # Build developer table
    author_loc = {}
    author_filenames = {}
    diffs = (
        Diff.objects.all()
        .filter(commit__project=pr.project, file_path__in=filenames)
        .all()
    )

    for d in diffs:
        body = d.body
        author = d.commit.author
        loc_count = body.count("\n+") + body.count("\n-")
        if author in author_loc:
            author_loc[author] += loc_count
            author_filenames[author].append(d.file_path)
        else:
            author_loc[author] = loc_count
            author_filenames[author] = [d.file_path]

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
        if author in authors:
            continue
        new_info.append((date, author, author_count[author], author_loc[author], link))
        authors.append(author)

    # see here for avoiding author alisases: https://towardsdatascience.com/string-matching-with-fuzzywuzzy-e982c61f8a84
    # combine counts for same author with different aliases.
    dev_table = [
        {
            "author": author.username + " - " + author.email,
            "number_commits": count,
            "filenames": author_filenames[author],
            "lines": loc,
            "most_recent_commit": date.strftime("%Y-%m-%d, %H:%M %p"),
            "commit_link": link,
        }
        for date, author, count, loc, link in new_info
    ]

    # merge authors
    comments = list(Comment.objects.all().filter(pr=pr))  # use this for excluding
    combined_authors = AuthorMergerTool._get_unique_authors(
        [author.username for date, author, count, loc, link in new_info]
    )
    # print("----------------------------")
    # print(combined_authors)
    # print("----------------------------")
    all_authors = combined_authors["author"].to_list()
    combined_authors = combined_authors["unique_author"].to_list()
    merged_dev_table = []
    merged_emails = []
    for date, author, count, loc, link in new_info:
        for idx, the_author in enumerate(all_authors):
            # Don't add PR author to the list
            # And don't add people who have already commented
            if (
                author.username != pr.author.username
                and author.username == the_author
                and the_author == combined_authors[idx]
                and [author["username"] for author in merged_dev_table].count(
                    the_author
                )
                < 1
            ):
                foundauthor = False
                for comment in comments:
                    if comment.author.username == author.username:
                        foundauthro = True
                if not foundauthor:
                    merged_emails.append(author.email)
                    merged_dev_table.append(
                        {
                            "username": author.username,
                            "author": author.username + " - " + author.email,
                            "filenames": [],
                            "number_commits": 0,
                            "lines": 0,
                            "most_recent_commit": date.strftime("%Y-%m-%d, %H:%M %p"),
                            "commit_link": link,
                        }
                    )

    # print("----------------------------")
    # print(merged_dev_table)
    # print([author['username'] for author in merged_dev_table])
    # print([author['username'] for author in merged_dev_table].count('Ruipeng Li'))

    for date, author, count, loc, link in new_info:
        for idx, the_author in enumerate(all_authors):
            if (
                author.username == the_author
            ):  # and the_author != combined_authors[idx]:
                for i in range(0, len(merged_dev_table)):
                    if merged_dev_table[i]["username"] == combined_authors[idx]:
                        merged_dev_table[i]["number_commits"] += count
                        merged_dev_table[i]["lines"] += loc
                        merged_dev_table[i]["filenames"].extend(
                            author_filenames[author]
                        )
                        if merged_dev_table[i]["most_recent_commit"] < date.strftime(
                            "%Y-%m-%d, %H:%M %p"
                        ):
                            merged_dev_table[i]["most_recent_commit"] = date.strftime(
                                "%Y-%m-%d, %H:%M %p"
                            )
                            merged_dev_table[i]["commit_link"] = link

    merged_dev_table = sorted(
        merged_dev_table, key=lambda d: d["most_recent_commit"], reverse=True
    )

    extra_devs = []
    roles = (
        ProjectRole.objects.all()
        .filter(project=pr.project)
        .all()
    )
    for role in roles:
        if role.user.email and role.user.email not in merged_emails:
            extra_devs.append(role.user.email)



    # Setup ChatGPT
    '''with open(settings.BASE_DIR / "meercat.config.json") as meercat_config:
        config = json.load(meercat_config)
    openai.api_key = config["OPEN_API_KEY"]

    completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role":"user", "content":"Please provide a critique-focused review of my Fortran 90 code. Ignore #include and @todo directives. Assume calls on ml_error have no problems. Ignore hard-coded indices. When checking argument typing, pay attention to use statements and derived types. Do not include a summary of the code, only problems with the code that you see."}])
    '''

    # Only call ChatGPT on F90 files for now (only calling on one file for initial testing)
    llm = [];
    '''for filename in filenames:
        if os.path.isfile(str(settings.REPOS_DIR) + "/" + pr.project.name + "/" + filename):
            if filename.endswith(".F90"):
                # Open and read the file
                with open(
                    str(settings.REPOS_DIR) + "/" + pr.project.name + "/" + filename, "r"
                ) as f:
                    lines = f.readlines()
                    f.close()
                filecontents = "".join(lines)

                completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role":"user", "content":filecontents}])

                llm.append({"filename": filename, "results": completion.choices[0].message.content})

                break'''

    resultdata = {
        "diffcommits": diffcommits,
        "prcommits": prcommits,
        "docstring_results": docstring_results,
        "linter_results": linter_results,
        "llm": llm,
        "dev_table": dev_table,
        "merged_dev_table": merged_dev_table,
        "extra_devs": extra_devs,
        "source_url": pr.project.source_url[0:-4],
        "repo_structure": repo_structure(str(settings.REPOS_DIR) + "/" + pr.project.name),
    }

    return HttpResponse(json.dumps(resultdata), content_type="application/json")


@login_required
def getFile(request):

    print("Get File DATA")

    # print(request.POST.get('pr'))

    prid = 2250
    if request.POST.get("pr"):
        prid = int(request.POST.get("pr"))

    #if not hasAccessToPR(request.user, prid):
    #    return redirect("not_authorized")

    filename = "folder1/arithmetic.py"
    if request.POST.get("filename"):
        filename = request.POST.get("filename")

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    # Open and read the file
    with open(
        str(settings.REPOS_DIR) + "/" + pr.project.name + "/" + filename, "r"
    ) as f:
        lines = f.readlines()
        f.close()

    # If python file or fortran file, get linter results
    linter_results = []
    # docstring_results = []

    '''if filename.endswith(".py"):
        # output = os.popen('export PYTHONPATH=${PYTHONPATH}:'+os.path.abspath(str(settings.REPOS_DIR)+'/'+pr.project.name)+' ; cd '+str(settings.REPOS_DIR)+'/'+pr.project.name+' ; pylint --output-format=json '+filename).read()
        rawresults = []
        try:
            output = os.popen(
                "export PYTHONPATH=${PYTHONPATH}:"
                + os.path.abspath(str(settings.REPOS_DIR) + "/" + pr.project.name)
                + " ; cd "
                + str(settings.REPOS_DIR)
                + "/"
                + pr.project.name
                + " ; . ../meercat/meercat-env/bin/activate ; pylint --output-format=json "
                + filename
            ).read()
            rawresults = json.loads(output)
        except Exception as e:
            pass

        for result in rawresults: 
            if 'Unnecessary parens after' not in result['message'] and 'doesn\'t conform to snake_case naming style' not in result['message'] and 'More than one statement on a single line' not in result['message'] and 'Missing function or method docstring' not in result['message'] and 'Formatting a regular string which' not in result['message'] and 'Unnecessary semicolon' not in result['message'] and 'Trailing whitespace' not in result['message'] and 'Bad indentation' not in result['message'] and 'Line too long' not in result['message']:
                linter_results.append(result) 
        # docstring_results = first_responder_function(pr.project, pr)

    if filename.endswith(".F90"):
        output = os.popen(
            "export PYTHONPATH=${PYTHONPATH}:"
            + os.path.abspath(str(settings.REPOS_DIR) + "/" + pr.project.name)
            + " ; cd "
            + str(settings.REPOS_DIR)
            + "/"
            + pr.project.name
            + " ; . ../meercat/meercat-env/bin/activate ; fortran-linter "
            + str(settings.REPOS_DIR)
            + "/"
            + pr.project.name
            + "/"
            + filename
            + " --syntax-only"
        ).read()

        results = []
        for result in output.split(
            str(settings.REPOS_DIR) + "/" + pr.project.name + "/" + filename + ":"
        ):
            if result and len(result) > 0:
                try:
                    if 'Replace .' not in result and 'At least one space before comment' not in result and 'Exactly one space after' not in result and 'Missing space' not in result and 'Single space' not in result and 'Trailing whitespace' not in result and 'Line length' not in result:
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
        linter_results = results

    if filename.endswith(".c"):
        output = os.popen(
            "export PYTHONPATH=${PYTHONPATH}:"
            + os.path.abspath(str(settings.REPOS_DIR) + "/" + pr.project.name)
            + " ; cd "
            + str(settings.REPOS_DIR)
            + "/"
            + pr.project.name
            + " ; . ../meercat/meercat-env/bin/activate ; cpplint --filter=-whitespace "
            + str(settings.REPOS_DIR)
            + "/"
            + pr.project.name
            + "/"
            + filename
            + " 2>&1"
        ).read()
        # linter_results = output.split('../'+pr.project.name+'/'+filename)
        results = []
        for result in output.split(
            str(settings.REPOS_DIR) + "/" + pr.project.name + "/" + filename + ":"
        ):
            if result and len(result) > 0:
                try:
                    if 'Include the directory when naming header' not in result and 'Using C-style cast.' not in result:
                        results.append(
                            {
                                "column": 0,
                                "line": int(result.split(":")[0]),
                                "message": result.split(":")[1].split("  [")[0].strip(),
                                "type": result.split(":")[1].split("  [")[1].split("] ")[0],
                            }
                        )
                except:
                    pass
        linter_results = results'''

    if not request.POST.get("llm"):
        linter_results = default_linter.check_file(pr.project, settings, filename)

    print("LINTER RESULTS: "+str(linter_results))
    # print("DOC CHECKER RESULTS: "+str(docstring_results))


    # Only call ChatGPT on F90 files for now (only calling on one file for initial testing)
    llm = "N/A"
    if request.POST.get("llm") and (filename.endswith(".F90") or filename.endswith(".py")):

        # Setup ChatGPT
        with open(settings.BASE_DIR / "meercat.config.json") as meercat_config:
            config = json.load(meercat_config)
        openai.api_key = config["OPEN_API_KEY"]

        print("CHATGPT: LLM")

        #completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role":"user", "content":"Please provide a critique-focused review of my Fortran 90 code. Ignore #include and @todo directives. Assume calls on ml_error have no problems. Ignore hard-coded indices. When checking argument typing, pay attention to use statements and derived types. Do not include a summary of the code, only problems with the code that you see."}])
        #completion = openai.ChatCompletion.create(model="gpt-4", messages=[{"role":"user", "content":"Please provide a critique-focused review of my Fortran 90 code. Ignore #include and @todo directives. Assume calls on ml_error have no problems. Ignore hard-coded indices. When checking argument typing, pay attention to use statements and derived types. Do not include a summary of the code, only problems with the code that you see."}])
        
        # First check to see if we have cached results
        llm_metrics = list(FileMetric.objects.all().filter(file_path=filename, pull_request=pr, metric_type=FileMetric.MetricTypeChoices.LLM))
        llm = ""

        # If no cache, call ChatGPT and then cache the results
        if len(llm_metrics) < 1:

            print("CHATGPT: CALLING API")

            # Open and read the file
            filecontents = "".join(lines)

            prompt = "Please provide a critique-focused review of my Fortran 90 code. Ignore #include and @todo directives. Assume calls on ml_error have no problems. Ignore hard-coded indices. When checking argument typing, pay attention to use statements and derived types. Do not include a summary of the code, only problems with the code that you see.\n\n"
            if filename.endswith(".py"):
                prompt = "Please provide a critique-focused review of my python code. Do not include a summary of the code, only problems with the code that you see.\n\n"

            #completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role":"user", "content":filecontents}])
            #completion = openai.ChatCompletion.create(model="gpt-4", messages=[{"role":"user", "content":filecontents}])
            completion = openai.ChatCompletion.create(model="gpt-3.5-turbo-16k", messages=[{"role":"user", "content":prompt+filecontents}])
            #completion = openai.ChatCompletion.create(model="gpt-4", messages=[{"role":"user", "content":"Please provide a critique-focused review of my Fortran 90 code. Ignore #include and @todo directives. Assume calls on ml_error have no problems. Ignore hard-coded indices. When checking argument typing, pay attention to use statements and derived types. Do not include a summary of the code, only problems with the code that you see.\n\n"+filecontents}])

            llm = completion.choices[0].message.content

            FileMetric.objects.create(datetime=datetime.datetime.today(), file_path=filename, pull_request=pr, metric_type=FileMetric.MetricTypeChoices.LLM, result_string=llm)

        # Else load the cached results
        else:  
            print("CHATGPT: USING CACHE")

            llm = llm_metrics[0].result_string  


    resultdata = {"filecontents": "".join(lines), "linter_results": linter_results, "llm":llm}

    return HttpResponse(json.dumps(resultdata), content_type="application/json")


@login_required
def getDocTemplate(request):

    print("Get TEMPLATE")

    prid = 2250
    if request.POST.get("pr"):
        prid = int(request.POST.get("pr"))

    if not hasAccessToPR(request.user, prid):
        return redirect("not_authorized")

    filename = "folder1/arithmetic.py"
    if request.POST.get("filename"):
        filename = request.POST.get("filename")

    template = '  """\\n  Template will go here.\\n  """'

    if filename.endswith(".py"):
        template = python_doxygen_template(request.POST.get("signature"))

    if filename.endswith(".F90"):
        template = fortran_doxygen_template(request.POST.get("signature"))

    resultdata = {
        "template": template,
    }

    return HttpResponse(json.dumps(resultdata), content_type="application/json")


@login_required
def sendInvite(request):

    print("Send Invite Email")

    prid = 2250
    if request.POST.get("pr"):
        prid = int(request.POST.get("pr"))

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]
    commits = list(
        Commit.objects.all().filter(
            hash__in=[committag.sha for committag in set(pr.commits.all())]
        )
    )

    branch = "main"
    if len(commits) > 0:
        branch = commits[0].branch.split()[-1]

    if not hasAccessToPR(request.user, prid):
        return redirect("not_authorized")

    email = "jprideau@cs.uoregon.edu"
    if request.POST.get("email"):
        email = request.POST.get("email")

    extra = False
    if request.POST.get("extra"):
        extra = True

    filenames = ""
    if request.POST.get("filenames"):
        filenames = request.POST.get("filenames")

    filenames = filenames.split()
    filenames = list(set(filenames))

    print("Files: " + str(len(filenames)))
    print(email)

    filetext = ""
    for filename in filenames:
        filetext += (
            filename
            + " https://meercat.cs.uoregon.edu/dashboard/filex/"
            + str(pr.project.id)
            + "?filename="
            + filename
            + "&branch="
            + branch
            + " \n"
        )

    if extra:
        gmail_send_message(
            subject="MeerCat Invitation",
            body="You were invited to be a part of a new Pull Request: https://meercat.cs.uoregon.edu/dashboard/pr/"
            + str(prid)
            + "\n\nYou are invited to join the PR discussion if interested.",
            recipient_list=[email],
        )
    elif len(filenames) < 5:
        gmail_send_message(
            subject="MeerCat Invitation",
            body="Files that you have worked on in the past are part of a new Pull Request: https://meercat.cs.uoregon.edu/dashboard/pr/"
            + str(prid)
            + "\n\nThe files are:\n\n"
            + filetext
            + "\nYou are invited to join the PR discussion if interested.",
            recipient_list=[email],
        )
    else:
        gmail_send_message(
            subject="MeerCat Invitation",
            body="You have worked on many files in the past that are part of a new Pull Request: https://meercat.cs.uoregon.edu/dashboard/pr/"
            + str(prid)
            + "\n\nYou are invited to join the PR discussion if interested.",
            recipient_list=[email],
        )

    resultdata = {
        "result": "success",
    }

    return HttpResponse(json.dumps(resultdata), content_type="application/json")


@login_required
def updateTags(request):

    print("Update Tags")

    prid = 2250
    if request.POST.get("pr"):
        prid = int(request.POST.get("pr"))

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    if not hasAccessToPR(request.user, prid):
        return redirect("not_authorized")

    print(request.POST.get("tags"))
    tags = []
    if request.POST.get("tags"):
        tags = request.POST.get("tags").split(",")

    print("Tags: " + str(len(tags)))

    # loop through tags and add to PR (if not in PR)
    labels = [label.name for label in pr.labels.all()]
    for tag in tags:
        if tag not in labels:
            print("missing!!!")
            label = Label.objects.create(name=tag)
            PullRequestLabel.objects.create(pr=pr, label=label)

    for label in pr.labels.all():
        if label.name not in tags:
            print("delete label")
            label.delete()

    # Update github with updated list of labels.
    try:
        repo_name = pr.project.name
        repo_owner = get_repo_owner(pr.project)
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{pr.number}/labels"
        payload = {"labels": tags}
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "token " + os.environ.get("MEERCAT_USER_TOKEN"),
        }

        # Use put to set labels instead of add new ones
        # Use delete to clear all labels
        # result = requests.post(url, headers=headers, data=json.dumps(payload))
        result = requests.put(url, headers=headers, data=json.dumps(payload))

        # Do a GET to get all labels for repo
        # url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/labels"
    except:
        pass

    resultdata = {
        "result": "success",
    }

    return HttpResponse(json.dumps(resultdata), content_type="application/json")


@csrf_exempt
def githubBot(request):

    print("Callback from webhook bot on github")

    payload = json.loads(request.body)

    print( str(payload) )

    print("Action Type: " + str(payload["action"]))
    print("Pull Request Number: " + str(payload["number"]))
    print("Repository: " + str(payload["repository"]["clone_url"]))
    print("Draft: " + str(payload["pull_request"]["draft"]))
    print("Branch from: " + str(payload["pull_request"]["head"]["label"]))

    prnumber = str(payload["number"])

    project = list(
        Project.objects.all()
        .filter(source_url=str(payload["repository"]["clone_url"]))
        .all()
    )[0]




    # Only do this for opened PRs (also do for edited PRS for test project)
    test_project_id = 30
    if str(payload["action"]) == "opened" or (project.id == test_project_id and str(payload["action"]) == "edited"):

        # Ignore if merging into main or master
        frombranch = str(payload["pull_request"]["head"]["label"])
        targetbranch = str(payload["pull_request"]["base"]["label"])

        # Check to see if PR is from a fork
        from_org = frombranch.split(":")[0]
        proj_org = project.source_url[19:]
        if proj_org is not None and from_org is not None and not proj_org.startswith(from_org):
            '''try:
                with open(settings.BASE_DIR / 'meercat.config.json') as meercat_config:
                    config = json.load(meercat_config)

                repo_name = project.name
                repo_owner = get_repo_owner(project)
                url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{prnumber}/comments"

                gh_payload = {
                    "body": "## MeerCat warning: The branch in this PR appears to be from a fork.  Currently, MeerCat cannot analyze forks."
                }

                headers = {
                    "Accept": "application/vnd.github+json",
                    "Authorization": "token " + config['MEERCAT_USER_TOKEN'],
                }
                result = requests.post(url, headers=headers, data=json.dumps(gh_payload))
            except Exception as e:
                print(e)
                pass'''

            #  git fetch origin pull/610/head:fork610  
            #  git checkout fork610  
            print("+-------- PULL REQUEST FROM A FORK --------+")
            cmd = f"cd {settings.REPOS_DIR}/{project.name} ; git fetch origin pull/{prnumber}/head:fork{prnumber} ; git checkout --force fork{prnumber}"
            try:
                os.system(cmd)
            except:
                print(f"Failure to checkout the pull {cmd}")

        if  project.id == test_project_id or ("main" not in targetbranch and "master" not in targetbranch):

            # Only post comments for anl_test_repo and FLASH5
            #if project.id == 35 or project.id == 30 or project.id == 26:
            '''try:
                # BASE_DIR = Path(__file__).resolve().parent.parent
                with open(settings.BASE_DIR / 'meercat.config.json') as meercat_config:
                    config = json.load(meercat_config)

                repo_name = project.name
                repo_owner = get_repo_owner(project)
                url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{prnumber}/comments"
                gh_payload = {
                    "body": "## MeerCat is working on this PR.  Please stay tuned."
                }

                branch = str(payload["pull_request"]["head"]["label"]) #TODO: We might not care where it is coming from
                if "staged" not in targetbranch: # make sure it is going into staged.
                    gh_payload = {
                        "body": "## MeerCat will ignore this PR because it is not going to the staged branch."
                    }

                headers = {
                    "Accept": "application/vnd.github+json",
                    "Authorization": "token " + config['MEERCAT_USER_TOKEN'],
                }
                result = requests.post(url, headers=headers, data=json.dumps(gh_payload))
            except Exception as e:
                print(e)
                pass'''        


            # Queue
            # Make the queue a size of one, and then put will block

            # Need to refresh the database before
            username = settings.DATABASES["default"]["USER"]
            password = settings.DATABASES["default"]["PASSWORD"]
            # cmd = f'cd .. ; export PYTHONPATH=. ; nohup python3 ./src/gitutils/update_database.py {username} {password} {project.id}'
            cmd = f"cd {settings.REPOS_DIR} ; . meercat/meercat-env/bin/activate ; export PYTHONPATH=. ; nohup python3 ./src/gitutils/update_database.py {username} {password} {project.id}"
            # os.system(cmd)
            result = subprocess.check_output(cmd, shell=True)

            pull_request = list(
                PullRequest.objects.all()
                .filter(project=project.id, number=int(prnumber))
                .all()
            )[0]

            # Queue
            # Remove item from queue


            # Analyze the files and get the message to send back to github
            comment, all_contexts = first_responder_function(pull_request.project, pull_request)
            print("------------")
            if comment:
                # Only post comment if the target is staged
                # branch = str(payload["pull_request"]["head"]["label"]) #TODO: maybe remove this since only care if target is staged
                # if "staged" in targetbranch and (project.id == 35 or project.id == 30 or project.id == 26):
                if "staged" in targetbranch:
                    comment_pullrequest(pull_request, comment)
                    print("commented")

            else:
                event = EventLog(
                    event_type=EventLog.EventTypeChoices.NO_NOTIFICATION,
                    pull_request=pull_request,
                    datetime=datetime.datetime.today(),
                )
                event.save()
                print("don't bug me")
            print("------------")


            # Now notify any subscribers
            profiles = Profile.objects.all()
            for profile in profiles:
                subscriptions = profile.subscriptions
                print("------------ CHECKING " + profile.user.username)
                try:
                    # Project subs is just an array of file names
                    project_subs = subscriptions[pull_request.project.name]

                    send_email = False

                    # Next, see if any PR files match file in project_subs
                    for filename,context in all_contexts.items():
                        for filename_sub in project_subs:
                            if filename_sub == filename:
                                # Send the email!
                                send_email = True

                    if send_email:
                        print("+---------- SHOULD SEND EMAIL!!!!!! -----------+")

                        if profile.user.email:
                            gmail_send_message(
                                subject="MeerCat Notification",
                                body="A new Pull Request has been created that you may be interested in: https://meercat.cs.uoregon.edu/dashboard/pr/"
                                + str(pull_request.id)
                                + "\n\nYou are receiving this because you are subscribed to a file that was modified in this Pull Request.",
                                recipient_list=[profile.user.email],
                            )
                        else:
                            gmail_send_message(
                                subject="MeerCat Notification",
                                body="A new Pull Request has been created that you may be interested in: https://meercat.cs.uoregon.edu/dashboard/pr/"
                                + str(pull_request.id)
                                + "\n\nYou are receiving this because you are subscribed to a file that was modified in this Pull Request.",
                                recipient_list=[profile.gh_email],
                            )

                except Exception as e:
                    print( "EXCEPTION "+str(e))

        else:
            # Only post comments for anl_test_repo and FLASH5
            # if project.id == 35 or project.id == 30 or project.id == 26:
            try:
                # BASE_DIR = Path(__file__).resolve().parent.parent
                with open(settings.BASE_DIR / 'meercat.config.json') as meercat_config:
                    config = json.load(meercat_config)

                repo_name = project.name
                repo_owner = get_repo_owner(project)
                url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{prnumber}/comments"

                branch = str(payload["pull_request"]["head"]["label"]) # get the from branch
                if "staged" not in branch: # this means a feature branch going directly into main.
                    gh_payload = {
                        "body": "## MeerCat warning: The branch in this PR appears to be skipping the staged branch."
                    }

                    headers = {
                        "Accept": "application/vnd.github+json",
                        "Authorization": "token " + config['MEERCAT_USER_TOKEN'],
                    }
                    result = requests.post(url, headers=headers, data=json.dumps(gh_payload))
            except Exception as e:
                print(e)
                pass             

        
    return HttpResponse(
        json.dumps({"results": "success"}), content_type="application/json"
    )


# Uses the Visualizer code to generate a graph.
# Works just for FLASH5 at the moment, but can be made to be more generic.
@login_required
def patternGraph1(request):
    print("PATTERN DATA")

    print(request.GET.get("start"))

    startdate = request.GET.get("start")
    enddate = request.GET.get("end")

    if startdate:
        startdate = datetime.datetime.strptime(startdate, "%Y-%m-%d")
    else:
        startdate = datetime.datetime.fromtimestamp(0)

    if enddate:
        enddate = datetime.datetime.strptime(enddate, "%Y-%m-%d")
    else:
        enddate = datetime.datetime.today()

    prid = 2250
    if request.GET.get("pr"):
        prid = int(request.GET.get("pr"))

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]
    commits = list(
        Commit.objects.all().filter(
            hash__in=[committag.sha for committag in pr.commits.all()]
        )
    )
    diffs = list(Diff.objects.all().filter(commit__in=[c for c in commits]))
    filenames = [d.file_path for d in diffs]

    # Visualizer()
    # vis = Visualizer(project_name='FLASH5')
    # vis.get_data()

    # removed = vis.remove_external()
    # removed = vis.remove_files(filenames)

    # vis.hide_names = False

    # Setting year or range seems to break some graphs
    # if startdate.year == enddate.year:

    # TEMPORARILY VIEW ALL YEARS
    # vis.set_year(enddate.year)

    # vis.select_month_range()
    # else:
    #    vis.select_year_range(startdate.year,enddate.year)

    # df = vis.plot_zone_heatmap(agg='mean')
    # df = vis.plot_top_N_heatmap(10, locc_metric='locc')

    # TEMPORARILY VIEW ALL YEARS
    # df = vis.plot_top_N_heatmap(10, time_range='year', locc_metric='change-size-cos')
    # df = vis.plot_top_N_heatmap(10, locc_metric='change-size-cos')

    resultdata = {
        #'filename': 'spack-zone-change-size-cos-map-Entire_project-mean.png',
        #'filename': 'FLASH5-top-10-locc-map-Entire_project.png',
        #'filename': 'FLASH5-top-10-change-size-cos-map-'+str(enddate.year)+'.png',
        "filename": "FLASH5-top-10-change-size-cos-map-Entire_project.png",
    }

    return HttpResponse(json.dumps(resultdata), content_type="application/json")


# Branches view (is this still needed)
@login_required
def branches(request):
    print("BRANCHES")
    template = loader.get_template("dashboard/branches.html")
    context = {}

    return HttpResponse(template.render(context, request))


# Returns branch data for anl_test_repo
# If this is still useful, need to make more generic
@login_required
def branchData(request):
    print("BRANCHES DATA")

    config = configparser.ConfigParser()
    config.read(str(settings.REPOS_DIR) + "/credentials.ini")

    GitHubAPIClient.set_credentials(
        username=config["github"]["login"], token=config["github"]["token"]
    )

    GitHubAPIClient.check_credentials()

    data = GitHubAPIClient.fetch_events(owner="fickas", repository="anl_test_repo")

    df = pd.DataFrame(data)

    created_branches = []
    deleted_branches = []
    for i in range(len(df)):
        if (
            df.loc[i, "type"] == "CreateEvent"
            and df.loc[i, "payload"]["ref_type"] == "branch"
        ):
            created_branches.append(df.loc[i, "payload"]["ref"])
        if (
            df.loc[i, "type"] == "DeleteEvent"
            and df.loc[i, "payload"]["ref_type"] == "branch"
        ):
            deleted_branches.append(df.loc[i, "payload"]["ref"])

    open_branches = set(created_branches) - set(deleted_branches)
    feature_branches = list(open_branches - set(["main", "development", "staged"]))

    branches = pd.DataFrame(columns=["Name", "Author", "Created", "Deleted"]).set_index(
        "Name"
    )

    for i in range(len(df)):
        if (
            df.loc[i, "type"] in ["CreateEvent", "DeleteEvent"]
            and df.loc[i, "payload"]["ref_type"] == "branch"
        ):
            name = df.loc[i, "payload"]["ref"]
            author = df.loc[i, "actor"]["login"]
            date = df.loc[i, "created_at"]
            event_type = "Created" if df.loc[i, "type"] == "CreateEvent" else "Deleted"
            if name in branches.index.to_list():
                branches.loc[name, event_type] = date
                branches.loc[name, "Author"] = author
            else:
                row = {"Author": author, "Created": "", "Deleted": ""}
                branches.loc[name] = row
                branches.loc[name, event_type] = date

    # TODO: update this to only attempt to drop if keys exist, otherwise error is thrown.
    # branches = branches.drop(['main', 'staged', 'development']).fillna('None')

    # might be easier to use for javascript
    name_column = branches.index.to_list()
    author_column = branches["Author"].to_list()
    created_column = branches["Created"].to_list()
    deleted_column = branches["Deleted"].to_list()

    resultdata = {
        "open_branches": list(open_branches),
        "created_branches": created_branches,
        "deleted_branches": deleted_branches,
        "feature_branches": feature_branches,
        "name_column": name_column,
        "author_column": author_column,
        "created_column": created_column,
        "deleted_column": deleted_column,
    }

    return HttpResponse(json.dumps(resultdata), content_type="application/json")


def repo_structure(start, begin_start=None):

    folder_structure = []

    for thing in os.listdir(start):
        ogthing = thing
        thing = os.path.join(start, thing)
        if os.path.isfile(thing):
            folder_structure.append({'isFile':True, 'name':ogthing})

    for thing in os.listdir(start):
        if not thing.startswith(".git") and not thing.startswith("repos"):
            ogthing = thing
            thing = os.path.join(start, thing)
            if os.path.isdir(thing):
                folder_structure.append({'isFile':False, 'name':ogthing, 'contents':repo_structure(thing, begin_start=start)})

    return folder_structure

def countlines(start, lines=0, header=True, begin_start=None):
    # if header:
    #    print('{:>10} |{:>10} | {:<20}'.format('ADDED', 'TOTAL', 'FILE'))
    #    print('{:->11}|{:->11}|{:->20}'.format('', '', ''))

    # TODO: Currently only counds python code.

    for thing in os.listdir(start):
        thing = os.path.join(start, thing)
        if os.path.isfile(thing):
            if thing.endswith(".py"):
                with open(thing, "r") as f:
                    newlines = f.readlines()
                    newlines = len(newlines)
                    lines += newlines

                    # if begin_start is not None:
                    #    reldir_of_thing = '.' + thing.replace(begin_start, '')
                    # else:
                    #    reldir_of_thing = '.' + thing.replace(start, '')

                    # print('{:>10} |{:>10} | {:<20}'.format(newlines, lines, reldir_of_thing))

    for thing in os.listdir(start):
        thing = os.path.join(start, thing)
        if os.path.isdir(thing):
            lines = countlines(thing, lines, header=False, begin_start=start)

    return lines


def countlinespython(start, lines=0, header=True, begin_start=None):

    for thing in os.listdir(start):
        thing = os.path.join(start, thing)
        if os.path.isfile(thing):
            if thing.endswith(".py"):
                with open(thing, "r", errors='ignore') as f:
                    newlines = f.readlines()
                    newlines = len(newlines)
                    lines += newlines

    for thing in os.listdir(start):
        if not thing.startswith(".git") and not thing.startswith("repos"):
            thing = os.path.join(start, thing)
            if os.path.isdir(thing):
                lines = countlinespython(thing, lines, header=False, begin_start=start)

    return lines


def countlinesfortran(start, lines=0, header=True, begin_start=None):

    for thing in os.listdir(start):
        thing = os.path.join(start, thing)
        if os.path.isfile(thing):
            if thing.endswith(".F90"):
                with open(thing, "r", errors='ignore') as f:
                    newlines = f.readlines()
                    newlines = len(newlines)
                    lines += newlines

    for thing in os.listdir(start):
        if not thing.startswith(".git") and not thing.startswith("repos"):
            thing = os.path.join(start, thing)
            if os.path.isdir(thing):
                lines = countlinesfortran(thing, lines, header=False, begin_start=start)

    return lines


def countlinesc(start, lines=0, header=True, begin_start=None):

    for thing in os.listdir(start):
        thing = os.path.join(start, thing)
        if os.path.isfile(thing):
            if thing.endswith(".c") or thing.endswith(".h") or thing.endswith(".cpp"):
                with open(thing, "r", errors='ignore') as f:
                    try:
                        newlines = f.readlines()
                        newlines = len(newlines)
                        lines += newlines
                    except:
                        pass

    for thing in os.listdir(start):
        if not thing.startswith(".git") and not thing.startswith("repos"):
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
        if not thing.startswith(".git") and not thing.startswith("repos"):
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





def handle_hypre(proj_object, filenames, project_info):
    proj_id = proj_object.id  # proj_id==26 or proj_id==35:  #Flash5 or Flash-X
    assert "filenames" in project_info, f"filenames missing from project_info {proj_id}"
    assert (
        "extensions" in project_info
    ), f"extensions missing from project_info {proj_id}"

    # hypre uses Doxygen with no predefined fields. Everything is open prose.
    # it is expected the prototype files are ones carrying comments.
    # it "appears" that prototype files only appear in .h files.
    # so only thing to check is for a prototype without a preceding Doxygen comment

    # All the user interfaces appear in header files that have the upper-case form ‘HYPRE_*.h’
    # The user interface functions all start with the upper-case prefix ‘HYPRE_’

    def check_hypre_prototype(lines, i):
        line = lines[i]
        s = line.find(" ")
        if s == -1:
            return ("", [], i)
        j = line[s:].find("HYPRE_")  # per Rob's instructions for public functions
        if j == -1:
            return ("", [], i)
        k = line[s:].find("(")
        if k == -1:
            return ("", [], i)
        name = line[s + 1 : line.find("(")].strip()

        # looks like found target prototype. Now get args. Can be multi-line.
        """
        HYPRE_Int HYPRE_IJMatrixCreate(MPI_Comm        comm,
                    HYPRE_BigInt    ilower,
                    HYPRE_BigInt    iupper,
                    HYPRE_BigInt    jlower,
                    HYPRE_BigInt    jupper,
                    HYPRE_IJMatrix *matrix);
        """

        args = line[line.find("(") + 1 :]
        while not args.strip().endswith(
            ");"
        ):  # ; signals this is prototype - only thing we are looking for
            i += 1
            if i >= len(lines):
                assert False, f"Malformed prototype {path},{name}"
            args += lines[i].strip()
        args = args.strip()[:-2]
        arg_list = args.split(",")
        just_args = [arg[arg.rfind(" ") :].strip().replace("*", "") for arg in arg_list]
        print(f"args: {arg_list}, {just_args}")
        return name, just_args, i

    def find_missing_hypre_params(doc_string, sig_params):
        e_pattern = "\e "
        missing_params = []
        missing_e = []
        doc_string = (
            doc_string.replace("\n", " ")
            .replace(".", " ")
            .replace(",", " ")
            .replace("*", " ")
        )
        for param in sig_params:
            j = doc_string.find(f" {param} ")
            if j == -1:
                missing_params.append(param)
            else:
                if (
                    doc_string[j - 2] == e_pattern[0]
                    and doc_string[j - 1] == e_pattern[1]
                    and doc_string[j] == e_pattern[2]
                ):
                    print(f"param has e: {param}")
                else:
                    missing_e.append(param)
        return missing_params, missing_e

    proj_name = proj_object.name
    file_lines = []
    for path in filenames:
        full_filename = os.path.basename(path)
        name, extension = os.path.splitext(full_filename)

        print(path, full_filename, extension, name)
        if extension == ".h" and name.startswith("HYPRE_"):  # per Rob's instructions
            with open(str(settings.REPOS_DIR) + "/" + proj_name + "/" + path, "r") as f:
                lines = f.readlines()
                f.close()
            file_lines.append((path, name, extension, lines))
        else:
            print(f"Uncheckable currently: {full_filename}")
            file_lines.append((path, name, extension, None))

    # Gather info on each file in file_lines
    all_files = []

    for path, name, extension, lines in file_lines:

        if not lines:
            all_files.append((path, [], "ignored"))
            continue  # no lines to check for file

        function_info = []
        i = 0  # start at top of file
        while i < len(lines):

            # look for doxygen. Not so easy. We cannot tell if doxygen comment is for subroutine or something else. robodoc actually flags it in header.
            # So search past comment to see if find subroutine. If not, ignore the comment (for now).
            if lines[i].startswith("/**"):
                doc_start = i
                while i < len(lines) and not lines[i].strip().startswith("**/"):
                    i += 1
                # found doc++ comment. Does it go with prototype?

                if i >= len(lines):
                    break  # done with file
                doc_end = i

                doc_string = ""
                for line in lines[doc_start : doc_end + 1]:
                    doc_string += line
                i += 1  # move to line after doc
                # skip over white space
                while i < len(lines) and lines[i].strip() == "":
                    print(f"skipping line {i}")
                    i += 1
                if i >= len(lines):
                    break  # done with file
                # we ran into a line that not comment or blank that follows the doxygen comment. See if prototype.
                sig_name, sig_params, i = check_hypre_prototype(lines, i)
                if not sig_name:
                    i += 1  # skip over whatever it is and keep looking
                    continue  # comment is for something other than prototype

                # found comment and prototype
                backslash = "\\"
                missing_params, missing_e = find_missing_hypre_params(
                    doc_string, sig_params
                )
                issues = (
                    [
                        [
                            f"Parameters not mentioned in comments: {missing_params}",
                            doc_start,
                        ]
                    ]
                    if missing_params
                    else []
                )
                issues = (
                    issues
                    + [[f"Parameters missing \\e comments: {missing_e}", doc_start]]
                    if missing_e
                    else issues
                )
                fields = []  # for now - can look for them at some point
                doc_params = (
                    []
                )  # might look at \e foo as naming param and see if really is
                params_start = 0
                function_info.append(
                    (
                        sig_name,
                        sig_params,
                        doc_string,
                        doc_start,
                        doc_end,
                        fields,
                        doc_params,
                        params_start,
                        issues,
                    )
                )
                i += 1
                continue

            # look for prototype with missing docstring
            sig_name, sig_params, i = check_hypre_prototype(lines, i)
            if sig_name:
                doc_params = []
                params_start = 0
                doc_lines = []
                doc_fields = []
                doc_start = 0
                doc_end = 0
                issues = [[f"Prototype missing Doxygen comment: {sig_name}", i]]

                function_info.append(
                    (
                        sig_name,
                        sig_params,
                        doc_lines,
                        doc_start,
                        doc_end,
                        doc_fields,
                        doc_params,
                        params_start,
                        issues,
                    )
                )  # no doc string

            i += 1  # keep looking through file

        # done looking for docstrings and subroutines in file. Now work on docstring alignment and mandatory fields

        extended_info = []
        for (
            sig_name,
            sig_params,
            doc,
            doc_start,
            doc_end,
            doc_fields,
            doc_params,
            params_start,
            issues,
        ) in function_info:

            # if no doc no reason to check matching
            if not doc:
                extended_info.append(
                    (
                        sig_name,
                        sig_params,
                        doc,
                        doc_start,
                        doc_end,
                        doc_fields,
                        doc_params,
                        params_start,
                        issues,
                    )
                )  # no doc string found
                continue

            # found docstring
            mandatories = project_info["docstring_mandatory"]
            mandatory_issues = check_mandatory(mandatories, doc_fields, doc_start)
            all_issues = issues + mandatory_issues
            extended_info.append(
                (
                    sig_name,
                    sig_params,
                    doc,
                    doc_start,
                    doc_end,
                    doc_fields,
                    doc_params,
                    params_start,
                    all_issues,
                )
            )  # add in new issues

        file_table = [
            {
                "signature_name": sig_name,
                "signature_params": sig_params,
                "full_signature": sig_name + "(" + ", ".join(sig_params) + ")",
                "docstring": "".join(doc),
                "doc_fields": doc_fields,
                "doc_start": doc_start,
                "params_start": params_start,
                "test_info": [],
                "result": issues,
            }
            for sig_name, sig_params, doc, doc_start, doc_end, doc_fields, doc_params, params_start, issues in extended_info
        ]
        all_files.append((path, file_table, "checked"))

    return all_files


def handle_anl_test_repo(proj_object, filenames, project_info):
    proj_id = proj_object.id
    assert "filenames" in project_info, f"filenames missing from project_info {proj_id}"
    assert (
        "extensions" in project_info
    ), f"extensions missing from project_info {proj_id}"

    proj_name = proj_object.name
    file_lines = []
    for filename in filenames:
        name, extension = os.path.splitext(filename)
        if (extension and extension in project_info["extensions"]) or (
            not extension and filename in project_info["filenames"]
        ):
            with open(
                str(settings.REPOS_DIR) + "/" + proj_name + "/" + filename, "r"
            ) as f:
                lines = f.readlines()
                f.close()
            file_lines.append((filename, name, extension, lines))
        else:
            print(f"Uncheckable currently: {filename}")
            file_lines.append((filename, name, extension, None))

    # Gather info on each file in file_lines
    all_files = []

    for path, name, extension, lines in file_lines:

        if not lines:
            all_files.append((name + extension, [], "currently uncheckable"))
            continue  # no lines to check for file

        function_info = (
            []
        )  # find all the functions in the file and record info on each of them
        i = 0

        # Python uses dostring that follows function. There is an alternative with doxygen where the comments
        # can precede, but it is frowned upon. Not handling Doxygen preceding comments currently.

        # find function signature then look for docstring following
        while i < len(lines):
            sig_start = i
            i, sig_name, sig_params = get_py_signature(lines, i)
            if not sig_name:
                i += 1  # move on and keep searching
                continue

            # is signature line - check for doc string currently only in numpy format. Adding Google style on todo list. Ditto Doxygen as docstring.
            sig_end = i
            (
                doc,
                doc_start,
                doc_end,
                fields,
                doc_params,
                params_start,
                issues,
            ) = get_py_doc_string(lines, sig_end + 1)

            # after demo, pass in sig_params to check. test_info will have to expand.
            test_info = find_pytest_files(
                proj_name, path, sig_name
            )  # returns list of triples (path, file_name, i)

            # get ready to move test function to repo
            # cd '..'
            # proj_name in os.listdir()

            # import importlib
            # proj = importlib.import_module(proj_name, '')

            # proj.bin.meercat_test_functions.find_pytest_files(proj_name, path, sig_name)

            mandatories = project_info["docstring_mandatory"]
            param_issues = (
                check_param_match(sig_params, doc_params, params_start) if doc else []
            )
            mandatory_issues = (
                check_mandatory(mandatories, fields, doc_start) if doc else []
            )
            all_issues = issues + param_issues + mandatory_issues
            function_info.append(
                (
                    sig_name,
                    sig_params,
                    doc,
                    doc_start,
                    doc_end,
                    fields,
                    doc_params,
                    params_start,
                    test_info,
                    all_issues,
                )
            )
            # print(f'function_info: {function_info}')

            i += 1  # move beyond docstring

        file_table = [
            {
                "signature_name": sig_name,
                "signature_params": sig_params,
                "full_signature": sig_name + "(" + ", ".join(sig_params) + ")",
                "subtype": tuple(),
                "docstring": "".join(doc),
                "doc_fields": doc_fields,
                "doc_start": doc_start,
                "params_start": params_start,
                "test_info": test_info,
                "result": issues,
            }
            for sig_name, sig_params, doc, doc_start, doc_end, doc_fields, doc_params, params_start, test_info, issues in function_info
        ]

        all_files.append((name + extension, file_table, "checked"))

    return all_files




#### Simulating global data about projects


def get_project_info(project_id):
    # simulate project info
    project_info = {
        26: {
            "docstring_kind": "robodoc",
            "docstring_mandatory": [],
            "testing_kind": "custom",
            "main": "master",
            "filenames": [],
            "code_quality": "",
            "supports_callgraph": False,
            "supports_test_hunt": False,
            "extensions": [".F90"],
        },  # flash5
        35: {
            "docstring_kind": "doxygen",
            "docstring_mandatory": [],
            "testing_kind": "custom",
            "main": "master",
            "filenames": [],
            "code_quality": "",
            "supports_callgraph": False,
            "supports_test_hunt": False,
            "extensions": [".F90"],
        },  # flash-x
        32: {
            "docstring_kind": "doc++",
            "docstring_mandatory": [],
            "testing_kind": "custom",
            "main": "master",
            "filenames": [],
            "code_quality": "",
            "supports_callgraph": False,
            "supports_test_hunt": False,
            "extensions": [".h"],
        },  # hypre
        30: {
            "docstring_kind": "numpy",
            "docstring_mandatory": ["Parameters", "Returns", "Raises"],
            "testing_kind": "pytest",
            "main": "main",
            "filenames": [],
            "code_quality": "CodeQL",
            "supports_callgraph": True,
            "supports_test_hunt": True,
            "extensions": [".py", ".F90"],
        },  # anl_test_repo
    }
    return project_info[project_id] if project_id in project_info else None


# Folder explorer
# localhost:8080/dashboard/folderx/25?branch=master&folder=path  where 25 is test_anl id and path is to file
def folder_explorer(request, *args, **kwargs):

    template = loader.get_template("dashboard/folder_explorer.html")

    # Get PR id
    if kwargs["pk"]:
        proj_id = int(kwargs["pk"])
        project = list(Project.objects.all().filter(id=proj_id).all())[0]
    else:
        return HttpResponse(
            json.dumps("Missing project"), content_type="application/json"
        )

    proj_list = list(Project.objects.all().filter(id=proj_id).all())
    if not proj_list:
        return HttpResponse(
            json.dumps(f"Unknown project {proj_id}"), content_type="application/json"
        )

    # Get branch
    if request.GET.get("branch"):
        branch = request.GET.get("branch")
    else:
        return HttpResponse(
            json.dumps(f"Missing branch"), content_type="application/json"
        )

    # Get folderpath
    if request.GET.get("folder"):
        folder = request.GET.get("folder")
    else:
        return HttpResponse(
            json.dumps(f"Missing folder"), content_type="application/json"
        )

    project_info = get_project_info(proj_id)
    if project_info == None:
        return HttpResponse(
            json.dumps(f"Project id missing from project_info {proj_id}"),
            content_type="application/json",
        )

    proj_object = proj_list[0]
    files = list_project_files(proj_object.name, folder, branch)
    #results = [{"filePath": ".github/CODEOWNERS", "errors": False}, {"filePath": ".github/workflows/codeql-analysis.yml", "errors": True}, {"filePath": ".github/workflows/doxygen-gh-pages.yml", "errors": False} ,{"filePath": ".github/workflows/github-actions-demo.yml", "errors": True}]
    results = [{"filePath": ".github/CODEOWNERS", "errors": False}, {"filePath": ".github/workflows/codeql-analysis.yml", "errors": False}, {"filePath": ".github/workflows/doxygen-gh-pages.yml", "errors": False} ,{"filePath": ".github/workflows/github-actions-demo.yml", "errors": False}]

    subscriptions = Profile.objects.get(user=request.user).subscriptions

    context = {
        "folder": folder,
        "project": project,
        "branch": branch,
        "files": files,
        "subscriptions": subscriptions,
        "results": results,
    }

    return HttpResponse(template.render(context, request))



# File explorer
# localhost:8080/dashboard/filex/25?branch=master&filename=path  where 25 is test_anl id and path is to file
def file_explorer(request, *args, **kwargs):

    template = loader.get_template("dashboard/file_explorer.html")

    # Get PR id
    if kwargs["pk"]:
        proj_id = int(kwargs["pk"])
    else:
        return HttpResponse(
            json.dumps("Missing project"), content_type="application/json"
        )

    proj_list = list(Project.objects.all().filter(id=proj_id).all())
    if not proj_list:
        return HttpResponse(
            json.dumps(f"Unknown project {proj_id}"), content_type="application/json"
        )

    # Get branch
    if request.GET.get("branch"):
        branch = request.GET.get("branch")
    else:
        return HttpResponse(
            json.dumps(f"Missing branch"), content_type="application/json"
        )

    # Get filename
    if request.GET.get("filename"):
        filename = request.GET.get("filename")
    else:
        return HttpResponse(
            json.dumps(f"Missing filename"), content_type="application/json"
        )

    proj_object = proj_list[0]
    proj_name = proj_object.name

    cmd = f"cd {settings.REPOS_DIR}/{proj_name} ; git checkout --force {branch}"
    try:
        import os
        os.system(cmd)
    except:
        assert False, f"Failure to checkout branch {cmd}"

    context = file_explorer_handler(proj_object, filename, branch)

    return HttpResponse(template.render(context, request))




#Checks documentation for a file.
#Computes developers committing to file in past.
#Checks if references an Issue 
# TODO: REMOVE THIS
def file_explorer_function(project_object, branch, filename):
    import os

    proj_name = project_object.name
    proj_id = project_object.id
    proj_info = project_object.info  #need to add this field

    cmd = f"cd {settings.REPOS_DIR}/{proj_name} ; git checkout --force {branch}"
    try:
        os.system(cmd)
    except:
        assert False, f"Failure to checkout branch {cmd}"

    #First check documentation present

    name, extension = os.path.splitext(filename)

    #check whitelist of allowable extensions. If no extension, check for allowed filenames.
    #If can't find, then assume file should not be checked for documentation.
    if (extension and extension in project_info["extensions"]) or (
            not extension and filename in project_info["filenames"]):
        with open(
            str(settings.REPOS_DIR) + "/" + proj_name + "/" + filename, "r") as f:
            lines = f.readlines()
            f.close()

        if proj_id == 32:
            documentation_issues = handle_hypre(project_object, [filename], lines)
        elif proj_id == 35:
            documentation_issues = handle_flash_x(project_object, [filename], lines)
        elif proj_id == 30:
            documentation_issues = handle_anl_test_repo(project_object, [filename], lines)
        # elif proj_id==38:
        # documentation_issues = handle_warpx(project_object, [filename], lines)
    else:
        documentation_issues = [dict(not_parsed= 'marked as ignore')]

            # finished with all files in PR

            # all_files:
            #   name, file_table
            #       {'signature_name': sig, 'signature_params':params, 'docstring': doc_info, 'result': all_issues}
            #       {'signature_name': sig, 'signature_params':params, 'docstring': doc_info, 'result': all_issues}
            #       ...
            #       where doc_info = (doc, doc_start, doc_end, fields, doc_params)
            #   status


    # Build developer table

    diffs = (
        Diff.objects.all()
        .filter(commit__project=project_object, file_path=filename)
        .all()
    )
    author_loc = {}

    for d in diffs:
        body = d.body
        author = d.commit.author
        loc_count = body.count("\n+") + body.count("\n-")
        if author in author_loc:
            author_loc[author] += loc_count
        else:
            author_loc[author] = loc_count

    # Get commits, authors for those (diffs)

    info = [(d.commit.datetime, d.commit.author, d.commit.hash) for d in diffs]
    commit_messages = [d.commit.message for d in diffs]
    commit_hashes = [d.commit.hash for d in diffs]

    tags = CommitTag.objects.all().filter(sha__in=commit_hashes)

    prs = list(
        set(PullRequest.objects.all().filter(commits__in=tags))
    )  # all prs that go with file commits

    pr_messages = [(pr.number, pr.url, pr.title, pr.description) for pr in prs]

    """
    print('pr_messages', '\n')
    for n, u, title, desc in pr_messages:
        print(n, ' ', u)
        print(title, ' ::: ', desc, '\n')
    """
    pr_comments = list(Comment.objects.all().filter(pr__in=prs))

    # print('comments','\n')

    issues = list(
        Issue.objects.all().filter(
            url__in=[
                pri.issue.url
                for pri in PullRequestIssue.objects.all().filter(pr__in=prs).all()
            ]
        )
    )

    # print('issues', issues, '\n')

    # issue_number = re.search(r'#\d+', pr.description)

    # closed_issue_list = list(Issue.objects.all().filter(url=project.source_url.replace('.git', '/issues/'+issue_number.group()[1:])))

    # issue_messsages = [(iss.title, iss.description) for iss in closed_issue_list]

    # issue_comments = list(Comment.objects.all().filter(issue__in=closed_issue_list))

    # print('issue comments', issue_comments)
    author_count = {}
    for date, author, link in info:
        if author in author_count:
            author_count[author] += 1
        else:
            author_count[author] = 1

    new_info = []
    authors = []
    for date, author, link in sorted(info, reverse=False):
        if author in authors:
            continue
        new_info.append((date, author, author_count[author], author_loc[author], link))
        authors.append(author)

    # see here for avoiding author alisases: https://towardsdatascience.com/string-matching-with-fuzzywuzzy-e982c61f8a84
    # combine counts for same author with different aliases.

    dev_table = [
        {
            "author": author,
            "number_commits": count,
            "lines": loc,
            "most_recent_commit": date,
            "commit_link": link,
        }
        for date, author, count, loc, link in new_info
    ]


    result = {
        "authors": dev_table,
        "authors_len": len(dev_table),
        "documentation": documentation_issues,
    }

    return result

# call with, e.g., 'anl_test_repo', 'folder1/arithmetic.py', 'sub'
def find_pytest_files(proj_name, file_path, function_name):
    # for full pytest dir setup see https://docs.pytest.org/en/7.1.x/explanation/goodpractices.html#conventions-for-python-test-discovery
    # here just assuming test files are in folder on file_path
    import os

    full_path = f"{settings.REPOS_DIR}/{proj_name}/{file_path}"
    found_asserts = []
    while True:
        head, tail = os.path.split(full_path)  # head now has containing dir for file
        if not head:
            break
        if tail == proj_name:
            break  # don't check above the repo
        all = os.listdir(head)  # files and folders
        # look for pytest files in dir
        for item in all:
            if os.path.isdir(item):
                continue  # skip over dirs
            name, extension = os.path.splitext(item)
            if "test" in name and extension == ".py":
                print(f"found: {head}, {name}")
                with open(head + "/" + name + extension, "r") as f:
                    lines = f.readlines()
                    f.close()
                i = 0
                while i < len(lines):
                    if lines[i].startswith("def test_"):
                        i += 1
                        while i < len(lines) and lines[i] != "\n":
                            if (
                                lines[i].strip().startswith("assert")
                                and f" {function_name}(" in lines[i]
                            ):
                                j = head.find(f"{proj_name}/")
                                path = head[j + len(proj_name) + 1 :]
                                found_asserts.append((path, name + extension, i))
                            i += 1
                    i += 1
        full_path = head
    return found_asserts


def get_callers(proj_id, sig_name, filename):
    project_callers = {
        30: {
            ("check_fum", "folder1/arithmetic.py"): [],
            ("concat", "folder2/strings.py"): [
                ("folder2/test_strings.py", "test_concat")
            ],
            ("count", "folder2/strings.py"): [],
            ("foo", "folder3/more_functions.py"): [("folder2/strings.py", "fum")],
            ("fum", "folder2/strings.py"): [("folder1/arithmetic.py", "check_fum")],
            ("list_sub", "folder1/arithmetic.py"): [],
            ("sub", "folder1/arithmetic.py"): [
                ("folder1/arithmetic.py", "list_sub"),
                ("folder1/test_arithmetic.py", "test_sub"),
            ],
            ("test_concat", "folder2/test_strings.py"): [],
            ("test_sub", "folder1/test_arithmetic.py"): [],
        }
    }
    if proj_id not in project_callers:
        print(f"No calling info for {proj_id}")
        return []
    if (sig_name, filename) not in project_callers[proj_id]:
        print(f"get_callers warning: did not find {(sig_name,filename)} in {proj_id}")
        return []
    return project_callers[proj_id][(sig_name, filename)]


#### Utility functions for parsing files and other things
def get_py_signature(lines, i):
    """!
    @param lines - a file as a list of strings
    @param i - the line to check within lines (0 origin)
    @return returns a triple of values: i is last line of signature (same as input if no signature); string name, empty if no signature found; list of params
    @details looks for line starting with "def ". If found then keeps moving through lines looking for closing colon, i.e., ":". The name and list of params returned has
     the def and colon removed. If the : is not found before reachining end of the file (lines) then the function will be ignored, i.e.,
     an empty string will be returned and the value of i will be one past the last line.
    @callgraph
    @callergraph
    """
    if not lines[i].startswith("def "):
        return i, "", []
    j = i
    while not lines[i].strip().endswith(":"):
        i += 1
        if i >= len(lines):
            print(f"get_signature warning: no colon found for {lines[j]}")
            return i, "", []
    raw = "".join([line for line in lines[j : i + 1]]).strip("\n")[4:]
    full = " ".join(raw.split())
    name = raw[: raw.find("(")].strip()
    args = raw[raw.find("(") + 1 : raw.find(")")].strip().split(",")
    return i, name, args


def get_py_doc_string(lines, i):
    # return doc, doc_start, doc_end, fields, doc_params, params_start, issues
    # skip over white space
    while lines[i].strip() == "":
        i += 1
    # check for triple quotes
    if lines[i].strip() not in ["'''", '"""']:
        return "", i, i, [], [], i, [["No docstring found", i]]  # did not find
    doc_start = i
    fields = []
    params = []
    params_start = i
    i += 1  # move beyond opening quotes
    issues = []
    numpy_fields = [
        "Parameters",
        "Returns",
        "Yields",
        "Raises",
        "See Also",
        "Notes",
        "Examples",
    ]
    while i < len(lines):
        if lines[i].strip() in ["'''", '"""']:
            doc_end = i
            break  # found end

        # check for field
        if (
            lines[i].strip() in numpy_fields
            and i + 1 < len(lines)
            and all([c == "-" for c in lines[i + 1].strip()])
        ):
            field = lines[i].strip()
            fields.append(field)
            i += 2  # skip over field and -------

            # check for Parameters field in particular
            if field == "Parameters":
                params_start = i - 2
                while i < len(lines):

                    if (
                        lines[i].strip() in numpy_fields
                        and i + 1 < len(lines)
                        and all([c == "-" for c in lines[i + 1].strip()])
                    ):
                        break  # found next field

                    if lines[i].strip() in ["'''", '"""']:
                        break  # found end

                    if ":" in lines[i]:
                        param = (
                            lines[i]
                            .strip()[: lines[i].find(":")]
                            .replace(":", "")
                            .strip()
                        )
                        params.append(param)
                        i += 1
                        continue

                    if lines[i].strip().isalnum() and lines[i].strip()[0].isalpha():
                        param = lines[i].strip()
                        params.append(param)
                        i += 1
                        continue

                    i += 1  # keep looking

                if i >= len(lines):
                    issues.append([f"Missing end to docstring", doc_start])
                    doc = lines[doc_start:]
                    return doc, doc_start, i - 1, fields, params, params_start, issues
                else:
                    continue  # broke out
        i += 1

    # end outer while
    if i >= len(lines):
        # fell out of while
        issues.append([f"Missing end to docstring", doc_start])
        doc_end = i

    doc = lines[doc_start : doc_end + 1]

    return doc, doc_start, doc_end, fields, params, params_start, issues


def check_param_match(sig_args, doc_args, doc_start):
    issue = []
    # check if 2 lists match up
    residue1 = [x for x in doc_args if x not in sig_args]  # more params than arg names?
    residue2 = [x for x in sig_args if x not in doc_args]  # more args than param names?
    if residue1:
        issue.append([f"Bogus doc arguments: {residue1}", doc_start])
    if residue2:
        issue.append([f"actual arguments missing doc arguments: {residue2}", doc_start])
    return issue


def check_mandatory(mandatories, fields, doc_start):
    residue1 = [
        x for x in mandatories if x not in fields
    ]  # more params than arg names?
    issues = [[f"mandatory fields missing: {residue1}", doc_start]] if residue1 else []
    return issues


def get_f90_robodoc_string_plus_sig(lines, i):
    # returns i, sig_name, sig_params, doc, doc_start, doc_end, fields, doc_params, params_start, issues
    assert lines[i].startswith("!!****if*") or lines[i].startswith(
        "!!****f*"
    )  # assumes lines[i] is beginning of docstring

    doc_start = i
    i += 1  # move past header
    # Look for fields
    fields = []
    params = []
    params_start = doc_start
    all_headers = [
        "NAME",
        "SYNOPSIS",
        "DESCRIPTION",
        "RESULT",
        "EXAMPLE",
        "SIDE EFFECTS",
        "NOTES",
        "SEE ALSO",
    ]
    while (
        not lines[i].startswith("!!**") and lines[i].startswith("!!") and i < len(lines)
    ):
        line = lines[i][2:].strip()
        if not line.isalpha() and not line.isupper():
            i += 1
            continue
        # found field
        fields.append(line)

        if line == "ARGUMENTS":
            params_start = i
            # found ARGUMENTS section - now get arguments

            i += 1  # move beyond ARGUMENTS line
            while i < len(lines):
                # check if ends by a non-comment line
                if not lines[i].startswith("!!"):
                    doc_end = i - 1
                    break

                # check if get to new section (so end of ARGUMENTS)
                line = lines[i][2:].strip()  # remove !! and padding
                if line in all_headers:
                    fields.append(line)
                    i += 1
                    break

                # check if - or : in line. If so, argument name is defined
                hyphen = line.find(" - ")
                index = (
                    line.find(" : ") if hyphen == -1 else hyphen
                )  # try colon if do not find hyphen

                # if not found, keep moving along
                if index == -1:
                    i += 1
                    continue

                # record arg name(s) found
                arg_name = line[:index].strip()
                for aname in arg_name.split(
                    ","
                ):  # can have more than one name preceding hyphen
                    params.append(aname.strip())
                i += 1
            # end inner while

            # figure out how dropped out of while loop collecting args
            if not lines[i].startswith("!!"):
                # ready to look for subroutine
                break

            if line in all_headers:
                # got to next section - keep going
                i += 1

            if i >= len(lines):
                # did not find closing of doc string
                return (
                    i,
                    "",
                    [],
                    lines[doc_start:i],
                    doc_start,
                    0,
                    fields,
                    params,
                    params_start,
                    [
                        [
                            f"No end found for docstring starting at {doc_start}",
                            doc_start,
                        ]
                    ],
                )
        else:
            i += 1  # Not ARGUMENTS - keep going
    # end outer while

    fields = list(set(fields))  # remove duplicates
    # found non comment line - assume ending
    doc_end = i - 1
    doc = lines[doc_start:i]

    # now look for subroutine
    while not lines[i].startswith("subroutine "):
        i += 1
        if i >= len(lines):
            # missing subroutine
            return (
                i,
                "",
                [],
                lines[doc_start:i],
                doc_start,
                0,
                fields,
                params,
                params_start,
                [[f"No subroutine for docstring starting at {doc_start}", doc_start]],
            )
    j = i
    while lines[i].find(")") == -1:
        i += 1
        if i >= len(lines):
            return (
                i,
                "",
                [],
                lines[doc_start:i],
                doc_start,
                doc_end,
                fields,
                params,
                params_start,
                [[f"No ) for for subroutine starting at {j}", j]],
            )

    # looks good!
    raw_sig = " ".join(lines[j : i + 1]).strip("\n").replace("&", " ")[10:]
    sig_name = raw_sig[: raw_sig.find("(")].strip()
    sig_params = raw_sig[raw_sig.find("(") + 1 : raw_sig.find(")")].strip().split(",")
    sig_params = [sp.strip() for sp in sig_params]

    return (
        i + 1,
        sig_name,
        sig_params,
        doc,
        doc_start,
        doc_end,
        fields,
        params,
        params_start,
        [],
    )


"""
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
 OR Python

## @package pyexample
#  Documentation for this module.
#
#  More details.
 
## Documentation for a function.
#
#  More details.
def func():
    pass
"""


def get_doxygen_string_plus_sig(lines, i, language):
    # returns i, sig_name, sig_params, doc, doc_start, doc_end, fields, doc_params, params_start, issues

    doc_start = i
    fields = []
    params = []
    params_start = doc_start
    language_mapping = {"F90": {"comment": "!"}, "py": {"comment": "#"}}
    comment_char = language_mapping[language]["comment"]
    while (lines[i].startswith(comment_char) or lines[i].strip() == "") and i < len(
        lines
    ):

        if lines[i].strip() == "":
            i += 1
            continue

        j = lines[i].find("@")
        if j == -1:
            i += 1
            continue

        # found field
        raw_field = lines[i][j + 1 :]
        k = raw_field.find(" ")  # space before name
        field = raw_field[:k].strip()
        fields.append(field)

        if field == "param":
            raw_name = raw_field[k + 1 :]
            params.append(raw_name[: raw_name.find(" ")])

    # either found sub or run out of lines
    if i >= len(lines):
        return (
            i,
            "",
            [],
            lines[doc_start:i],
            doc_start,
            0,
            list(set(fields)),
            params,
            params_start,
            [[f"No subroutine for docstring starting at {doc_start}", doc_start]],
        )
    doc_end = i - 1
    doc = lines[doc_start:i]

    return (
        i + 1,
        sig_name,
        sig_params,
        doc,
        doc_start,
        doc_end,
        list(set(fields)),
        params,
        params_start,
        [],
    )


def parse_f90_subroutine(lines, i):
    # now look for subroutine
    while not lines[i].startswith("subroutine "):
        i += 1
        if i >= len(lines):
            # missing subroutine
            return (
                i,
                "",
                [],
                lines[doc_start:i],
                doc_start,
                0,
                list(set(fields)),
                params,
                params_start,
                [[f"No subroutine for docstring starting at {doc_start}", doc_start]],
            )
    j = i
    while lines[i].find(")") == -1:
        i += 1
        if i >= len(lines):
            return (
                i,
                "",
                [],
                lines[doc_start:i],
                doc_start,
                doc_end,
                list(set(fields)),
                params,
                params_start,
                [[f"No ) for for subroutine starting at {j}", j]],
            )

    # looks good!
    raw_sig = " ".join(lines[j : i + 1]).strip("\n").replace("&", " ")[10:]
    sig_name = raw_sig[: raw_sig.find("(")].strip()
    sig_params = raw_sig[raw_sig.find("(") + 1 : raw_sig.find(")")].strip().split(",")


def write_pr_info_to_file(proj_id):
    return []


def comute_pr_file_intersection(proj_object, filenames):
    proj_id = proj_object.id
    all_prs = []
    for file in filenames:
        prs = find_prs_with_file(proj_id, file)
        all_prs += prs  # concat

    pr_info = []
    for pr in list(set(all_prs)):
        files = find_files_with_pr(proj_object, pr)
        file_info = []
        for file in files:
            if file in filenames:
                file_info.append((file, True))
            else:
                file_info.append((file, False))
        assert any([b for f, b in file_info])
        pr_info.append((pr.number, file_info))

    return pr_info


def find_prs_with_file(proj_id, filename):

    diffs = Diff.objects.all().filter(commit__project=proj_id, file_path=filename).all()
    commit_hashes = [d.commit.hash for d in diffs]
    tags = CommitTag.objects.all().filter(sha__in=commit_hashes)
    prs = list(
        set(PullRequest.objects.all().filter(commits__in=tags))
    )  # all prs that go with file commits

    return prs


def find_files_with_pr(proj_object, pr_object):

    proj_name = proj_object.name  # get project name
    proj_id = proj_object.id

    # get set up on right feature branch
    commits_list = list(
        Commit.objects.all().filter(
            hash__in=[committag.sha for committag in pr_object.commits.all()]
        )
    )
    assert commits_list, f"No commits found for {proj_id}"

    # get all files in PR
    diffs = list(Diff.objects.all().filter(commit__in=[c for c in commits_list]))
    filenames = [d.file_path for d in diffs]
    # Get just unique filenames
    filenames_set = set(filenames)
    filenames = list(filenames_set)

    return filenames
