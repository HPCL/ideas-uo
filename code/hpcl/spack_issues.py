import datetime

import pandas as pd
import pymongo

from github_api import GitHubAPIClient


class SpackMongoClient:
    """A client for retrieving the latest spack issues and comments.

    Interfaces with the `GitHubAPIClient` class and MongoDB to keep issues and
    issue comments up-to-date. Issues and their comments are stored on separate
    collections on the server. For each, there is a corresponding smaller
    collection denoted as `latest_issue` or `latest_comment` which keeps track of
    the last entry stored on the server. With this design, the number of API calls
    is drastically reduced and it easier to quickly view what the current state of
    the data is.

    The MongoDB server is organized as follows:

    +-- spack_issues: Root database that contains the collections necessary for
                      keeping spack issues and comments up-to-date
        +-- latest_issue: Collection that keeps track of the state of issues
                          stored on the server. Contains two keyword:
                          `latest_issue` and `last_updated`. The first is a
                          monotonic increasing integer which is the latest issue
                          number currently residing in the `issues` collection.
                          The latter keyword simply determines the last time new
                          issues were fetched from the GitHub REST API (UTC time,
                          ISO 8601 format).
        +-- issues: Collection that stores the individual issues.
        +-- latest_comments:  Collection that keeps track of the state of comments
                              stored on the server. (NOT YET IMPLEMENTED)
        +-- comments: Collection that stores the individual comments.
                      (NOT YET IMPLEMENTED)

    Attributes:
      client: MongoDB client instance for accessing the databases
    """

    # MongoDB Client
    client = None

    def __init__(self, mongo_username, mongo_password, github_username, github_token):
        """Creates an instance of SpackMongoClient for accessing spack issues and comments.

        Args:
            mongo_username: username for HPCL MongoDB
            mongo_password: password for HPCL MongoDB
            github_username: GitHub username
            github_token: GitHub private access token (see GitHubAPIClient for more details)
        """

        GitHubAPIClient.set_credentials(username=github_username, token=github_token)
        self.set_credentials(username=mongo_username, password=mongo_password)
        self.check_credentials()

    def check_credentials(self):
        """Verifies the MongoDB client for accessing databases.

        Raises:
          RuntimeError: Occurs when the credentials are not valid.
        """
        try:
            self.client.server_info()
        except (pymongo.errors.ServerSelectionTimeoutError, AttributeError):
            raise RuntimeError("Invalid credentials provided. Credentials must be "
                               "set via `SpackMongoClient.set_credentials` prior "
                               "to an database call.")

    def set_credentials(self, username, password):
        """Sets MongoDB credentials for the client.

        These are the credentials needed for accessing the MongoDB server.

        Args:
          username: MongoDB username
          password: MongoDB password
        """

        host = f"mongodb://{username}:{password}@sansa.cs.uoregon.edu:27017"
        self.client = pymongo.MongoClient(host=host)

    def get_latest_issue(self):
        """Returns the latest issue number stored on the MongoDB server.

        Returns:
          A positive, monotonic increasing, integer representing the most recent
          issue number stored. If the collection `latest_issue` does not exist on
          the server then it simply returns 0. GitHub issue numbers always start at
          1 so it will follow the update behavior and grab issue numbers > 0 on the
          `SpackMongoClient.update_spack_issues()` function call -- i.e. if the
          collection does not exist, then on an update call the server will grab
          every single issue from the spack repository.
        """

        db = self.client.spack_issues
        if not db.latest_issue.find_one():
            return 0
        else:
            return db.latest_issue.find_one()["latest_issue"]

    def update(self, key):
        """Updates the server to have the latest issues or comments.

        Retrieves all issues or comments since the last update check. Old
        records are replaced by the new ones.

        Args:
            key: str of issues or comments
        """

        valid_keys = {"issues", "comments"}
        if key.lower() not in valid_keys:
            raise TypeError(f"Argument 'key' must be one of the following: {valid_keys}.")

        last_updated = None

        if key == "issues":
            if self.get_issue_status():
                last_updated = datetime.datetime.fromisoformat(self.get_issue_status())
            print(f"Fetching {key} updated since {last_updated}...")
            api_result = GitHubAPIClient.fetch_issues(
                owner="spack", repository="spack", last_updated=last_updated)
        else:
            if self.get_comment_status():
                last_updated = datetime.datetime.fromisoformat(self.get_comment_status())
            print(f"Fetching {key} updated since {last_updated}...")
            api_result = GitHubAPIClient.fetch_issue_comments(
                owner="spack", repository="spack", last_updated=last_updated)

        print(f"Got {len(api_result)} from GitHub REST API.")
        update = False if not api_result else True # only update if needed

        if update:
            spack_issues_db = self.client.spack_issues

            if not last_updated:
                last_updated = datetime.datetime.fromtimestamp(0)
            else:
                import dateutil
                last_update = dateutil.parser.isoparse(str(last_updated))
                # TODO: Improve versioning issue
                #last_updated = datetime.datetime.fromisoformat(str(last_updated)) # only works on python 3.7+ (Google Colab 3.6.9)


            # only care about records after last update
            # https://stackoverflow.com/questions/19654578/python-utc-datetime-objects-iso-format-doesnt-include-z-zulu-or-zero-offset
            records_to_add = [record for record in api_result
                if datetime.datetime.fromisoformat(record["updated_at"][:-1]) > last_updated]

            urls = [record["url"] for record in records_to_add]
            replaced = spack_issues_db[key].delete_many({"url": {"$in": urls}})
            inserted = spack_issues_db[key].insert_many(records_to_add)

            if key == "issues":
                self.update_issue_status()
            else:
                self.update_comment_status()

            print(f"Inserted {len(inserted.inserted_ids) - replaced.deleted_count} new {key} to MongoDB.")
            print(f"Updated {replaced.deleted_count} existing {key} in MongoDB.")

        else:
            print("No new changes.")

        print("Done.")

    def update_issues(self):
        """Wrapper for updating issues.
        """

        self.update("issues")

    def update_comments(self):
        """Wrapper for updating comments.
        """

        self.update("comments")

    def load(self, key, update=True):
        """Gets the issues or comments from the MongoDB server and returns
        it in a Pandas DataFrame.

        Args:
            key: str of issues or comments
            update: boolean whether to check for the latest spack issues before
                    retrieval of the issue from the server (default: True)
        """

        valid_keys = {"issues", "comments"}
        if key.lower() not in valid_keys:
            raise TypeError(f"Argument 'key' must be one of the following: {valid_keys}.")

        db = self.client.spack_issues
        if update: self.update(key)

        cursor = db[key].find({})
        return pd.DataFrame(list(cursor)).drop("_id", axis=1)

    def load_issues(self, update=True):
        """Wrapper for loading issues.

        Args:
            update: boolean whether to check for the latest spack issues before
                    retrieval of the issue from the server (default: True)
        """

        return self.load("issues", update)

    def load_comments(self, update=True):
        """Wrapper for loading comments.

        Args:
            update: boolean whether to check for the latest spack issues before
                    retrieval of the issue from the server (default: True)
        """

        return self.load("comments", update)

    def get_status(self):
        spack_issues_db = self.client.spack_issues
        status = spack_issues_db.status.find_one()
        return status

    def get_comment_status(self):
        status = self.get_status()
        return None if not status else status["comments_updated_at"]

    def get_issue_status(self):
        status = self.get_status()
        return None if not status else status["issues_updated_at"]

    def set_status(self, comments_updated_at, issues_updated_at):
        spack_issues_db = self.client.spack_issues
        payload = {
            "comments_updated_at": comments_updated_at,
            "issues_updated_at": issues_updated_at}
        spack_issues_db.status.delete_many({})
        spack_issues_db.status.insert_one(payload)

    def update_comment_status(self):
        current_date = datetime.datetime.utcnow().isoformat()
        self.set_status(comments_updated_at=current_date,
            issues_updated_at=self.get_issue_status())

    def update_issue_status(self):
        current_date = datetime.datetime.utcnow().isoformat()
        self.set_status(comments_updated_at=self.get_comment_status(),
            issues_updated_at=current_date)

    def get_issue_comments(self, issue_number, comments):
        """Finds issue comments.

        Args:
            issue_number: Number identifiying the issue
            comments:  Pandas DataFrame of all issue comments via `load_comments()`

        Returns:
            DataFrame of comments.
        """

        issue_url = f"https://api.github.com/repos/spack/spack/issues/{issue_number}"
        comments = comments.loc[comments.issue_url == issue_url]

        return comments
