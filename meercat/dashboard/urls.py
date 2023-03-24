#from django.urls import path

from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('support/', views.support, name="support"),
    path('subscriptions/', views.subscriptions, name='subscriptions'),
    path('staff_index/', views.staff_index, name='staff_index'),
    path('not_authorized/', views.not_authorized, name='not_authorized'),
    path('project/<int:pk>', views.project, name='project'),
    path('prlist/<int:pk>', views.prlist, name='prlist'),
    path('pr/<int:pk>', views.pr, name='pr'),
    path('archeology/<int:pk>', views.archeology, name='archeology'),
    path('filex/<int:pk>', views.file_explorer, name='file_explorer'),
    path('folderx/<int:pk>', views.folder_explorer, name='folder_explorer'),
    path('firstresponder/<int:pk>', views.firstresponder, name='firstresponder'),
    path('refreshproject', views.refreshProject, name='refreshproject'),
    path('createpatch/', views.createPatch, name='createpatch'),
    path('branches', views.branches, name='branches'),
    path('branchdata', views.branchData, name='branchdata'),
    path('patterngraph1', views.patternGraph1, name='patterngraph1'),
    path('diffcommitdata/', views.diffCommitData, name='diffcommitdata'),
    path('getfile/', views.getFile, name='getfile'),
    path('githubbot/', views.githubBot, name='githubbot'),
    path('getdoctemplate/', views.getDocTemplate, name='getdoctemplate'),
    path('sendinvite/', views.sendInvite, name='sendinvite'),
    path('updatetags/', views.updateTags, name='updatetags'),
    path('logevent/', views.logEvent, name='logevent'),
]

