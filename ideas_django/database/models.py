from django.db import models

# Create your models here.
class Author(models.Model):
    username = models.CharField(max_length=64)
    email = models.EmailField(null=True)
    name = models.CharField(max_length=256, null=True)
    url = models.CharField(max_length=256, null=True)

    class Meta:
        db_table = 'author'
        ordering = ['id']
        verbose_name = 'author'
        verbose_name_plural = 'authors'
        
    def __str__(self):
        return self.username

class Project(models.Model):
    source_url = models.URLField()
    name = models.CharField(max_length=64)
    last_updated = models.DateTimeField(auto_now=True)
    authors = models.ManyToManyField(Author, through='ProjectAuthor')
    has_github = models.BooleanField(default=False)
    has_gitlab = models.BooleanField(default=False)
    github_last_updated = models.DateTimeField(auto_now=True, null=True)
    gitlab_last_updated = models.DateTimeField(auto_now=True, null=True)
    fork_of = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='project_fork_of')
    child_of = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='project_child_of')

    class Meta:
        db_table = 'project'
        ordering = ['id']
        verbose_name = 'project'
        verbose_name_plural ='projects'

    def __str__(self):
        return self.name

class Tag(models.Model):
    tag = models.CharField(max_length=64)

    class Meta:
        db_table = 'tag'
        ordering = ['id']
        verbose_name = 'tag'
        verbose_name_plural = 'tags'

    def __str__(self):
        return self.tag

class ProjectTag(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        db_table = 'project_has_tag'
        ordering = ['id']
        verbose_name = 'project has tag'
        verbose_name_plural = 'project has tags'

    def __str__(self):
        return f'{self.project} has {self.author}'

class ProjectAuthor(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

    class Meta:
        db_table = 'project_has_author'
        ordering = ['id']
        verbose_name = 'project has author'
        verbose_name_plural = 'project has authors'

    def __str__(self):
        return f'{self.project} has {self.author}'

class Person(models.Model):
    alias = models.CharField(max_length=64)
    email = models.EmailField()
    github_username = models.CharField(max_length=64, null=True)
    gitlab_username = models.CharField(max_length=64, null=True)

    class Meta:
        db_table = 'person'
        ordering = ['id']
        verbose_name = 'person'
        verbose_name_plural = 'people'

    def __str__(self):
        return self.alias

class PersonAuthor(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

    class Meta:
        db_table = 'person_has_author'
        ordering = ['id']
        verbose_name = 'person has author'
        verbose_name_plural = 'person has authors'

    def __str__(self):
        return f'{self.person} has {self.author}'

class Commit(models.Model):
    hash = models.CharField(max_length=128)
    datetime = models.DateTimeField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    message = models.TextField()
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    branch = models.TextField()

    class Meta:
        db_table = 'commit'
        ordering = ['id']
        verbose_name = 'commit'
        verbose_name_plural ='commits'

    def __str__(self):
        return f'Commit {self.hash}'

class Diff(models.Model):
    file_path = models.FilePathField(max_length=256)
    language = models.CharField(max_length=64)
    body = models.TextField()
    commit = models.ForeignKey(Commit, on_delete=models.CASCADE)

    class Meta:
        db_table = 'diff'
        ordering = ['id']
        verbose_name = 'diff'
        verbose_name_plural ='diffs'

    def __str__(self):
        return f'Diff {self.file_path}'

class Label(models.Model):
    name = models.CharField(max_length=256)

    class Meta:
        db_table = 'label'
        ordering = ['id']
        verbose_name = 'label'
        verbose_name_plural = 'labels'

    def __str__(self):
        return f'Label {self.name}'

class Issue(models.Model):
    title = models.CharField(max_length=256)
    description = models.TextField()
    updated_at = models.DateTimeField()
    closed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(null=True)
    locked = models.BooleanField()
    url = models.CharField(max_length=256)
    number = models.IntegerField()
    state = models.CharField(max_length=64)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='issue_author')
    assignees = models.ManyToManyField(Author, through='IssueAssignee', related_name='issue_assignee')
    labels = models.ManyToManyField(Label, through='IssueLabel')

    class Meta:
        db_table = 'issue'
        ordering = ['id']
        verbose_name = 'issue'
        verbose_name_plural = 'issues'

    def __str__(self):
        return f'Issue #{self.number}: {self.title}'

class CommitTag(models.Model):
    sha = models.CharField(max_length=64)

    class Meta:
        db_table = 'commit_tag'
        ordering = ['id']
        verbose_name = 'commit tag'
        verbose_name_plural = 'commit tags'

    def __str__(self):
        return f'CommitTag {self.sha}'

class PullRequest(models.Model):
    title = models.CharField(max_length=256)
    description = models.TextField()
    updated_at = models.DateTimeField()
    created_at = models.DateTimeField(null=True)
    merged_at = models.DateTimeField(null=True)
    locked = models.BooleanField()
    url = models.CharField(max_length=256)
    number = models.IntegerField()
    state = models.CharField(max_length=64)
    head_sha = models.CharField(max_length=256)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='pr_author')
    assignees = models.ManyToManyField(Author, through='PullRequestAssignee', related_name='pr_assignee')
    labels = models.ManyToManyField(Label, through='PullRequestLabel')
    commits = models.ManyToManyField(CommitTag, through='PullRequestCommit')

    class Meta:
        db_table = 'pr'
        ordering = ['id']
        verbose_name = 'pull request'
        verbose_name_plural = 'pull requests'

    def __str__(self):
        return f'Pull Request #{self.number}: {self.title}'

class Milestone(models.Model):
    state = models.CharField(max_length=64)
    description = models.TextField()
    title = models.CharField(max_length=256)
    due_on = models.DateTimeField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, null=True)
    pr = models.ForeignKey(PullRequest, on_delete=models.CASCADE, null=True)
    
    class Meta:
        db_table = 'milestone'
        ordering = ['id']
        verbose_name = 'milestone'
    
    def __str__(self):
        return f'Milestone {self.title}'

