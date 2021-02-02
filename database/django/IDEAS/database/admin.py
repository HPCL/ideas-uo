from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import urlencode

from .models import Author, Project, ProjectAuthor, Commit, Diff

# Register your models here.
@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'source_url', 'last_updated', 'fork_of')

@admin.register(ProjectAuthor)
class ProjecAuthorAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'author')

@admin.register(Commit)
class CommitAdmin(admin.ModelAdmin):
    list_display = ('id', 'hash', 'datetime', 'message', 'project', 'author')

@admin.register(Diff)
class DiffAdmin(admin.ModelAdmin):
    list_display = ('id', 'commit', 'file_path', 'language', 'body')
