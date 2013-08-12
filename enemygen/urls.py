from django.conf.urls import patterns, include, url

from enemygen import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^generate_enemies/$', views.generate_enemies, name='generate_enemies'),
    url(r'^select_setting_ruleset/$', views.select_setting_ruleset, name='select_setting_ruleset'),
    url(r'^edit_index/$', views.edit_index, name='edit_index'),
    url(r'^delete_template/(?P<template_id>\d+)/$', views.delete_template, name='delete_template'),
    url(r'^create_enemy_template/$', views.create_enemy_template, name='create_enemy_template'),
    url(r'^enemy_template/(?P<enemy_template_id>\d+)/$', views.enemy_template, name='enemy_template'),
    url(r'^ruleset/(?P<ruleset_id>\d+)/$', views.ruleset, name='ruleset'),
)
