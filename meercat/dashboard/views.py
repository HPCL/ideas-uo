import datetime
import json

import configparser

from django.http import HttpResponse
from django.template import loader
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render

import pandas as pd

import re

import sys
sys.path.insert(1, '/shared/soft/ideas_db/ideas-uo/src')
sys.path.insert(1, '../src')
from gitutils.github_api import GitHubAPIClient

from database.models import Project, ProjectRole, Commit, Diff, Issue, PullRequest, PullRequestIssue, Comment, EventPayload

import subprocess
import os, warnings
warnings.filterwarnings('ignore')
from patterns.visualizer import Visualizer

def not_authorized(request):
    return render(request, 'dashboard/not_authorized.html')


# Index view - should list all projects
@login_required
def index(request):
    print("INDEX")

    pid = 30
    if request.GET.get('pid'):
        pid = int(request.GET.get('pid'))

    if request.user.is_staff:
        return redirect('staff_index')

    devProjects = getUserProjectsByRole(request.user, 'DEV') 
    devProjects = sorted(devProjects, key=lambda d: d.name, reverse=False)
    
    PMProjects = getUserProjectsByRole(request.user, 'PM')
    PMProjects = sorted(PMProjects, key=lambda d: d.name, reverse=False)
    
    context = {'devProjects': devProjects, 'PMProjects': PMProjects}
 
    return render(request, 'dashboard/index.html', context)

@login_required
def staff_index(request):
    print("STAFF INDEX")

    pid = 30
    if request.GET.get('pid'):
        pid = int(request.GET.get('pid'))

    projects = list(Project.objects.all())
    projects = sorted(projects, key=lambda d: d.name, reverse=False)

    return render(request, 'dashboard/staff_index.html', {'projects': projects})

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

    prs = list(PullRequest.objects.all().filter(project=project).all())
    prs = sorted(prs, key=lambda d: d.number, reverse=True)

    commits = list(Commit.objects.all().filter(project=project).all())
    commits = sorted(commits, key=lambda d: d.datetime, reverse=True)

    issues = list(Issue.objects.all().filter(project=project).all())
    issues = sorted(issues, key=lambda d: d.number, reverse=True)


    pythonloc = countlinespython(r'../'+project.name)
    fortranloc = countlinesfortran(r'../'+project.name)
    cloc = countlinesc(r'../'+project.name)
    files = countfiles(r'../'+project.name)


    #TODO: should be able to remove this
    with open('../anl_test_repo/folder1/arithmetic.py', 'r') as f:
        lines = f.readlines()
        f.close()


    context = {'project':project,'prs':prs, 'commits':commits, 'issues':issues, 'pythonloc':pythonloc, 'fortranloc':fortranloc, 'cloc':cloc, 'files':files, 'file':''.join(lines).replace('\\','\\\\').replace('\n', '\\n').replace('\'','\\\'')}

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

    commits = list(Commit.objects.all().filter(hash__in=[committag.sha for committag in pr.commits.all()]))

    issues = list(Issue.objects.all().filter(url__in=[pri.issue.url for pri in PullRequestIssue.objects.all().filter(pr=pr).all()]))


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

    


    context = {'pr':pr, 'commits':commits, 'issues':issues, 'filenames':filenames, 'events':events, 'comments':comments,'closed_issue':closed_issue}

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

    cmd = f'cd .. ; export PYTHONPATH=. ; nohup python3 ./src/gitutils/update_database.py {username} {password} 30'
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
    commits = list(Commit.objects.all().filter(hash__in=[committag.sha for committag in pr.commits.all()]))

    print("Commits: "+str(len(commits)))

    diffs = list(Diff.objects.all().filter(commit__in=[c for c in commits]))
    filenames = [d.file_path for d in diffs]
    #Get just unique filenames
    filenames_set = set(filenames)
    filenames = list(filenames_set)

    #Now find all commits and diffs for the changed files in the past 60 days
    #date = datetime.datetime.now() - datetime.timedelta(days=60)
    date = pr.created_at - datetime.timedelta(days=60)
    diffcommits = []

    filtereddiffs = Diff.objects.all().filter(commit__project=pr.project, commit__datetime__gte=date, commit__datetime__lte=pr.created_at)
    for filename in filenames:
        diffcommits.append( {'filename': filename, 'commits':[{'commit':d.commit.hash, 'diff':d.body} for d in filtereddiffs.filter(file_path=filename)]} )

    prcommits = []
    for commit in commits:
        prcommits.append({'hash':commit.hash})
    
    resultdata = {
        'diffcommits':diffcommits,
        'prcommits':prcommits,
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


    #with open('../ideas-uo/anl_test_repo/folder1/arithmetic.py', 'r') as f:
    with open('../'+pr.project.name+'/'+filename, 'r') as f:
        lines = f.readlines()
        f.close()


    resultdata = {
        'filecontents':''.join(lines),
    }

    return HttpResponse(
        json.dumps(resultdata),
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
                    newlines = f.readlines()
                    newlines = len(newlines)
                    lines += newlines

    for thing in os.listdir(start):
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
        if not thing.startswith('.git'):
            thing = os.path.join(start, thing)
            if os.path.isdir(thing):
                files = countfiles(thing, files, header=False, begin_start=start)

    return files

def getUserProjectsByRole(user, role):
    projectRoles = list(ProjectRole.objects.filter(user__id=user.id, role=role))
    projectIds = [role.project.id for role in projectRoles]
    projects = [Project.objects.get(id=projectId) for projectId in projectIds]

    return projects


def hasAccessToProject(user, project_id):
    if user.is_staff:
        return True

    return ProjectRole.objects.filter(user__id=user.id, project=project_id).exists()

def hasAccessToPR(user, pr_id):
    if user.is_staff:
        return True

    project_id = PullRequest.objects.get(id=pr_id).project.id
    return ProjectRole.objects.filter(user__id=user.id, project=project_id).exists()