"""Interfaces a GitHub repository with MongoDB.

This module handles the storage of GitHub repository data on a MongoDB server
for faster access. Interacts with the GitHub REST API to retrieve data and
store it on MongoDB collections. Each GitHub project is stored as a separate
database on the MongoDB server.

The structure for each project is as follows:

+-- <owner:repo> (Database): Root directory of a project. Where owner is the
    owner of the GitHub repository and repo is the repo name. The naming
    convention for the databases are <owner:repo> (without < & >) where owner
    is the GitHub username or organization that owns the repository and repo
    is simply the repository name. For example, github.com/HPCL/ideas-uo would
    have a database name of: HPCL:ideas-uo. Due to GitHub's naming convention,
    this is hashed via MD5 to eliminate naming inconsistencies. 
    +-- status (Collection): Single document collection for keeping track of
        updates.
        - comments_updated_at: ISO8601 DateTime of the last time new
            issue comments were pulled from the API.
        - issues_updated_at: ISO8601 DateTime of the last time new
            issues were pulled from the API.
    +-- issues (Collection): Collection where each document is a single issue.
    +-- comments (Collection): Collection where each document is a single issue.
"""

import datetime
import hashlib
import logging

# Setup Logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(level=logging.DEBUG)
formatter = logging.Formatter(fmt="[%(levelname)s]: %(asctime)s - %(message)s")
ch.setFormatter(fmt=formatter)
logger.addHandler(hdlr=ch)

import pandas as pd
import pymongo

from github_api import GitHubAPIClient

# Naive implementation of datetime.datetime.fromisoformat() for Google Colab
# as it runs on Python 3.6.9

def fromisoformat(current):
    # For Python 3.7+ use datetime.datetime.fromisoformat()
    year = current[:current.index("-")]
    current = current[current.index("-")+1:]
    month = current[:current.index("-")]
    current = current[current.index("-")+1:]
    day = current[:current.index("T")]
    current = current[current.index("T")+1:]
    hour = current[:current.index(":")]
    current = current[current.index(":")+1:]
    minute = current[:current.index(":")]
    current = current[current.index(":")+1:]
    try:
        second = current[:current.index(".")]
        current = current[current.index(".")+1:]
        microsecond = current
    except:
        second = current
        microsecond = 0
    date = datetime.datetime(year=int(year), month=int(month), day=int(day), 
        hour=int(hour), minute=int(minute), second=int(second), 
        microsecond=int(microsecond))
    return date

# Constants
MONGODB_ADDRESS = "sansa.cs.uoregon.edu:27017"

