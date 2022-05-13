import datetime
import json

import configparser

from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from django.conf import settings

import pandas as pd

import re

import sys
sys.path.insert(1, '/shared/soft/ideas_db/ideas-uo/src/gitutils')
from github_api import GitHubAPIClient

from database.models import Author, Project, ProjectAuthor, Commit, Diff, Issue, PullRequest, PullRequestIssue, IssueTag, Comment, EventPayload

import subprocess
import os, getpass, warnings
warnings.filterwarnings('ignore')
from patterns.visualizer import Visualizer

# Create your views here.

# Index view - should list all projects
def index(request):
    print("INDEX")
    template = loader.get_template('dashboard/index.html')

    pid = 30
    if request.GET.get('pid'):
        pid = int(request.GET.get('pid'))

    projects = list(Project.objects.all())
    projects = sorted(projects, key=lambda d: d.name, reverse=False)

    context = {'projects':projects}

    return HttpResponse(template.render(context, request))


# Project view - should list general project info
def project(request, *args, **kwargs):
    print("PROJECT")
    print( kwargs['pk'] )
    template = loader.get_template('dashboard/project.html')

    pid = 30
    if kwargs['pk']:
        pid = int(kwargs['pk'])

    project = list(Project.objects.all().filter(id=pid).all())[0]

    prs = list(PullRequest.objects.all().filter(project=project).all())
    prs = sorted(prs, key=lambda d: d.number, reverse=True)

    commits = list(Commit.objects.all().filter(project=project).all())
    commits = sorted(commits, key=lambda d: d.datetime, reverse=True)

    issues = list(Issue.objects.all().filter(project=project).all())
    issues = sorted(issues, key=lambda d: d.number, reverse=True)


    loc = countlines(r'../ideas-uo/'+project.name)
    files = countfiles(r'../ideas-uo/'+project.name)

    '''for thing in os.listdir(start):
        thing = os.path.join(start, thing)
        if os.path.isfile(thing):
            if thing.endswith('.py'):
                with open(thing, 'r') as f:'''

    #config.read('../ideas-uo/credentials.ini')

    with open('../ideas-uo/anl_test_repo/folder1/arithmetic.py', 'r') as f:
        lines = f.readlines()
        f.close()



    context = {'project':project,'prs':prs, 'commits':commits, 'issues':issues, 'loc':loc, 'files':files, 'file':''.join(lines).replace('\\','\\\\').replace('\n', '\\n').replace('\'','\\\'')}

    return HttpResponse(template.render(context, request))


# PR list view - list all the PRs for project
def prlist(request, *args, **kwargs):
    print("PRLIST")
    template = loader.get_template('dashboard/prlist.html')

    pid = 30
    #if request.GET.get('pid'):
    #    pid = int(request.GET.get('pid'))
    if kwargs['pk']:
        pid = int(kwargs['pk'])

    project = list(Project.objects.all().filter(id=pid).all())[0]

    prs = list(PullRequest.objects.all().filter(project=project).all())
    prs = sorted(prs, key=lambda d: d.number, reverse=True)

    context = {'project':project,'prs':prs}

    return HttpResponse(template.render(context, request))


# Pull Request view - show the assistant for specific PR
def pr(request, *args, **kwargs):
    print("PR")
    template = loader.get_template('dashboard/pr.html')

    prid = 2250
    #if request.GET.get('pr'):
    #    prid = int(request.GET.get('pr'))
    if kwargs['pk']:
        prid = int(kwargs['pk'])

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    commits = list(Commit.objects.all().filter(hash__in=[committag.sha for committag in pr.commits.all()]))

    issues = list(Issue.objects.all().filter(url__in=[pri.issue.url for pri in PullRequestIssue.objects.all().filter(pr=pr).all()]))


    #Find any issue that this PR closed
    closed_issue = None
    issue_number = re.search(r'#\d+', pr.description)
    if issue_number:
        print(issue_number.group())
        print( pr.project.source_url.replace('.git', '/issues/'+issue_number.group()[1:]) )
        closed_issue = list(Issue.objects.all().filter(url=pr.project.source_url.replace('.git', '/issues/'+issue_number.group()[1:])))[0]


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


