#!/usr/bin/env python3

import os
import sys

import MySQLdb
from db_interface import *

HOST = 'sansa.cs.uoregon.edu'
USERNAME = '' # edit this
PASSWORD = '' # edit this
PORT = 3331
DATABASE = 'ideas_db'
LOG_DIR = '/shared/soft/ideas_db/logs/'

if len(sys.argv)>2: 
    USERNAME=sys.argv[1]
    PASSWORD=sys.argv[2]

def update():
    db = MySQLdb.connect(host=HOST,
                         port=PORT,
                         user=USERNAME,
                         password=PASSWORD,
                         database=DATABASE,
                         use_unicode=True,
                         charset='utf8mb4')
    cursor = db.cursor()
    query = 'select name, source_url from project'
    cursor.execute(query)
    project_info = cursor.fetchall()
    cursor.close()
    db.close()

    os.makedirs(LOG_DIR, exist_ok=True)

    for name, source_url in project_info:
        # Add git info
        git_log_path = os.path.join(LOG_DIR, f'{name}_git.log')
        git_command = f'nohup python3 -m src.gitutils.db_interface --username {USERNAME} --password {PASSWORD} --add_project {source_url} > {git_log_path} 2>&1;'
        print(git_command)
        #os.system(git_command)
        # Add prs
        pr_log_path = os.path.join(LOG_DIR, f'{name}_pr.log')
        pr_command = f'nohup python3 -m src.gitutils.db_interface --username {USERNAME} --password {PASSWORD} --add_prs {source_url} > {pr_log_path} 2>&1 &'
        #os.system(pr_command)
        # Add issues
        issue_log_path = os.path.join(LOG_DIR, f'{name}_issue.log')
        issue_command = f'nohup python3 -m src.gitutils.db_interface --username {USERNAME} --password {PASSWORD} --add_issues {source_url} > {issue_log_path} 2>&1 &'
        #os.system(issue_command)
        # Add events
        event_log_path = os.path.join(LOG_DIR, f'{name}_event.log')
        event_command = f'nohup python3 -m src.gitutils.db_interface --username {USERNAME} --password {PASSWORD} --add_events {source_url} > {event_log_path} 2>&1 &'
        #os.system(event_command)
        
if __name__ == '__main__':
    update()
