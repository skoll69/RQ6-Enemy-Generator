from django.contrib import admin
from django import forms
from enemygen.models import EnemyTemplate, Ruleset, Race, HitLocation
from enemygen.models import SkillAbstract, SpellAbstract, StatAbstract, Weapon
from enemygen.models import EnemySkill, EnemySpell, EnemyStat, EnemyHitLocation, RaceStat
from enemygen.models import CombatStyle, CustomSpell, CustomWeapon, Party, TemplateToParty
from enemygen.models import EnemySpirit, ChangeLog
from enemygen.models import EnemyAdditionalFeatureList, AdditionalFeatureList, AdditionalFeatureItem

class EnemyTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'race', 'rank', 'generated', 'published', 'owner')
    list_filter = ('owner',)

class RaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'published')

class ChangeLogForm(forms.ModelForm):
    class Meta:
        model = ChangeLog
        widgets = {'description': forms.Textarea}
    
class ChangeLogAdmin(admin.ModelAdmin):
    list_display = ('publish_date', 'name')
    form = ChangeLogForm
    
class StatAbstractAdmin(admin.ModelAdmin):
    list_display = ('name',)
    
class AdditionalFeatureItemForm(forms.ModelForm):
    class Meta:
        model = AdditionalFeatureItem
        widgets = {'name': forms.Textarea}
    
class AdditionalFeatureItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'feature_list')
    form = AdditionalFeatureItemForm
    list_filter = ('feature_list',)
    
class CombatStyleAdmin(admin.ModelAdmin):
    list_display = ('name', 'enemy_template', 'one_h_amount', 'two_h_amount', 'ranged_amount', 'shield_amount')
    
class SkillAbstractAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_value', 'standard')
    list_filter = ('standard',)
    
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
    list_display = ('enemy_template', 'hit_location', )

class WeaponAdmin(admin.ModelAdmin):
    list_display = ('name', 'damage', 'type')
    ordering = ('type', 'name')

class PartyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner')
    ordering = ('name',)

class HitLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'range', 'race', 'hp_modifier')
    list_filter = ('race',)
    ordering = ('race', 'range_start',)

admin.site.register(EnemyTemplate, EnemyTemplateAdmin)
admin.site.register(Weapon, WeaponAdmin)
admin.site.register(CombatStyle, CombatStyleAdmin)
admin.site.register(Ruleset)
admin.site.register(EnemySpirit)
admin.site.register(Race, RaceAdmin)
admin.site.register(CustomSpell)
admin.site.register(CustomWeapon)
admin.site.register(TemplateToParty)
admin.site.register(AdditionalFeatureList)
admin.site.register(AdditionalFeatureItem, AdditionalFeatureItemAdmin)
admin.site.register(EnemyAdditionalFeatureList)
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