class ProjectInterface:
    """Interface between GitHub and MongoDB.

    This class handles the creation and retrieval of data from a GitHub 
    repository to MongoDB.

    Attributes:
        resources: list of GitHub API resources that can be utilized
    """

    resources = {
        "issues": GitHubAPIClient.fetch_issues,
        "comments": GitHubAPIClient.fetch_issue_comments}

    def __init__(self, mongo_username, mongo_password, owner, repo, 
            github_username=None, github_token=None, first_grab=True):
        """Initializes a ProjectInterface instance with the HPCL MongoDB 
        server.

        Args:
            mongo_username: username for MongoDB
            mongo_password: password for MongoDB
            owner: github repo owner
            repo: github repo name 
                (e.g. https://github.com/HPCL/ideas-uo/ -> owner = HPCL 
                and repo = ideas-uo)
            github_username: username for GitHub (Default: None)
            github_token: personal access token for GitHub (Default: None)
            first_grab: if new project, pulls all resources into MongoDB (Default: True)
        """
        
        self.owner = owner
        self.repo = repo

        if mongo_username and mongo_password:
            host = f"mongodb://{mongo_username}:{mongo_password}@{MONGODB_ADDRESS}"
        else:
            # for testing without credentials
            host = f"mongodb://{MONGODB_ADDRESS}"

        logger.debug(f"Connecting to MongoDB server at: {MONGODB_ADDRESS}")
        self.client = pymongo.MongoClient(host=host)

        self._no_update = False
        if not github_username or not github_token:
            logger.warn("GitHub credentials not provided. Only able to pull from existing project.")
            self._no_update = True
        else:
            GitHubAPIClient.set_credentials(username=github_username, 
                token=github_token)

        # Verify MongoDB connection
        try:
            self.client.server_info()
        except (pymongo.errors.ServerSelectionTimeoutError, AttributeError):
            raise ConnectionError("Invalid credentials or host for MongoDB server.")
        
        # Project repository can have symbols that are invalid with MongoDB, hash the entire string to prevent this
        self.project = self._create_project_name(owner=self.owner, repo=self.repo)

        # Check if project is already on mongodb
        if any(cursor for cursor in self.client.list_database_names() if cursor == self.project):
            logger.debug(f"Found {self.project} on MongoDB.")
            # TODO: check if tables exist
        else:
            logger.debug(f"Unknown project {self.project}.")
            # If no update privileges then raise error
            if self._no_update:
                message = f"Unable to find {self.project} on MongoDB. Either parameter(s) `owner` and/or `repo` are misspelled or do not have GitHub credentials to create new project."
                logger.critical(message)
                raise RuntimeError(message)
            
            # Verify that the specific repository exists or has sufficient access
            try:
                GitHubAPIClient.fetch_issues(owner=owner, repository=repo, cond=lambda r: True) # pass cond only need 1 page of results
            except:
                message = f"Unable to find {self.owner}/{self.repo} on GitHub. Either invalid GitHub credentials, insufficient repo/token access, or parameter(s) 'owner' and/or 'repo' are misspelled."
                logger.critical(message)
                raise RuntimeError(message)
            
            self._create_status_collection()
            if first_grab:
                logger.debug("Filling new project with GitHub data...")
                for resource in ProjectInterface.resources:
                    self.update(resource=resource)
                    logger.debug(f"Added {resource} to MongoDB.")
            logger.debug("Successfully created new project.")

    # __init__ helper functions

    def _create_project_name(self, owner, repo):
        """Creates the project (i.e. MongoDB database) name by using MD5 hashing.

        Utilizes hashes as GitHub repository names can be invalid names for
        MongoDB databases and collections. This is not a security measure rather a
        way to standardize the database names.
        
        Args:
            owner: owner of repo
            repo: repo name
        Returns:
            The hexdigest of the hash.
        """

        m = hashlib.md5()
        raw_project_name = f"{owner}:{repo}"
        m.update(raw_project_name.encode(encoding="utf-8"))
        digest = m.hexdigest()
        logger.debug(f"Hashed project name {raw_project_name} to {digest}.")
        return digest

    def _create_status_collection(self):
        """Creates the status collection for the project.
        """

        # If all checks pass initialize new project
        db = self.client[self.project]
        # Initialize status collection
        payload = {collection + "_updated_at": None for collection in ProjectInterface.resources}
        status = db["status"]
        status.insert_one(document=payload)
        logger.debug(f"Initialized status with fields: {payload.keys()}")
    
    def get_status(self):
        """Retrieves the status of the project.

        Returns:
            JSON object of ProjectInterface.resources updated_at fields
        """

        return self.client[self.project]["status"].find_one()

    def _update_status(self, *args):
        """Function helper for updating the status of a project.

        Whenever there is an update to the status collection, the function
        simply deletes the existing document and inserts a new one.

        Args:
            args: args of ProjectInterface.resources attributes
        """

        db = self.client[self.project]
        status = self.get_status()
        payload = {(k + "_updated_at"): status[k + "_updated_at"] for k in ProjectInterface.resources}

        for arg in args:
            if arg in ProjectInterface.resources:
                logger.debug(f"Updated status field {arg}")
                # bug with current time so go 1 day earlier
                payload[arg + "_updated_at"] = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).isoformat()
        
        db["status"].delete_many({})
        db["status"].insert_one(payload)

    def load(self, resource, update=False, query={}):
        """Loads API data from MongoDB into a Pandas DataFrame.

        Args:
            resource: resource to grab
            update: boolean whether to check for the latest spack issues before
                    retrieval of the issue from the server (Default: False)
        Returns:
            Pandas DataFrame of an entire resource collection (e.g. resource)
        """

        if resource not in ProjectInterface.resources:
            raise TypeError(f"Argument 'resource' must be one of the following: {ProjectInterface.resources.keys()}.")

        db = self.client[self.project]
        if update: self.update(resource)

        cursor = db[resource].find(query)
        return pd.DataFrame(list(cursor))
    
    def load_issues(self, update=False, start_date=datetime.datetime.fromtimestamp(0).isoformat(),
        end_date=datetime.datetime.utcnow().isoformat(), labels=[], assignees=[]):
        """Wrapper for grabbing issues from MongoDB.

        Args:
            update: boolean whether to check for the latest spack issues before
                    retrieval of the issue from the server (Default: False)
            start_date: ISO8601 datetime string for inclusive lower-bound (Default: UTC Epoch)
            end_date: IS08601 datetime string for exclusive upper-bound (Default: current time)
            labels: list of label names to filter for (Default: [])
            assignees: list of login names to filter for (Default: []) 
        Returns:
            Pandas DataFrame of issues based on query
        """
        query = {
            "updated_at": 
                {"$gte": start_date, "$lt": end_date},
            "labels": 
                {"$elemMatch": 
                    {"name": 
                        {"$in": labels}
                    }
                },
            "assignees":
                {"$elemMatch":
                    {"login":
                        {"$in": assignees}
                    }
                }
        }
        if not labels: del query["labels"]
        if not assignees: del query["assignees"]

        return self.load(resource="issues", update=update, query=query)

    def load_comments(self, update=False, start_date=datetime.datetime.fromtimestamp(0).isoformat(),
        end_date=datetime.datetime.utcnow().isoformat(), login=None):
        """Wrapper for grabbing issue comments from MongoDB.
        
        Args:
            update: boolean whether to check for the latest spack issues before
                    retrieval of the issue from the server (Default: False)
            start_date: ISO8601 datetime string for inclusive lower-bound (Default: UTC Epoch)
            end_date: IS08601 datetime string for exclusive upper-bound (Default: current time)
            login: string of commenter login (Default: None)
        """
        
        query = {
            "updated_at": 
                {"$gte": start_date, "$lt": end_date},
            "user.login": 
                {"$eq": login}
        }
        if not login: del query["user.login"]

        return self.load(resource="comments", update=update, query=query)

    def update(self, resource):
        """Updates the server to have the latest issues or comments.

        Retrieves all issues or comments since the last update check. Old
        records are replaced by the new ones.

        Args:
            key: str of issues or comments
        """

        if self._no_update:
            message = "Cannot update without GitHub credentials."
            logger.critical(message)
            raise RuntimeError(message)

        if resource not in ProjectInterface.resources:
            raise TypeError(f"Argument 'resource' must be one of the following: {ProjectInterface.resources.keys()}.")

        last_updated = self.get_status()[resource + "_updated_at"] 
        logger.debug(f"Fetching {resource} updated since {last_updated}...")
        last_updated = fromisoformat(last_updated) if last_updated else None
        api_result = ProjectInterface.resources[resource](
            owner=self.owner,
            repository=self.repo,
            last_updated=last_updated)
                
        logger.debug(f"Got {len(api_result)} records from GitHub REST API.")
        update = False if not api_result else True # only update if needed

        if update:
            db = self.client[self.project]
            last_updated = datetime.datetime.fromtimestamp(0) if not last_updated else fromisoformat(last_updated.isoformat())

            # only care about records after last update
            # https://stackoverflow.com/questions/19654578/python-utc-datetime-objects-iso-format-doesnt-include-z-zulu-or-zero-offset
    
            if resource in {"issues", "comments"}:
                records_to_add = [record for record in api_result
                    if fromisoformat(record["updated_at"][:-1]) > last_updated]

                urls = [record["url"] for record in records_to_add]
                replaced = db[resource].delete_many({"url": {"$in": urls}})
                inserted = db[resource].insert_many(records_to_add)
                
                self._update_status(resource)
            else:
                message = "This resource has not been supported yet!"
                logger.critical(message)
                raise NotImplementedError(message)

            logger.debug(f"Inserted {len(inserted.inserted_ids) - replaced.deleted_count} new {resource} to MongoDB.")
            logger.debug(f"Updated {replaced.deleted_count} existing {resource} in MongoDB.")

        else:
            logger.debug("No new changes.")

        logger.debug("Done.")