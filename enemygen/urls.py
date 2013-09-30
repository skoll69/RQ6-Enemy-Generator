from django.conf.urls import patterns, include, url

from enemygen import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^generate_enemies/$', views.generate_enemies, name='generate_enemies'),
    url(r'^generate_party/$', views.generate_party, name='generate_party'),
    url(r'^party_index/$', views.party_index, name='party_index'),
    url(r'^select_setting_ruleset/$', views.select_setting_ruleset, name='select_setting_ruleset'),
    url(r'^edit_index/$', views.edit_index, name='edit_index'),
    url(r'^enemy_template/(?P<enemy_template_id>\d+)/$', views.enemy_template, name='enemy_template'),
    url(r'^race/(?P<race_id>\d+)/$', views.race, name='race'),
    url(r'^party/(?P<party_id>\d+)/$', views.party, name='party'),
    url(r'^instructions/$', views.instructions, name='instructions'),
    url(r'^statistics/$', views.statistics, name='statistics'),
    url(r'^disclaimer/$', views.disclaimer, name='disclaimer'),

    url(r'^pdf_export/$', views.pdf_export, name='pdf_export'),
    url(r'^delete_template/(?P<template_id>\d+)/$', views.delete_template, name='delete_template'),
    url(r'^clone_race/(?P<race_id>\d+)/$', views.clone_race, name='clone_race'),
    url(r'^clone_template/(?P<template_id>\d+)/$', views.clone_template, name='clone_template'),
    url(r'^create_enemy_template/$', views.create_enemy_template, name='create_enemy_template'),
    url(r'^apply_skill_bonus/(?P<template_id>\d+)/$', views.apply_skill_bonus, name='apply_skill_bonus'),
    url(r'^create_race/$', views.create_race, name='create_race'),
    url(r'^delete_party/(?P<party_id>\d+)/$', views.delete_party, name='delete_party'),
    url(r'^delete_race/(?P<race_id>\d+)/$', views.delete_race, name='delete_race'),
    url(r'^ruleset/(?P<ruleset_id>\d+)/$', views.ruleset, name='ruleset'),
    url(r'^create_party/$', views.create_party, name='create_party'),
    url(r'^add_template_to_party/$', views.add_template_to_party, name='add_template_to_party'),
)
