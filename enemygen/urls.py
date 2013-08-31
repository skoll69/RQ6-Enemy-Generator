from django.conf.urls import patterns, include, url

from enemygen import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^instructions/$', views.instructions, name='instructions'),
    url(r'^generate_enemies/$', views.generate_enemies, name='generate_enemies'),
    url(r'^select_setting_ruleset/$', views.select_setting_ruleset, name='select_setting_ruleset'),
    url(r'^edit_index/$', views.edit_index, name='edit_index'),
    url(r'^delete_template/(?P<template_id>\d+)/$', views.delete_template, name='delete_template'),
    url(r'^clone_template/(?P<template_id>\d+)/$', views.clone_template, name='clone_template'),
    url(r'^create_enemy_template/$', views.create_enemy_template, name='create_enemy_template'),
    url(r'^enemy_template/(?P<enemy_template_id>\d+)/$', views.enemy_template, name='enemy_template'),
    url(r'^apply_skill_bonus/(?P<template_id>\d+)/$', views.apply_skill_bonus, name='apply_skill_bonus'),
    url(r'^race/(?P<race_id>\d+)/$', views.race, name='race'),
    url(r'^create_race/$', views.create_race, name='create_race'),
    url(r'^delete_race/(?P<race_id>\d+)/$', views.delete_race, name='delete_race'),
    url(r'^ruleset/(?P<ruleset_id>\d+)/$', views.ruleset, name='ruleset'),
)
