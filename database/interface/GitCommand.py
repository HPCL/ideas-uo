import os, sys, subprocess, datetime

    #Get all commits in all the versions of a repo since data (default: utc epoch) and group by author
    def getRepoCommitData(self, reponame, includebranches = False, since=datetime.datetime.utcfromtimestamp(0).isoformat(), until=datetime.datetime.today().isoformat()):
        # function-context for python just adds all the surrounding lines of code to the diff output
        retcode, out, err = Command.Command(f'git log -p --date=iso-strict-local --function-context --since={since} --until={until}').run()
                commitid = commitid.decode('utf-8')
                commitid = commitid.strip('\n')

                #Retrieve all branches that contains this commit
                branches = ''
                if includebranches:
                    retcode, branches, err = Command.Command('git branch -a --contains %s' % commitid).run()
                    try:
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
                                    diffs.append({'filename':filename, 'diff':diffinfo})

                                #else:
                                    #ignore deleted files for now
                            else:
                                try:
                                    diff = next(lines)
                                except:
                                    break
                    except:
                        print('Done with commits from this repo.')

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
    def getAllCommits(self, reponame, includebranches = False):

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
                commitid = commitid.strip('\n')

                #Retrieve all branches that contains this commit
                branches = ''
                if includebranches:
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
                    try:
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
                    except:
                        print('Done with commits for this repo.')
                    commits.append({'id':commitid, 'date':date, 'message':message, 'diffs':diffs, 'branches':branches})