class PullRequestCommit(models.Model):
    pr = models.ForeignKey(PullRequest, on_delete=models.CASCADE)
    commit = models.ForeignKey(CommitTag, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'pr_has_commit'
        ordering = ['id']
        verbose_name = 'pr has commit'
        verbose_name_plural = 'pr has commits'

    def __str__(self):
        return f'{self.pr} has {self.commit}'

class IssueLabel(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE)
    label = models.ForeignKey(Label, on_delete=models.CASCADE)

    class Meta:
        db_table = 'issue_has_label'
        ordering = ['id']
        verbose_name = 'issue has label'
        verbose_name_plural = 'issue has labels'

    def __str__(self):
        return f'{self.issue} has {self.label}'

class IssueAssignee(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE)
    assignee = models.ForeignKey(Author, on_delete=models.CASCADE)

    class Meta:
        db_table = 'issue_has_assignee'
        ordering = ['id']
        verbose_name = 'issue has assignee'
        verbose_name_plural = 'issue has assignees'

    def __str__(self):
        return f'{self.issue} has {self.assignee}'

class PullRequestLabel(models.Model):
    pr = models.ForeignKey(PullRequest, on_delete=models.CASCADE)
    label = models.ForeignKey(Label, on_delete=models.CASCADE)

    class Meta:
        db_table = 'pr_has_label'
        ordering = ['id']
        verbose_name = 'pr has label'
        verbose_name_plural = 'pr has labels'

    def __str__(self):
        return f'{self.pr} has {self.label}'

class PullRequestAssignee(models.Model):
    pr = models.ForeignKey(PullRequest, on_delete=models.CASCADE)
    assignee = models.ForeignKey(Author, on_delete=models.CASCADE)

    class Meta:
        db_table = 'pr_has_assignee'
        ordering = ['id']
        verbose_name = 'pr has assignee'
        verbose_name_plural = 'pr has assignees'

    def __str__(self):
        return f'{self.pr} has {self.assignee}'

class Comment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, null=True)
    pr = models.ForeignKey(PullRequest, on_delete=models.CASCADE, null=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    body = models.TextField()

    class Meta:
        db_table = 'comment'
        ordering = ['id']
        verbose_name = 'comment'
        verbose_name_plural = 'comments'

    def __str__(self):
        return f'Comment by {self.author}'

class IssueTag(models.Model):
    url = models.CharField(max_length=256)

    class Meta:
        db_table = 'issue_tag'
        ordering = ['id']
        verbose_name = 'issue tag'
        verbose_name_plural = 'issue tags'

class PullRequestIssue(models.Model):
    pr = models.ForeignKey(PullRequest, on_delete=models.CASCADE)
    issue = models.ForeignKey(IssueTag, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'pr_has_issue'
        ordering = ['id']
        verbose_name = 'pull request has issue'
        verbose_name_plural = 'pull request has issues'

class EventRepo(models.Model):
    repo_id = models.IntegerField()
    name = models.CharField(max_length=128)
    url = models.URLField()
    
    class Meta:
        db_table = 'event_repo'
        ordering = ['id']
        verbose_name = 'event repo'
        verbose_name_plural = 'event repos'

class EventActor(models.Model):
    actor_id = models.IntegerField()
    login = models.CharField(max_length=128)
    gravatar_id = models.CharField(max_length=128)
    avatar_url = models.URLField()
    url = models.URLField()

    class Meta:
        db_table = 'event_actor'
        ordering = ['id']
        verbose_name = 'event actor'
        verbose_name_plural = 'event actors'

class EventOrg(models.Model):
    org_id = models.IntegerField()
    login = models.CharField(max_length=128)
    gravatar_id = models.CharField(max_length=128)
    avatar_url = models.URLField()
    url = models.URLField()
    
    class Meta:
        db_table = 'event_org'
        ordering = ['id']
        verbose_name = 'event org'
        verbose_name_plural = 'event orgs'

class EventPayload(models.Model):
    action = models.CharField(max_length=128, null=True)
    ref = models.CharField(max_length=128, null=True)
    ref_type = models.CharField(max_length=128, null=True)
    master_branch = models.CharField(max_length=128, null=True)
    description = models.CharField(max_length=1024, null=True)
    forkee_url = models.URLField(null=True)
    issue_url = models.URLField(null=True)
    comment_url = models.URLField(null=True)
    member_login = models.CharField(max_length=128, null=True)
    pr_number = models.IntegerField(null=True)
    pr_url = models.URLField(null=True)
    pr_review_url = models.URLField(null=True)
    push_id = models.BigIntegerField(null=True)
    size = models.IntegerField(null=True)
    distinct_size = models.BigIntegerField(null=True)
    head_sha = models.CharField(max_length=128, null=True)
    before_sha = models.CharField(max_length=128, null=True)
    release_url = models.URLField(null=True)
    effective_date = models.CharField(max_length=128, null=True)

    class Meta:
        db_table = 'event_payload'
        ordering = ['id']
        verbose_name = 'event payload'
        verbose_name_plural = 'event payloads'

class EventPage(models.Model):
    name = models.CharField(max_length=128)
    title = models.CharField(max_length=128)
    action = models.CharField(max_length=128)
    sha = models.CharField(max_length=128)
    url = models.URLField()

    class Meta:
        db_table = 'event_page'
        ordering = ['id']
        verbose_name = 'event page'
        verbose_name_plural = 'event pages'

class EventPages(models.Model):
    payload = models.ForeignKey(EventPayload, on_delete=models.CASCADE)
    page = models.ForeignKey(EventPage, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'event_has_page'
        ordering = ['id']
        verbose_name = 'event has page'
        verbose_name_plural = 'event has pages'

class Event(models.Model):
    api_id = models.BigIntegerField()
    type = models.CharField(max_length=128)
    public = models.BooleanField()
    created_at = models.DateTimeField()
    payload = models.ForeignKey(EventPayload, on_delete=models.CASCADE, null=True)
    repo = models.ForeignKey(EventRepo, on_delete=models.CASCADE)
    actor = models.ForeignKey(EventActor, on_delete=models.CASCADE)
    org = models.ForeignKey(EventOrg, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    class Meta:
        db_table = 'event'
        ordering = ['id']
        verbose_name = 'event'
        verbose_name_plural = 'events'
