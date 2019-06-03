import os, sys, subprocess
import Command

class GitCommand(object):

    def __init__(self, dir):
        self.tmpdir = dir

    #Clone a repo
    def cloneRepo(self, url):
        
        os.chdir(self.tmpdir) 

        #Check if already exists in tmp folder
        os.system('git clone ' + url)

        return True

    #Get all the versions of a repo
    def getRepoVersions(self, reponame):
        
        os.chdir(self.tmpdir)   

        currdir = os.getcwd()
        tmpdir = os.path.join(currdir,'tmp')

        filepath=os.path.join(reponame,'Releases.txt')
        if not os.path.exists(filepath): 
            return '',getYears(reponame) 
        return 'tags/',[x.strip() for x in open(filepath,'r').readlines()]

    #Get all the versions of a repo
    def getRepoCommitData(self, reponame):

        prefix,versions = self.getRepoVersions(reponame)

        commits = {}

        for version in versions:   

            #checkout the version
            print('git checkout %s%s' % (prefix,version))
            retcode, out, err = Command.Command('git checkout %s%s' % (prefix,version)).run(dryrun=False)
            print(out)
            
        
            #git log -p # this will list all commits and the code additions in addition to dates and messages.
            retcode, out, err = Command.Command('git log -p').run()
            lines = iter(out.splitlines())

            current_author = ''
            for line in lines:

                #If the line is an author, then start to piece together the commit   
                if line.startswith('Author: '):
                    current_author = line[8:len(line)]

                    #track the number of commits for this author
                    if current_author in commits:
                        commits[current_author]['total_commits'] += 1
                    else:    
                        commits[current_author] = {'total_commits':1, 'commits':[]}

                    #get the commit date
                    rawdate = next(lines)
                    date = rawdate[8:len(rawdate)]

                    #get the commit message
                    next(lines)
                    message = ''
                    m = next(lines)
                    while len(m) > 1:
                        message += (m + '\n')
                        m = next(lines)

                    #get the diffs
                    diffs = []
                    diff = next(lines)
                    while len(diff) > 1 and diff.startswith('\\') == False:
                        if diff.startswith('diff'):
                            next(lines)
                            next(lines)
                            next(lines)
                            filenameline = next(lines)
                            filename = filenameline[6:len(filenameline)]
                            #print 'FILENAME '+ filename
                            next(lines)
                            diff = next(lines)
                            diffinfo = ''
                            while len(diff) > 1 and (diff.startswith('+') or diff.startswith('-')):
                                diffinfo += diff
                                diff = next(lines)

                            diffs.append({'filename':filename, 'diff':diff})
                        else:
                            diff = next(lines)

                    #add the commit to the author's list of commits.
                    commits[current_author]['commits'].append({'date':date,'message':message, 'diffs':diffs})

                #else:
                #ignore anything else until next author line      

        return commits


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


