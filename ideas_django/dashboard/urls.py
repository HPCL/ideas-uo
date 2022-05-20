#from django.urls import path

from django.conf.urls import url, include

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^project/(?P<pk>\d+)$', views.project, name='project'),
    url(r'^prlist/(?P<pk>\d+)$', views.prlist, name='prlist'),
    url(r'^pr/(?P<pk>\d+)$', views.pr, name='pr'),
    url(r'^refreshproject/$', views.refreshProject, name='refreshproject'),
    url(r'^createpatch/$', views.createPatch, name='createpatch'),
    url(r'^branches/$', views.branches, name='branches'),
    url(r'^branchdata/$', views.branchData, name='branchdata'),
    url(r'^patterngraph1/$', views.patternGraph1, name='patterngraph1'),
    url(r'^diffcommitdata/$', views.diffCommitData, name='diffcommitdata'),
    url(r'^getfile/$', views.getFile, name='getfile'),
    url(r'^codecheck/$', views.codeCheck, name='codecheck'),
]