# Refresh the GIT and GitHub data for a project (INTENTIONALLY ONLY WORKS FOR PROJECT ID 30)
def refreshProject(request):
    print("REFRESH")

    pid = 30
    if request.GET.get('pid'):
        pid = int(request.GET.get('pid'))

    project = list(Project.objects.all().filter(id=pid).all())[0]

    username = settings.DATABASES['default']['USER']
    password = settings.DATABASES['default']['PASSWORD']

    cmd = f'cd ../ideas-uo ; export PYTHONPATH=. ; nohup python3 ./src/gitutils/update_database.py {username} {password} 30'
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
def createPatch(request):
    print("CREATE PATCH")

    prid = 2250
    if request.POST.get('pr'):
        prid = int(request.POST.get('pr'))

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
    with open('../ideas-uo/'+pr.project.name+'/'+filename, 'w') as f:
        f.write(request.POST.get('filecontents'))
        f.close()
    
    #cmd = f'cd ../ideas-uo/anl_test_repo ; git diff folder1/arithmetic.py > arithmetic.py.patch'
    cmd = f'cd ../ideas-uo/'+pr.project.name+' ; git diff '+filename+' > '+filename[filename.rindex('/')+1:]+'.patch'
    os.system(cmd)
    #result = subprocess.check_output(cmd, shell=True)

    #with open('../ideas-uo/anl_test_repo/arithmetic.py.patch', 'r') as f:
    with open('../ideas-uo/'+pr.project.name+'/'+filename[filename.rindex('/')+1:]+'.patch', 'r') as f:
        lines = f.readlines()
        f.close()
    os.remove('../ideas-uo/'+pr.project.name+'/'+filename[filename.rindex('/')+1:]+'.patch')    

    #cmd = f'cd ../ideas-uo/anl_test_repo ; git checkout -- folder1/arithmetic.py'
    cmd = f'cd ../ideas-uo/'+pr.project.name+' ; git checkout -- '+filename
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


# Run some code quality checks and return results
def codeCheck(request):
    print("CODE CHECK")

    prid = 2250
    if request.POST.get('pr'):
        prid = int(request.POST.get('pr'))

    project = list(Project.objects.all().filter(id=pid).all())[0]

    filename = 'folder1/arithmetic.py'
    if request.POST.get('filename'):
        filename = request.POST.get('filename')


    #Run a linter on give filename in given project

    #Also run FLASH5 codecheck script?

    #cmd = f'cd ../ideas-uo/'+pr.project.name+' ; git diff '+filename+' > '+filename[filename.rindex('/')+1:]+'.patch'
    #os.system(cmd)
    #result = subprocess.check_output(cmd, shell=True)


    
    resultdata = {
        'status':'success'
        'linter':'test1'
        'codecheck':'test2'
    }

    return HttpResponse(
        json.dumps(resultdata),
        content_type='application/json'
    )


# Retrieves commit data for a specific PR
def diffCommitData(request):
    print("Diff Commit DATA")

    print(request.POST.get('pr'))

    prid = 2250
    if request.POST.get('pr'):
        prid = int(request.POST.get('pr'))

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    #Find all changed files related to the PR by getting all diffs from all commits in PR    
    commits = list(Commit.objects.all().filter(hash__in=[committag.sha for committag in pr.commits.all()]))

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
        'prcommits':prcommits
    }

    return HttpResponse(
        json.dumps(resultdata),
        content_type='application/json'
    )


def getFile(request):

    print("Get File DATA")

    #print(request.POST.get('pr'))

    prid = 2250
    if request.POST.get('pr'):
        prid = int(request.POST.get('pr'))

    filename = 'folder1/arithmetic.py'
    if request.POST.get('filename'):
        filename = request.POST.get('filename')

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]


    #with open('../ideas-uo/anl_test_repo/folder1/arithmetic.py', 'r') as f:
    with open('../ideas-uo/'+pr.project.name+'/'+filename, 'r') as f:
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
# Works just fro FLASH5 at the moment, but can be made to be more generic.
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

    
    

    Visualizer()
    vis = Visualizer(project_name='FLASH5')
    vis.get_data()

    #removed = vis.remove_external()
    removed = vis.remove_files(filenames)

    vis.hide_names = False

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
    df = vis.plot_top_N_heatmap(10, locc_metric='change-size-cos')

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
def branches(request):
    print("BRANCHES")
    template = loader.get_template('dashboard/branches.html')
    context = {}

    return HttpResponse(template.render(context, request))


# Returns branch data for anl_test_repo
# If this is still useful, need to make more generic
def branchData(request):
    print("BRANCHES DATA")

    config = configparser.ConfigParser()
    config.read('../ideas-uo/credentials.ini')

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

    branches = branches.drop(['main', 'staged', 'development']).fillna('None')

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