import os, sys, subprocess
import datetime
import Command

class GitCommand(object):

    def __init__(self, dir):
        self.tmpdir = dir

    #Clone a repo
    def cloneRepo(self, url):

        os.chdir(self.tmpdir)

        #Check if already exists in tmp folder
        os.system('git clone ' + url)

        #pull for the latest in case it was previously cloned
        repo = url[url.rfind('/')+1:url.rfind('.')]
        os.chdir(repo)
        os.system('git pull')

        os.chdir(self.tmpdir)

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


    #Get all commits in all the versions of a repo since data (default: utc epoch) and group by author
    def getRepoCommitData(self, reponame, since=datetime.datetime.utcfromtimestamp(0).isoformat()):

        prefix,versions = self.getRepoVersions(reponame)

        commits = {}

        for version in versions:
            #checkout the versions
            print('git checkout %s%s' % (prefix,version))
            retcode, out, err = Command.Command('git checkout %s%s' % (prefix,version)).run(dryrun=False)
            print(out)


        #git log -p # this will list all commits and the code additions in addition to dates and messages.
        # function-context for python just adds all the surrounding lines of code to the diff output
        retcode, out, err = Command.Command(f'git log -p --date=iso-strict-local --function-context --since={since}').run()
        lines = iter(out.splitlines())

        current_author = ''
        for line in lines:


            #If the line is an author, then start to piece together the commit
            #if line.startswith(b'Author: '):
            if line.startswith(b'commit'):

                commitid = line[7:len(line)]

                #Retrieve all branches that contains this commit
                #git branch -a --contains <commit>
                retcode, branches, err = Command.Command('git branch -a --contains %s' % commitid).run()

                line = next(lines)
                #print(line)

                if line.startswith(b'Author: '):

                    current_author = line[8:len(line)]

                    #track the number of commits for this author
                    if current_author in commits:
                        commits[current_author]['total_commits'] += 1
                    else:
                        commits[current_author] = {'total_commits':1, 'commits':[]}

                    #get the commit date
                    rawdate = next(lines)
                    date = rawdate[8:len(rawdate)]

                    #print(rawdate)

                    #get the commit message
                    next(lines)
                    message = ''
                    m = next(lines)
                    #print(m)
                    while len(m) > 1:
                        message += (m + b'\n').decode("utf-8")
                        try:
                            m = next(lines)
                        except StopIteration:
                            m = ''

                    #get the diffs
                    #this code will iterate over the lines trying to pull just the +/- info from the diff output
                    diffs = []
                    diff = next(lines)
                    while len(diff) > 0 and diff.startswith(b'\\') == False:
                        if diff.startswith(b'diff'):
                            #next(lines)
                            #next(lines)
                            #next(lines)
                            filenameline = diff.decode("utf-8")
                            filename = filenameline[11:len(filenameline)]
                            #print('FILENAME '+ filename)

                            line = next(lines)

                            #skip extra line if this line is seen
                            if line.startswith(b'new file mode'):
                                next(lines)
                                diff = next(lines)
                                if diff.startswith(b'diff'):
                                    break

                            if not line.startswith(b'deleted file mode') and not line.startswith(b'old mode'):

                                #skip just one line if this line is seen
                                if line.startswith(b'new file mode'):
                                    next(lines)

                                else:
                                    next(lines)
                                    next(lines)

                                #skip ahead until see first + or -
                                diff = next(lines)
                                while not (diff.startswith(b'+') or diff.startswith(b'-')) or (diff.startswith(b'+++') or diff.startswith(b'---')) :
                                    diff = next(lines)

                                diffinfo = []
                                while len(diff) >= 1:

                                    if (diff.startswith(b'+') or diff.startswith(b'-')):
                                        diffinfo.append(diff.decode("utf-8", errors='ignore'))

                                    elif diff.startswith(b'diff'):
                                        break
                                    elif len(diff) < 2:
                                        try:
                                            diff = next(lines)
                                            if len(diff) < 2:
                                                break
                                        except:
                                            break

                                    try:
                                        diff = next(lines)
                                    except:
                                        break

                                diffs.append({'filename':filename, 'diff':diffinfo})

                            #else:
                                #ignore deleted files for now
                        else:
                            try:
                                diff = next(lines)
                            except:
                                break

                    #print(diffs)
                    #add the commit to the author's list of commits.
                    commits[current_author]['commits'].append({'id':commitid, 'date':date, 'message':message, 'diffs':diffs, 'branches':branches})

                elif line.startswith(b'Merge: '):
                    #ignore merges
                    next(lines)

            #else:
                #ignore anything else until next author line

        #print(commits)
        return commits


    #Get all commits in all versions of repo and put in flat list
    def getAllCommits(self, reponame):

        prefix,versions = self.getRepoVersions(reponame)

        commits = []

        for version in versions:
            #checkout the versions
            print('git checkout %s%s' % (prefix,version))
            retcode, out, err = Command.Command('git checkout %s%s' % (prefix,version)).run(dryrun=False)
            print(out)


        #git log -p # this will list all commits and the code additions in addition to dates and messages.
        # function-context for python just adds all the surrounding lines of code to the diff output
        retcode, out, err = Command.Command('git log -p --date=iso-strict-local --function-context').run()
        lines = iter(out.splitlines())

        #current_author = ''
        for line in lines:


            #If the line is an author, then start to piece together the commit
            if line.startswith(b'commit'):

                commitid = line[7:len(line)]

                #Retrieve all branches that contains this commit
                #git branch -a --contains <commit>
                retcode, branches, err = Command.Command('git branch -a --contains %s' % commitid).run()

                line = next(lines)
                #print(line)

                if line.startswith(b'Author: '):

                    #get the commit date
                    rawdate = next(lines)
                    date = rawdate[8:len(rawdate)]

                    #print(rawdate)

                    #get the commit message
                    next(lines)
                    message = ''
                    m = next(lines)
                    #print(m)
                    while len(m) > 1:
                        message += (m + b'\n').decode("utf-8")
                        try:
                            m = next(lines)
                        except StopIteration:
                            m = ''

                    #get the diffs
                    #this code will iterate over the lines trying to pull just the +/- info from the diff output
                    diffs = []
                    diff = next(lines)
                    while len(diff) > 0 and diff.startswith(b'\\') == False:
                        if diff.startswith(b'diff'):
                            #next(lines)
                            #next(lines)
                            #next(lines)
                            filenameline = diff.decode("utf-8")
                            filename = filenameline[11:len(filenameline)]
                            #print('FILENAME '+ filename)

                            line = next(lines)

                            #skip extra line if this line is seen
                            if line.startswith(b'new file mode'):
                                next(lines)
                                diff = next(lines)
                                if diff.startswith(b'diff'):
                                    break

                            if not line.startswith(b'deleted file mode') and not line.startswith(b'old mode'):

                                #skip just one line if this line is seen
                                if line.startswith(b'new file mode'):
                                    next(lines)

                                else:
                                    next(lines)
                                    next(lines)

                                #skip ahead until see first + or -
                                diff = next(lines)
                                while not (diff.startswith(b'+') or diff.startswith(b'-')) or (diff.startswith(b'+++') or diff.startswith(b'---')) :
                                    diff = next(lines)

                                diffinfo = []
                                while len(diff) >= 1:

                                    if (diff.startswith(b'+') or diff.startswith(b'-')):
                                        diffinfo.append(diff.decode("utf-8", errors='ignore'))

                                    elif diff.startswith(b'diff'):
                                        break
                                    elif len(diff) < 2:
                                        try:
                                            diff = next(lines)
                                            if len(diff) < 2:
                                                break
                                        except:
                                            break

                                    try:
                                        diff = next(lines)
                                    except:
                                        break

                                diffs.append({'filename':filename, 'diff':diffinfo})

                            #else:
                                #ignore deleted files for now
                        else:
                            try:
                                diff = next(lines)
                            except:
                                break

                    #print(diffs)
                    #add the commit to the author's list of commits.
                    commits.append({'id':commitid, 'date':date, 'message':message, 'diffs':diffs, 'branches':branches})

                elif line.startswith(b'Merge: '):
                    #ignore merges
                    next(lines)

            #else:
                #ignore anything else until next author line

        #print(commits)
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


