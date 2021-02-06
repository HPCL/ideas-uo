from django.db import models

# Create your models here.
class Author(models.Model):
    username = models.CharField(max_length=64)
    email = models.EmailField()

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
    fork_of = models.ForeignKey('self', on_delete=models.CASCADE, null=True)

    class Meta:
        db_table = 'project'
        ordering = ['id']
        verbose_name = 'project'
        verbose_name_plural ='projects'

    def __str__(self):
        return self.name

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
        db_table = 'person_has_auhtor'
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
    branch = models.CharField(max_length=128, default='master')

    class Meta:
        db_table = 'commit'
        ordering = ['id']
        verbose_name = 'commit'
        verbose_name_plural ='commits'

    def __str__(self):
        return f'Commit {self.hash}'

class Diff(models.Model):
    file_path = models.FilePathField()
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
