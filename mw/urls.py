from django.conf.urls import patterns, url

from mw import views

urlpatterns = patterns('',
    url(r'^$', views.home, name='mw_home'),
    url(r'^enemies/$', views.index, name='mw_index'),
    url(r'^parties/$', views.party_index, name='mw_party_index'),
    url(r'^generate_enemies/$', views.generate_enemies, name='mw_generate_enemies'),
    url(r'^generate_party/$', views.generate_party, name='mw_generate_party'),
    url(r'^edit_index/$', views.edit_index, name='mw_edit_index'),
    url(r'^enemy_template/(?P<enemy_template_id>\d+)/$', views.enemy_template, name='mw_enemy_template'),
    url(r'^party/(?P<party_id>\d+)/$', views.party, name='mw_party'),
    url(r'^instructions/$', views.instructions, name='mw_instructions'),
    url(r'^statistics/$', views.statistics, name='mw_statistics'),
    url(r'^about/$', views.about, name='mw_about'),
    url(r'^whats_new/$', views.whats_new, name='mw_whats_new'),
    url(r'^set_filter/$', views.set_filter, name='mw_set_filter'),
    url(r'^set_party_filter/$', views.set_party_filter, name='mw_set_party_filter'),

    url(r'^pdf_export/$', views.pdf_export, name='mw_pdf_export'),
    url(r'^png_export/$', views.png_export, name='mw_png_export'),
    url(r'^delete_template/(?P<template_id>\d+)/$', views.delete_template, name='mw_delete_template'),
    url(r'^clone_template/(?P<template_id>\d+)/$', views.clone_template, name='mw_clone_template'),
    url(r'^clone_party/(?P<party_id>\d+)/$', views.clone_party, name='mw_clone_party'),
    url(r'^create_enemy_template/$', views.create_enemy_template, name='mw_create_enemy_template'),
    url(r'^apply_skill_bonus/(?P<template_id>\d+)/$', views.apply_skill_bonus, name='mw_apply_skill_bonus'),
    url(r'^delete_party/(?P<party_id>\d+)/$', views.delete_party, name='mw_delete_party'),
    url(r'^create_party/$', views.create_party, name='mw_create_party'),
)
