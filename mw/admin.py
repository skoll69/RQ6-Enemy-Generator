from django.contrib import admin
from django import forms
from mw import models as m


class EnemyTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'rank', 'generated', 'published', 'owner')
    list_filter = ('owner', )
    search_fields = ['name', ]


class ChangeLogForm(forms.ModelForm):
    class Meta:
        model = m.ChangeLog
        widgets = {'description': forms.Textarea}


class ChangeLogAdmin(admin.ModelAdmin):
    list_display = ('publish_date', 'name')
    form = ChangeLogForm


class StatAbstractAdmin(admin.ModelAdmin):
    list_display = ('name',)


class CombatStyleAdmin(admin.ModelAdmin):
    list_display = ('enemy_template', 'one_h_amount', 'two_h_amount', 'ranged_amount', 'shield_amount')


class CustomWeaponAdmin(admin.ModelAdmin):
    list_display = ('name', 'damage')


class SkillAbstractAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_value')


class SpellAbstractAdmin(admin.ModelAdmin):
    list_display = ('name', )
    ordering = ('name', )


class EnemySkillAdmin(admin.ModelAdmin):
    list_display = ('skill', 'enemy_template', 'die_set')
    list_filter = ('enemy_template',)


class EnemyWeaponAdmin(admin.ModelAdmin):
    list_display = ('die_set', 'weapon')


class EnemyStatAdmin(admin.ModelAdmin):
    list_display = ('stat', 'enemy_template', 'die_set')
    list_filter = ('enemy_template',)
    ordering = ('enemy_template', 'stat',)


class EnemySpellAdmin(admin.ModelAdmin):
    list_display = ('enemy_template', 'spell', 'probability')


class WeaponAdmin(admin.ModelAdmin):
    list_display = ('name', 'damage', 'type')
    ordering = ('type', 'name')


class PartyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner')
    ordering = ('name',)


class StarAdmin(admin.ModelAdmin):
    list_display = ('user', 'template')


admin.site.register(m.MWEnemyTemplate, EnemyTemplateAdmin)
admin.site.register(m.Weapon, WeaponAdmin)
admin.site.register(m.CombatStyle, CombatStyleAdmin)
admin.site.register(m.CustomSpell)
admin.site.register(m.CustomSkill)
admin.site.register(m.CustomWeapon, CustomWeaponAdmin)
admin.site.register(m.TemplateToParty)
admin.site.register(m.MWParty, PartyAdmin)
admin.site.register(m.ChangeLog, ChangeLogAdmin)
admin.site.register(m.SkillAbstract, SkillAbstractAdmin)
admin.site.register(m.EnemySkill, EnemySkillAdmin)
admin.site.register(m.StatAbstract, StatAbstractAdmin)
admin.site.register(m.EnemyStat, EnemyStatAdmin)
admin.site.register(m.SpellAbstract, SpellAbstractAdmin)
admin.site.register(m.EnemySpell, EnemySpellAdmin)
admin.site.register(m.EnemyWeapon, EnemyWeaponAdmin)
admin.site.register(m.Star, StarAdmin)
