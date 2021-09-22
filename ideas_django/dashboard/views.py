import datetime
import json

import configparser

from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader

import pandas as pd

import sys
sys.path.insert(1, '/shared/soft/ideas_db/ideas-uo/src/gitutils')
from github_api import GitHubAPIClient

from database.models import Author, Project, ProjectAuthor, Commit, Diff, Issue, PullRequest, PullRequestIssue, IssueTag, Comment, EventPayload

import os, getpass, warnings
warnings.filterwarnings('ignore')
from patterns.visualizer import Visualizer

# Create your views here.

def index(request):
    print("INDEX")
    template = loader.get_template('dashboard/index.html')

    prid = 2250
    if request.GET.get('pr'):
        prid = int(request.GET.get('pr'))

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    commits = list(Commit.objects.all().filter(hash__in=[committag.sha for committag in pr.commits.all()]))

    issues = list(Issue.objects.all().filter(url__in=[pri.issue.url for pri in PullRequestIssue.objects.all().filter(pr=pr).all()]))

    diffs = list(Diff.objects.all().filter(commit__in=[c for c in commits]))
    filenames = [d.file_path for d in diffs]
    #get just unique filenames
    filenames_set = set(filenames)
    filenames = list(filenames_set)

    events = list(EventPayload.objects.all().filter(pr_number=pr.number))

    
    

    #Get all the commits for each file
    #Moved this to a seperate json call because it is slow
    date = datetime.datetime.now() - datetime.timedelta(days=60)
    diffcommits = {}
    #filtereddiffs = Diff.objects.all().filter(commit__project=pr.project, commit__datetime__gte=date)
    #for filename in filenames:
    #    diffcommits[filename] = [d.commit.hash for d in filtereddiffs.filter(file_path=filename)]

    


    context = {'pr':pr, 'commits':commits, 'issues':issues, 'filenames':filenames, 'events':events, 'diffcommits':diffcommits}

    return HttpResponse(template.render(context, request))



def diffCommitData(request):
    print("Diff Commit DATA")

    prid = 2250
    if request.GET.get('pr'):
        prid = int(request.GET.get('pr'))

    pr = list(PullRequest.objects.all().filter(id=prid).all())[0]

    commits = list(Commit.objects.all().filter(hash__in=[committag.sha for committag in pr.commits.all()]))
    diffs = list(Diff.objects.all().filter(commit__in=[c for c in commits]))
    filenames = [d.file_path for d in diffs]
    #get just unique filenames
    filenames_set = set(filenames)
    filenames = list(filenames_set)

    date = datetime.datetime.now() - datetime.timedelta(days=60)
    diffcommits = []
    filtereddiffs = Diff.objects.all().filter(commit__project=pr.project, commit__datetime__gte=date)
    for filename in filenames:
        diffcommits.append( {'filename': filename, 'commits':[d.commit.hash for d in filtereddiffs.filter(file_path=filename)]} )

    
    
    resultdata = {
        'diffcommits':diffcommits
    }

    return HttpResponse(
        json.dumps(resultdata),
        content_type='application/json'
    )



def patternGraph1(request):
    print("PATTERN DATA")

    print( request.GET.get('start') )

    startdate = request.GET.get('start')
    enddate = request.GET.get('end')

    if startdate: 
        startdate = datetime.datetime.strptime(startdate, '%Y-%m-%d')
    if enddate: 
        enddate = datetime.datetime.strptime(enddate, '%Y-%m-%d')

    #vis.select_month_range()
    #vis.select_year_range()

    Visualizer()
    vis = Visualizer(project_name='spack')
    vis.get_data()

    removed = vis.remove_external()

    vis.hide_names = False

    df = vis.plot_zone_heatmap(agg='mean')
    #print(df)

    resultdata = {
        'filename': 'spack-zone-change-size-cos-map-Entire_project-mean.png',
    }

    return HttpResponse(
    	json.dumps(resultdata),
    	content_type='application/json'
    )



def branches(request):
    print("BRANCHES")
    template = loader.get_template('dashboard/branches.html')
    context = {}

    return HttpResponse(template.render(context, request))



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
