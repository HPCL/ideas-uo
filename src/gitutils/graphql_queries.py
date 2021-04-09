GITHUB_ISSUE = '''
    query($cursor: String) {
        repository(owner: "%s" name: "%s") {
            issues(first: 100, after: $cursor) {
                totalCount
                nodes {
                    title
                    createdAt
                    updatedAt
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
