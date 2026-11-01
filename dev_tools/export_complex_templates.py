"""
Export complex templates for testing generation classes.
"""
import django
import os
import json

os.environ['DJANGO_SETTINGS_MODULE'] = 'mythras_eg.settings'
django.setup()

from django.core import serializers
from enemygen.models import (
    EnemyTemplate, Race, Ruleset, EnemyStat, StatAbstract,
    EnemySkill, SkillAbstract, CustomSkill,
    EnemySpell, SpellAbstract, CustomSpell,
    EnemySpirit, EnemyCult,
    CombatStyle, Weapon, EnemyWeapon, CustomWeapon,
    HitLocation, EnemyHitLocation,
    AdditionalFeatureList, AdditionalFeatureItem,
    EnemyAdditionalFeatureList, EnemyNonrandomFeature,
)

# Templates to export - start with these
initial_template_ids = [
    973,    # Air Spirit Intensity 1 (Spirit)
    1162,   # Air Elemental (Elemental)
    8431,   # Hanjethulut (Cult)
    9531,   # Cultist of Ojahl Acolyte (Priest with cult)
    2089,   # 7 Mothers - Jakaleel the Witch Acolyte (Priest with cult)
    520,    # Agimori Shaman2 (Shaman with spirits)
    532,    # Thanatari Priest (Shaman with Binding)
    68,     # Human Sorcerer Apprentice (Sorcerer)
    995,    # Mystic (Mystic with Mysticism+Meditation)
]

# Collect all template IDs including dependencies
template_ids = set(initial_template_ids)
changed = True
while changed:
    changed = False
    for t in EnemyTemplate.objects.filter(id__in=template_ids):
        # Spirits reference other templates
        for es in t.spirits.all():
            if es.spirit_id not in template_ids:
                template_ids.add(es.spirit_id)
                changed = True
        # Cults reference other templates
        for ec in t.cults.all():
            if ec.cult_id not in template_ids:
                template_ids.add(ec.cult_id)
                changed = True

templates = EnemyTemplate.objects.filter(id__in=template_ids)
print(f"Found {templates.count()} templates (including dependencies)")

# Collect all related objects
races = set()
rulesets = set()
skill_abstracts = set()
spell_abstracts = set()
feature_lists = set()
combat_styles = set()
weapons = set()

for t in templates:
    races.add(t.race_id)
    rulesets.add(t.ruleset_id)
    if t.namelist:
        feature_lists.add(t.namelist_id)
    
    # Skills
    for es in t.enemyskill_set.all():
        skill_abstracts.add(es.skill_id)
    
    # Spells
    for es in t.enemyspell_set.all():
        spell_abstracts.add(es.spell_id)
    
    # Spirits
    for es in t.spirits.all():
        races.add(es.spirit.race_id)
        # Add the spirit template too
        templates = list(templates)  # Convert to list to avoid modification
    
    # Cults
    for ec in t.cults.all():
        races.add(ec.cult.race_id)
    
    # Feature lists
    for efl in t.enemyadditionalfeaturelist_set.all():
        feature_lists.add(efl.feature_list_id)
    
    # Non-random features
    for enrf in t.enemynonrandomfeature_set.all():
        feature_lists.add(enrf.feature.feature_list_id)
    
    # Combat styles
    for cs in t.combatstyle_set.all():
        combat_styles.add(cs.id)
        for ew in cs.enemyweapon_set.all():
            weapons.add(ew.weapon_id)

print(f"Races: {len(races)}")
print(f"Skill abstracts: {len(skill_abstracts)}")
print(f"Spell abstracts: {len(spell_abstracts)}")
print(f"Feature lists: {len(feature_lists)}")

# Get all user IDs referenced
user_ids = set(t.owner_id for t in templates if t.owner_id)

# Serialize
from django.contrib.auth.models import User, Group
objects = []
# Groups first (users reference them)
objects.extend(Group.objects.filter(user__id__in=user_ids))
objects.extend(User.objects.filter(id__in=user_ids))
objects.extend(EnemyTemplate.objects.filter(id__in=template_ids))
objects.extend(Race.objects.filter(id__in=races))
objects.extend(Ruleset.objects.filter(id__in=rulesets))
objects.extend(StatAbstract.objects.all())  # All stats are shared
objects.extend(SkillAbstract.objects.filter(id__in=skill_abstracts))
objects.extend(SpellAbstract.objects.filter(id__in=spell_abstracts))
objects.extend(AdditionalFeatureList.objects.filter(id__in=feature_lists))
objects.extend(CombatStyle.objects.filter(id__in=combat_styles))
objects.extend(Weapon.objects.filter(id__in=weapons))
objects.extend(HitLocation.objects.filter(race_id__in=races))

# Related objects
for t in EnemyTemplate.objects.filter(id__in=template_ids):
    objects.extend(t.enemystat_set.all())
    objects.extend(t.enemyskill_set.all())
    objects.extend(t.enemyspell_set.all())
    objects.extend(t.enemyhitlocation_set.all())
    objects.extend(t.spirits.all())
    objects.extend(t.cults.all())
    objects.extend(t.enemyadditionalfeaturelist_set.all())
    objects.extend(t.enemynonrandomfeature_set.all())
    objects.extend(t.combatstyle_set.all())
    for cs in t.combatstyle_set.all():
        objects.extend(cs.enemyweapon_set.all())

# Get feature list items
for fl in AdditionalFeatureList.objects.filter(id__in=feature_lists):
    objects.extend(fl.items.all())

# Get race stats
for r in Race.objects.filter(id__in=races):
    objects.extend(r.stats.all())

data = serializers.serialize('json', objects, indent=2)
with open('enemygen/tests/complex_templates.json', 'w') as f:
    f.write(data)

print(f"Exported {len(objects)} objects to complex_templates.json")
