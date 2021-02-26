import pandas as pd 
import MySQLdb 
import datetime 
import calendar 
from dateutil import parser 

class Fetcher:
    def __init__(self, project_name):
        self.db = MySQLdb.connect(host='sansa.cs.uoregon.edu', port=3331, user='ideas_user', passwd='cabbage', db='ideas_db', charset='utf8mb4')
        self.cursor = self.db.cursor() 
        commit_query = '''select c.id as commit_id, c.hash as sha, c.datetime as datetime, a.username as author, c.message as message, d.file_path, d.body 
        from commit c join author a on(c.author_id = a.id) join project p on(c.project_id = p.id) join diff d on(c.id = d.commit_id)
        where p.name = %s'''
        comm_ans                 = self.cursor.execute(commit_query, (project_name, ))
        self.commit_data         = pd.DataFrame(self.cursor.fetchall()) 
        self.commit_data.columns = ['index', 'sha', 'datetime', 'author', 'message', 'filepath', 'diff']  
        self.commit_data.drop(columns=['index'])
        temp_d = self.commit_data['datetime'].map(lambda x: x.date())
        self.commit_data[['year', 'month', 'day', 'doy', 'dow']] = pd.DataFrame(
            list(
                temp_d.map(
                    lambda x : [x.year, x.month, x.day, x.timetuple().tm_yday, calendar.day_name[x.weekday()]]
                )
            )
            , index = self.commit_data.index 
        )


    def close_session(self): 
        self.cursor.close() 
        self.db.close()