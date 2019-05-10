import os, sys, subprocess
import hpcl.Command
import mysql.connector
from hpcl.analysis import *

def getVersions(project):
    currdir = os.getcwd()
    tmpdir = os.path.join(currdir,'tmp')
    # Restore the backed up clone
    # os.system('/bin/rm -rf tmp && cp -pr ../../git_repos/%s tmp' % project) 
    filepath=os.path.join(project,'Releases.txt')
    if not os.path.exists(filepath): 
        return '',getYears(project) 
    return 'tags/',[x.strip() for x in open(filepath,'r').readlines()]

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

def checkoutSubrepos(repos,tdir):
    #currdir = os.getcwd()
    for repopath in repos.keys():
        if repopath == tdir: continue
        retcode, out, err = Command.Command('git checkout %s%s' % repos[repopath]).run(dryrun=dry_run)
    return


if __name__ == "__main__":
    
    print('Going to load repos...')

    #Load the list of repos to clone from the following file
    urls = open(os.path.join('.','URL.txt'),'r').readlines()

    #Move to the tmp directory that will hold the repos
    currdir = os.getcwd()
    tmpdir = os.path.join(currdir,'tmp')
    os.chdir(tmpdir)

    #Download each repo
    for url in urls:
        print('Cloning: ' + url)
        os.system('git clone ' + url)

    print('Finished cloning repos.')

    outfile = open('../stats.csv','w')
    outfile.write('Date' + ',' + ','.join(categories.keys()) + ',' + 'Other' + '\n')

    #Setup DB connection, this will probably change soon.
    #mydb = mysql.connector.connect(host="localhost", port="3307", user="pythondb", passwd="********", database="gitstats")
    #print(mydb)
    #mycursor = mydb.cursor()
    #sql = "INSERT INTO stats (reponame, stats) VALUES(%s, %s)"

    #Now run commands on the repos
    for repo in os.listdir('.'):
        print('Checking: ' + repo)
        os.chdir(tmpdir)   
        prefix,versions = getVersions(repo)
        print(prefix)
        print(versions)
        
        #getVersions should have already moved us into the repo dir
        linecounts =  [ [] for i in range(len(category_names)) ]
        for version in versions:    
            print('git checkout %s%s' % (prefix,version))
            retcode, out, err = Command.Command('git checkout %s%s' % (prefix,version)).run(dryrun=False)
            print(out)
            retcode, out, err = Command.Command('git log -1').run()
            print(out)
            retcode, out, err = Command.Command('git show -s --format="%%ci" %s | cut -d " " -f 1' % version).run()
            print(out)
            
            stats = getStats('.',repo)
            ts = repo + ', ' + out.strip().split('-')[0] 
            buf = ts
            for i in range(0,len(category_names)): 
                buf += ', %d' % stats[category_names[i]]
                linecounts[i].append(stats[category_names[i]]*0.001)
            outfile.write(buf+'\n')
            #years.append(int(ts))
            print(stats)
            
            val = (repo, buf)
            #mycursor.execute(sql,val)
            #mydb.commit()

    outfile.close()


