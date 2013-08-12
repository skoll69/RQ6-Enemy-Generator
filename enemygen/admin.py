from django.contrib import admin
from enemygen.models import EnemyTemplate, Setting, Ruleset, Race, HitLocation
from enemygen.models import SkillAbstract, SpellAbstract, StatAbstract, Weapon
from enemygen.models import EnemySkill, EnemySpell, EnemyStat, EnemyHitLocation, RaceStat
from enemygen.models import CombatStyle

class EnemyTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'ruleset', 'setting', 'race', 'rank', 'generated', 'published', 'owner')

class StatAbstractAdmin(admin.ModelAdmin):
    list_display = ('name',)

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

class HitLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'range', 'race', 'hp_modifier')
    list_filter = ('race',)
    ordering = ('race', 'range_start',)

admin.site.register(EnemyTemplate, EnemyTemplateAdmin)
admin.site.register(Setting)
admin.site.register(CombatStyle)
admin.site.register(Ruleset)
admin.site.register(Race)
admin.site.register(Weapon, WeaponAdmin)
admin.site.register(RaceStat, RaceStatAdmin)
admin.site.register(HitLocation, HitLocationAdmin)
admin.site.register(SkillAbstract, SkillAbstractAdmin)
admin.site.register(EnemySkill, EnemySkillAdmin)
admin.site.register(EnemyHitLocation, EnemyHitLocationAdmin)
admin.site.register(StatAbstract, StatAbstractAdmin)
admin.site.register(EnemyStat, EnemyStatAdmin)
admin.site.register(SpellAbstract, SpellAbstractAdmin)
admin.site.register(EnemySpell, EnemySpellAdmin)