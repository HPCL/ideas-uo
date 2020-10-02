import requests


class GitHubAPIClient:
    """An interface for accessing the GitHub API Client.

    Utilizes the GitHub REST API to retrieve resources. More details can be seen
    here: https://docs.github.com/en/free-pro-team@latest/rest. 

    Attributes:
      username: GitHub username of account with Private Access Token (PAT)
      token: GitHub PAT that has sufficient privileges for API resources 
    """
    # Credentials
    username = None
    token = None

    # Requests Session
    session = requests.Session()

    @classmethod
    def check_credentials(cls):
        """Verifies the GitHub credentials for accessing the GitHub REST API.

        Returns:
          A boolean representing if the currently supplied credentials are valid. 
          Credentials should be set via `GitHubAPIClient.set_credentials`.

        Raises:
          ConnectionError: An error trying to access the GitHub REST API.
          RuntimeError: Occurs when the credentials are not valid.
        """

        cls.session.auth = (cls.username, cls.token)
        try:
            response = cls.session.get("https://api.github.com/")
        except requests.exceptions.ConnectionError:
            raise ConnectionError("Could not establish a connection to the GitHub "
                                  "REST API.")

        if response.status_code != 200:
            raise RuntimeError("Invalid credentials provided. Credentials must be"
                               "set via `GitHubAPIClient.set_credentials` prior "
                               "to an API call.")

    @classmethod
    def set_credentials(cls, username, token):
        """Sets GitHub credentials for accessing the GitHub REST API. 

        The specified user account should have a Private Access Token (PAT) that has
        repo access privileges. This is necessary due to rate limiting for
        unauthenticated request which is pertinent in larger repositories.

        Args:
          username: GitHub username tied with the PAT for leveraging the REST API
          token: GitHub PAT (not password!)     
        """

        cls.username = username
        cls.token = token

    @classmethod
    def get_from_api(cls, url, params, headers):
        """Queries the GitHub REST API via a HTTP GET request.

        Args:
          url: URL of GitHub REST API resource
          params: dict of keywords for resource, must contain "page" : int > 0
          headers: dict of headers to send to API server

        Returns:
          A requests.Response object for the specified API call. Invalid requests
          will still be returned, but failed connections will be raised.

        Raises:
          ConnectionError: An error trying to access the GitHub REST API.
        """

        cls.check_credentials()  # cannot access API without proper credentials

        try:
            response = cls.session.get(url=url, params=params, headers=headers)
            if response.status_code != 200:
                # TODO: better exception for designating error in pagination
                raise requests.exceptions.ConnectionError
        except requests.exceptions.ConnectionError:
            raise ConnectionError("Could not establish a connection to the GitHub"
                                  " REST API.")
        return response

    @classmethod
    def fetch_resource(cls, owner, repository, resource, params, headers,
                       start_page=1, cond=lambda r: False):
        """Fetches target resources of a GitHub repository.

        Utilizes pagination to traverse API resources with more than a 100 entries.
        From the `start_page` argument, traverses each API resource page until there
        are no more resources to fetch. 

        Args:
          owner: GitHub username or organization that owns the target repository
          repository: GitHub repository name
          resource: resource specified on GitHubAPI REST API
          params: dict of keywords for resource ("page" keyword specified by 
                  start_page argument)
          headers: dict of headers to send to API server
          start_page: int (> 0) of which page to start pagination from (default: 1)
          cond: boolean function that exists traversal based on response argument
                (default: returns False)

        Returns:
          A JSON object API results. A list of dicts.
        """

        url = f"https://api.github.com/repos/{owner}/{repository}/{resource}"

        data = []
        page = start_page
        while True:  # do while loop to utilize pagination
            params["page"] = page
            response = cls.get_from_api(
                url=url, params=params, headers=headers)
            data += response.json()
            page += 1
            if (cond(response) or not response.links or
                    "next" not in response.links.keys()):
                break

        return data

    @classmethod
    def fetch_issues(cls, owner, repository, cond=lambda response: False,
                     last_updated=None):
        """Wrapper for fetching issues from the repository.

        Args:
          last_updated: retrieves issues after this ISO 8601 date (default: None)
        """

        params = {"per_page": 100, "direction": "desc", "sort": "updated",
                  "since": last_updated, "state": "all"}
        headers = {"accept": "application/vnd.github.v3+json"}

        return cls.fetch_resource(owner=owner,
                                  repository=repository,
                                  resource="issues",
                                  params=params,
                                  headers=headers,
                                  cond=cond)

    @classmethod
    def fetch_issue_comments(cls, owner, repository, cond=lambda response: False,
                             last_updated=None):
        """Wrapper for fetching issue comments from the repository.

        Args:
          last_updated: retrieves comments after this ISO 8601 date (default: None)
        """

        params = {"per_page": 100, "direction": "desc", "sort": "updated",
                  "since": last_updated}
        headers = {"accept": "application/vnd.github.v3+json"}

        return cls.fetch_resource(owner=owner,
                                  repository=repository,
                                  resource="issues/comments",
                                  params=params,
                                  headers=headers,
                                  cond=cond)
