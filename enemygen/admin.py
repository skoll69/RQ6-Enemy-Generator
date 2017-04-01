from django.contrib import admin
from django import forms
from enemygen.models import EnemyTemplate, Race, HitLocation
from enemygen.models import SkillAbstract, SpellAbstract, StatAbstract, Weapon
from enemygen.models import EnemySkill, EnemySpell, EnemyStat, EnemyHitLocation, RaceStat
from enemygen.models import CombatStyle, Party, ChangeLog
from enemygen.models import AdditionalFeatureList, AdditionalFeatureItem, Star
from enemygen import models as m

class EnemyTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'race', 'rank', 'generated', 'published', 'owner')
    list_filter = ('owner',)
    search_fields = ['name',]
    
class RaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'published')
    search_fields = ['name',]

class AdditionalFeatureListAdmin(admin.ModelAdmin):
    list_display = ('name', 'type')
    list_filter = ('type',)

class ChangeLogForm(forms.ModelForm):
    class Meta:
        model = ChangeLog
        widgets = {'description': forms.Textarea}
        fields = '__all__'
    
class ChangeLogAdmin(admin.ModelAdmin):
    list_display = ('publish_date', 'name')
    form = ChangeLogForm
    
class StatAbstractAdmin(admin.ModelAdmin):
    list_display = ('name',)
    
class AdditionalFeatureItemForm(forms.ModelForm):
    class Meta:
        model = AdditionalFeatureItem
        widgets = {'name': forms.Textarea}
        fields = '__all__'
    
class AdditionalFeatureItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'feature_list')
    form = AdditionalFeatureItemForm
    list_filter = ('feature_list',)

class EnemyAdditionalFeatureListAdmin(admin.ModelAdmin):
    list_display = ('enemy_template', 'feature_list', 'probability')
    list_filter = ('feature_list',)
    search_fields = ('enemy_template__name', 'feature_list__name')
    
class CombatStyleAdmin(admin.ModelAdmin):
    list_display = ('name', 'enemy_template', 'one_h_amount', 'two_h_amount', 'ranged_amount', 'shield_amount')
    
class CustomWeaponAdmin(admin.ModelAdmin):
    list_display = ('name', 'damage', 'special_effects')
    
class SkillAbstractAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_value', 'standard', 'magic')
    list_filter = ('standard', 'magic')
    
class SpellAbstractAdmin(admin.ModelAdmin):
    list_display = ('name', 'type')
    list_filter = ('type',)
    ordering = ('type', 'name')

class EnemySkillAdmin(admin.ModelAdmin):
    list_display = ('skill', 'enemy_template', 'die_set')
    list_filter = ('enemy_template',)

class EnemyStatAdmin(admin.ModelAdmin):
    list_display = ('stat', 'enemy_template', 'die_set')
    list_filter = ('enemy_template',)
    ordering = ('enemy_template', 'stat',)
    
class EnemySpellAdmin(admin.ModelAdmin):
    list_display = ('enemy_template', 'spell', 'probability')

class RaceStatAdmin(admin.ModelAdmin):
    list_display = ('race', 'stat', 'default_value')
    list_filter = ('race', 'stat')

class EnemyHitLocationAdmin(admin.ModelAdmin):
    list_display = ('enemy_template', 'hit_location',)
    search_fields = ['enemy_template__name',]

class WeaponAdmin(admin.ModelAdmin):
    list_display = ('name', 'damage', 'type', 'tag_names', 'special_effects')
    ordering = ('type', 'name')
    def tag_names(self, obj):
        return ', '.join(obj.tags.names())

class PartyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner')
    ordering = ('name',)

class StarAdmin(admin.ModelAdmin):
    list_display = ('user', 'template')

class HitLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'range', 'race', 'hp_modifier', 'armor')
    list_filter = ('race',)
    ordering = ('race', 'range_start',)

admin.site.register(EnemyTemplate, EnemyTemplateAdmin)
admin.site.register(Weapon, WeaponAdmin)
admin.site.register(CombatStyle, CombatStyleAdmin)
admin.site.register(Race, RaceAdmin)
admin.site.register(m.Ruleset)
admin.site.register(m.EnemySpirit)
admin.site.register(m.CustomSpell)
admin.site.register(m.CustomSkill)
admin.site.register(m.CustomWeapon, CustomWeaponAdmin)
admin.site.register(m.TemplateToParty)
admin.site.register(m.EnemyNonrandomFeature)
admin.site.register(AdditionalFeatureList, AdditionalFeatureListAdmin)
admin.site.register(AdditionalFeatureItem, AdditionalFeatureItemAdmin)
admin.site.register(m.EnemyAdditionalFeatureList, EnemyAdditionalFeatureListAdmin)
admin.site.register(m.PartyAdditionalFeatureList)
admin.site.register(Party, PartyAdmin)
admin.site.register(ChangeLog, ChangeLogAdmin)
admin.site.register(RaceStat, RaceStatAdmin)
admin.site.register(HitLocation, HitLocationAdmin)
admin.site.register(SkillAbstract, SkillAbstractAdmin)
admin.site.register(EnemySkill, EnemySkillAdmin)
admin.site.register(EnemyHitLocation, EnemyHitLocationAdmin)
admin.site.register(StatAbstract, StatAbstractAdmin)
admin.site.register(EnemyStat, EnemyStatAdmin)
admin.site.register(SpellAbstract, SpellAbstractAdmin)
admin.site.register(EnemySpell, EnemySpellAdmin)
admin.site.register(Star, StarAdmin)
admin.site.register(m.EnemyCult)