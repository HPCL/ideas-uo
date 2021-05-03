GITHUB_ISSUE = '''
    query($cursor: String) {
        repository(owner: "%s" name: "%s") {
            issues(first: 100, after: $cursor) {
                totalCount
                nodes {
                    title
                    createdAt
                    updatedAt
                    closedAt
                    state
                    locked
                    url
                    body
                    number
                    assignees(first: 100) {
                        nodes {
                            name
                            login
                            email
                            url
                        }
                    }
                    author {
                        login
                        url
                    }
                    milestone {
                        state
                        description
                        title
                        dueOn
                        createdAt
                        updatedAt
                    }
                    labels(first: 100) {
                        nodes {
                            name
                        }
                    }
                    comments(first: 100) {
                        nodes {
                            author {
                                login
                                url
                            }
                            body
                            createdAt
                            updatedAt
                            url
                            id
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
        rateLimit {
            limit
            cost
            remaining
            resetAt
        }
    }
    '''

GITHUB_PULLREQUEST = '''
    query($cursor: String) {
        repository(owner: "%s" name: "%s") {
            pullRequests(first: 100, after: $cursor) {
                totalCount
                nodes {
                    headRefOid
                    commits(first: 100) {
                        nodes {
                            commit {
                                oid
                            }
                        }
                    }
                    title
                    createdAt
                    updatedAt
                    mergedAt
                    state
                    locked
                    url
                    body
                    number
                    assignees(first: 100) {
                        nodes {
                            name
                            login
                            email
                            url
                        }
                    }
                    author {
                        login
                        url
                    }
                    milestone {
                        state
                        description
                        title
                        dueOn
                        createdAt
                        updatedAt
                    }
                    labels(first: 100) {
                        nodes {
                            name
                        }
                    }
                    comments(first: 100) {
                        nodes {
                            author {
                                login
                                url
                            }
                            body
                            createdAt
                            updatedAt
                            url
                            id
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }
'''

GITLAB_ISSUE = '''
    query($cursor: String) {
        project(fullPath: "%s/%s") {
            issues(first: 100000000, after: $cursor) {
                count
                nodes {
                    description
                    title
                    updatedAt
                    closedAt
                    discussionLocked
                    webUrl
                    iid
                    assignees {
                        nodes {
                            name
                            username
                            publicEmail
                            webUrl
                        }
                    }
                    author {
                        username
                        webUrl
                    }
                    milestone {
                        state
                        description
                        createdAt
                        updatedAt
                        title
                        dueDate
                    }
                    labels {
                        nodes {
                            title
                        }
                    }
                    notes {
                        nodes {
                            author {
                                username
                                webUrl
                            }
                            body
                            createdAt
                            updatedAt
                            url
                            id
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    }
'''

GITLAB_PULLREQUEST = '''
    query($cursor: String) {
        project(fullPath: "%s/%s") {
            mergeRequests(first: 100000000, after: $cursor) {
                count
                nodes {
                    commitsWithoutMergeCommits {
                        nodes {
                            sha
                        }
                    }
                    diffHeadSha
                    title
                    updatedAt
                    mergedAt
                    discussionLocked
                    webUrl
                    description
                    iid
                    assignees {
                        nodes {
                            name
                            username
                            publicEmail
                            webUrl
                        }
                    }
                    author {
                        username
                        webUrl
                    }
                    milestone {
                        state
                        description
                        createdAt
                        updatedAt
                        title
                        dueDate
                    }
                    labels {
                        nodes {
                            title
                        }
                    }
                    notes {
                        nodes {
                            author {
                                username
                                webUrl
                            }
                            body
                            createdAt
                            updatedAt
                            url
                            id
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    }
'''
