from django.urls import re_path as url
from django.conf import settings

from enemygen import views
from enemygen import ajax

try:
    ROOT = settings.WEB_ROOT
except:
    ROOT = ''

urlpatterns = [
    url('^' + ROOT + r'$', views.home, name='home'),
    url('^' + ROOT + r'enemies/$', views.index, name='index'),
    url('^' + ROOT + r'simple_index/$', views.simple_index),
    url('^' + ROOT + r'index_json/$', views.index_json),
    url('^' + ROOT + r'parties/$', views.party_index, name='party_index'),
    url('^' + ROOT + r'party_index/$', views.party_index),  # Old one. Kept in case somebody has bookmarked it
    url('^' + ROOT + r'party_index_json/$', views.party_index_json),
    url('^' + ROOT + r'generate_enemies/$', views.generate_enemies, name='generate_enemies'),
    url('^' + ROOT + r'generate_party/$', views.generate_party, name='generate_party'),
    url('^' + ROOT + r'edit_index/$', views.edit_index, name='edit_index'),
    url('^' + ROOT + r'enemy_template/(?P<enemy_template_id>\d+)/$', views.enemy_template, name='enemy_template'),
    url('^' + ROOT + r'race/(?P<race_id>\d+)/$', views.race, name='race'),
    url('^' + ROOT + r'party/(?P<party_id>\d+)/$', views.party, name='party'),
    url('^' + ROOT + r'instructions/$', views.instructions, name='instructions'),
    url('^' + ROOT + r'statistics/$', views.statistics, name='statistics'),
    url('^' + ROOT + r'about/$', views.about, name='about'),
    url('^' + ROOT + r'whats_new/$', views.whats_new, name='whats_new'),
    url('^' + ROOT + r'account/$', views.account, name='account'),
    url('^' + ROOT + r'set_filter/$', views.set_filter, name='set_filter'),
    url('^' + ROOT + r'set_party_filter/$', views.set_party_filter, name='set_party_filter'),
    url('^' + ROOT + r'feature_items/(?P<feature_id>\d+)/$', views.feature_items, name='feature_items'),
    url('^' + ROOT + r'generate_enemies_json/$', views.generate_enemies_json),
    url('^' + ROOT + r'generate_party_json/$', views.generate_party_json),

    url('^' + ROOT + r'pdf_export/$', views.pdf_export, name='pdf_export'),
    url('^' + ROOT + r'png_export/$', views.png_export, name='png_export'),
    url('^' + ROOT + r'delete_template/(?P<template_id>\d+)/$', views.delete_template, name='delete_template'),
    url('^' + ROOT + r'race_index/$', views.race_index, name='race_index'),
    url('^' + ROOT + r'clone_race/(?P<race_id>\d+)/$', views.clone_race, name='clone_race'),
    url('^' + ROOT + r'clone_template/(?P<template_id>\d+)/$', views.clone_template, name='clone_template'),
    url('^' + ROOT + r'clone_party/(?P<party_id>\d+)/$', views.clone_party, name='clone_party'),
    url('^' + ROOT + r'create_enemy_template/$', views.create_enemy_template, name='create_enemy_template'),
    url('^' + ROOT + r'apply_skill_bonus/(?P<template_id>\d+)/$', views.apply_skill_bonus, name='apply_skill_bonus'),
    url('^' + ROOT + r'create_cult/$', views.create_cult, name='create_cult'),
    url('^' + ROOT + r'create_race/$', views.create_race, name='create_race'),
    url('^' + ROOT + r'delete_party/(?P<party_id>\d+)/$', views.delete_party, name='delete_party'),
    url('^' + ROOT + r'create_party/$', views.create_party, name='create_party'),

    url('^' + ROOT + r'rest/toggle_star/(?P<et_id>\d+)/$', ajax.toggle_star, name='toggle_star'),
    url('^' + ROOT + r'rest/get_weapons/(?P<cs_id>\d+)/$', ajax.get_weapons, name='get_weapons'),
    url('^' + ROOT + r'rest/search/$', ajax.search, name='search'),
    url('^' + ROOT + r'rest/submit/(?P<id>\d+)/$', ajax.submit, name='submit'),
    url('^' + ROOT + r'rest/change_template/$', ajax.change_template, name='change_template'),
    url('^' + ROOT + r'rest/add_additional_feature/(?P<parent_id>\d+)/$', ajax.add_additional_feature, name='add_additional_feature'),
    url('^' + ROOT + r'rest/get_feature_list_items/(?P<list_id>\d+)/$', ajax.get_feature_list_items, name='get_feature_list_items'),
    url('^' + ROOT + r'rest/del_item/(?P<item_id>\d+)/(?P<item_type>[a-z_]+)/$', ajax.del_item, name='del_item'),
    url('^' + ROOT + r'rest/add_custom_weapon/(?P<cs_id>\d+)/(?P<type>[\da-z_-]+)/$', ajax.add_custom_weapon, name='add_custom_weapon'),
    url('^' + ROOT + r'rest/add_nonrandom_feature/(?P<feature_id>\d+)/$', ajax.add_nonrandom_feature, name='add_nonrandom_feature'),
    url('^' + ROOT + r'rest/add_template_to_party/(?P<party_id>\d+)/$', ajax.add_template_to_party, name='add_template_to_party'),
    url('^' + ROOT + r'rest/add_hit_location/(?P<race_id>\d+)/$', ajax.add_hit_location, name='add_hit_location'),
    url('^' + ROOT + r'rest/add_cult/(?P<et_id>\d+)/$', ajax.add_cult, name='add_cult'),
    url('^' + ROOT + r'rest/add_spirit/(?P<et_id>\d+)/$', ajax.add_spirit, name='add_spirit'),
    url('^' + ROOT + r'rest/add_custom_skill/(?P<et_id>\d+)/$', ajax.add_custom_skill, name='add_custom_skill'),
    url('^' + ROOT + r'rest/add_custom_spell/(?P<et_id>\d+)/(?P<type>[\da-z_-]+)/$', ajax.add_custom_spell, name='add_custom_spell'),
    url('^' + ROOT + r'rest/apply_notes_to_templates/(?P<race_id>\d+)/$', ajax.apply_notes_to_templates, name='apply_notes_to_templates'),
]
