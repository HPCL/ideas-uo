#!/usr/bin/env python3

import os

import MySQLdb

HOST = 'sansa.cs.uoregon.edu'
USERNAME = '' # edit this
PASSWORD = '' # edit this
PORT = 3331
DATABASE = 'ideas_db'
LOG_DIR = '/shared/soft/ideas_db/logs/'

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
    db.close()

    #os.makedirs(LOG_DIR, exist_ok=True)

    for name, source_url in project_info:
        log_path = os.path.join(LOG_DIR, f'{name}.log')
        command = f'nohup python3 -m src.gitutils.db_interface --username {USERNAME} --password {PASSWORD} --update {source_url} > {log_path} 2>&1 &'

        os.system(command)

if __name__ == '__main__':
    update()
