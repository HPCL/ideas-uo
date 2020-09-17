import os, sys, subprocess
import argparse, getpass
import requests
from bs4 import BeautifulSoup
import gzip
import mailbox

class RemoteCommand(object):

    def __init__(self):
        #self.tmpdir = dir

        #Prep for gitHub API
        '''parser = argparse.ArgumentParser()
        parser.add_argument('-user','--username',
                            help='The github username', type=str)
        parser.add_argument('-pass','--password', 
                            help='The github password', type=str)
        args = parser.parse_args()
        
        self.GITHUB_USER = args.username'''

        print("Enter GitHub credentials")
        self.GITHUB_USER = input("Username: ")
        self.GITHUB_PASSWORD = getpass.getpass(prompt='Password: ', stream=None)

        if not self.GITHUB_USER or self.GITHUB_PASSWORD:
            'You must specify the username and password to access the issues of the desired github repository.'
            #parser.print_usage(sys.stderr)
        pass


    #Get all of the issues for a repo
    def getIssues(self, reponame):
        
        print('Checking: ' + reponame)
        
        page = 1
        result = [];

        PULLS_FOR_REPO_URL = 'https://api.github.com/repos/%s/issues' % reponame
        ARGS = '?state=all&page=1'
        AUTH = (self.GITHUB_USER, self.GITHUB_PASSWORD)
        print('Link accessing: ', PULLS_FOR_REPO_URL + ARGS)
        response = requests.get(PULLS_FOR_REPO_URL + ARGS, auth=AUTH)
        print('Request successful...... ', response)
        print('Request length...... ', str(len(response.json())))
        if not response.status_code == 200:
            raise Exception(response.status_code)

        #if there is a result add it 
        result.extend(response.json())


        while len(response.json()) > 0:
            page = page+1
            ARGS = '?state=all&page='+str(page)
            print('Link accessing: ', PULLS_FOR_REPO_URL + ARGS)
            response = requests.get(PULLS_FOR_REPO_URL + ARGS, auth=AUTH)
            #print('Request successful...... ', response)
            #print('Request length...... ', str(len(response.json())))
            
            #if there is a result add it 
            result.extend(response.json())

        #Need to iterate over all pages (link)
        #&page=1
        #for issue in response.json():
        #    print(issue)

        print('RESULTS '+str(len(result)))

        #need to return a dict of all the issues eventually
        return result


    #Get all of the comments for a repo
    def getComments(self, reponame):
        
        print('Checking: ' + reponame)
        
        page = 1
        result = [];

        PULLS_FOR_REPO_URL = 'https://api.github.com/repos/%s/issues/comments' % reponame
        ARGS = '?state=all&page=1&per_page=100'
        AUTH = (self.GITHUB_USER, self.GITHUB_PASSWORD)
        print('Link accessing: ', PULLS_FOR_REPO_URL + ARGS)
        response = requests.get(PULLS_FOR_REPO_URL + ARGS, auth=AUTH)
        print('Request successful...... ', response)
        print('Request length...... ', str(len(response.json())))
        if not response.status_code == 200:
            raise Exception(response.status_code)

        #if there is a result add it 
        result.extend(response.json())


        while len(response.json()) > 0:
            page = page+1
            ARGS = '?state=all&page='+str(page)+'&per_page=100'
            print('Link accessing: ', PULLS_FOR_REPO_URL + ARGS)
            response = requests.get(PULLS_FOR_REPO_URL + ARGS, auth=AUTH)
            #print('Request successful...... ', response)
            print('Request length...... ', str(len(response.json())))
            
            #if there is a result add it 
            result.extend(response.json())

        print('RESULTS '+str(len(result)))

        #need to return a dict of all the comments
        return result


    #Get all of the comments for a specific issue
    def getCommentsForIssue(self, reponame, issueNumber):
        
        print('Checking: ' + reponame)
        
        page = 1
        result = [];

        PULLS_FOR_REPO_URL = 'https://api.github.com/repos/%s/issues/%s/comments' % (reponame,str(issueNumber))
        ARGS = '?state=all&page=1&per_page=100'
        AUTH = (self.GITHUB_USER, self.GITHUB_PASSWORD)
        print('Link accessing: ', PULLS_FOR_REPO_URL + ARGS)
        response = requests.get(PULLS_FOR_REPO_URL + ARGS, auth=AUTH)
        print('Request successful...... ', response)
        print('Request length...... ', str(len(response.json())))
        if not response.status_code == 200:
            raise Exception(response.status_code)

        #if there is a result add it 
        result.extend(response.json())


        while len(response.json()) > 0:
            page = page+1
            ARGS = '?state=all&page='+str(page)+'&per_page=100'
            print('Link accessing: ', PULLS_FOR_REPO_URL + ARGS)
            response = requests.get(PULLS_FOR_REPO_URL + ARGS, auth=AUTH)
            #print('Request successful...... ', response)
            print('Request length...... ', str(len(response.json())))
            
            #if there is a result add it 
            result.extend(response.json())

        print('RESULTS '+str(len(result)))

        #need to return a dict of all the comments
        return result



    def getPetscMail(self):

        print('Downloading mail for petsc...')

        result = [];

        url = "https://lists.mcs.anl.gov/pipermail/petsc-users/"
        response = requests.get(url)
        soup = BeautifulSoup(response.content)
        for link in soup.find_all('a'):

            if "txt.gz" in link.get('href'):
                
                print(link.get('href'))
                response2 = requests.get(url + link.get('href'))
                open('mail.txt.gz', 'wb').write(response2.content)

                file=gzip.open('mail.txt.gz','rb')
                file_content=file.read()
                open('archive.mbox', 'wb').write(file_content)

                for message in mailbox.mbox('archive.mbox'):
                    result.append(message)

                os.remove('mail.txt.gz')
                os.remove('archive.mbox')

        print("Total emails: "+ str(len(result)))

        return result



#Helper Functions

def getYears(repodir):
    os.chdir(repodir)
    retcode, out, err = Command.Command('git log | grep Date | tail -1').run()
    if not out.strip(): repoError(repodir,err)
    startyear = out.split()[-2]
    retcode, out, err = Command.Command('git log | grep Date | head -1').run()
    if not out.strip(): repoError(repodir,err)
    endyear = out.split()[-2]
                    
    changesets = []
    for year in range(int(startyear),int(endyear)+1):
        retcode, out, err = Command.Command(getGitCmd(year)).run()
        if out.strip(): changesets.append(out.strip())

    if not changesets:
        for year in range(int(endyear),2000,-1):
            retcode, out, err = Command.Command(getGitCmd(year)).run()
            if out.strip(): changesets.append(out.strip())
    return changesets

def getGitCmd(year):
      return "git log --since '1 January %d' --before '31 December %d' | grep -e '^commit' | tail -1 | cut -d ' ' -f 2" % (year,year)


