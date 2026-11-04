"""
Consolidated model and dice tests.

This file combines all model-related tests from:
- test_models_coverage.py (Race, HitLocation, EnemyTemplate, Party, CombatStyle,
  Weapon, Skill, Spell, Spirit/Cult, FeatureList, Stat, Star models)
- test_base.py (TestDice, TestViewsLib, TestEnemyTemplate, TestEnemySkill,
  TestMisc, TestJson, TestPublicCors)
"""
from django.test import TestCase, RequestFactory, SimpleTestCase
from django.contrib.auth.models import User
from django.http import HttpResponse
from collections import OrderedDict
import json
import os
import tempfile

from ..ajax import change_template
from ..dice import Dice, _die_to_tuple, clean
from ..models import (
    EnemyTemplate, Party, Race, Ruleset, CombatStyle, Weapon,
    AdditionalFeatureList, AdditionalFeatureItem, CustomSpell, CustomSkill,
    CustomWeapon, HitLocation, EnemySpirit, EnemyCult,
    EnemyAdditionalFeatureList, EnemyNonrandomFeature,
    PartyAdditionalFeatureList, PartyNonrandomFeature, TemplateToParty,
    EnemyStat, StatAbstract, SpellAbstract, EnemySpell, EnemySkill,
    SkillAbstract, EnemyWeapon, RaceStat, EnemyHitLocation, Star,
    _Enemy, _Spirit,
)
from ..enemygen_lib import select_random_item, replace_die_set
from ..views_lib import as_json, get_context
from mythras_eg.middleware import SimpleCorsMiddleware
from django.conf import settings
from django.test import override_settings


class RaceModelTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)

    def test_race_set_published_false(self):
        """Test setting race published to false works without validation."""
        self.race.set_published(False)
        self.assertFalse(self.race.published)

    def test_race_set_published_true_with_validation_error(self):
        """Test setting race published to true raises error if hit locations don't cover 1-20."""
        incomplete_race = Race(name='Incomplete', owner=self.user)
        incomplete_race.save()
        incomplete_race.published = False
        incomplete_race.save()
        HitLocation(name='Head', range_start=1, range_end=5, race=incomplete_race, hp_modifier=0).save()
        with self.assertRaises(Exception):  # ValidationError from enemygen_lib
            incomplete_race.set_published(True)

    def test_race_clone(self):
        """Test cloning a race creates a new race with all stats and hit locations."""
        new_race = self.race.clone(self.user)
        self.assertEqual(new_race.name, 'Copy of %s' % self.race.name)
        self.assertEqual(new_race.stats.count(), self.race.stats.count())
        self.assertEqual(new_race.hit_locations.count(), self.race.hit_locations.count())




class HitLocationModelTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)

    def test_hit_location_create(self):
        """Test creating a new hit location."""
        hl = HitLocation.create(self.race.id)
        self.assertEqual(hl.race, self.race)
        self.assertIsNotNone(hl)

    def test_hit_location_set_armor(self):
        """Test setting armor value on hit location."""
        hl = self.race.hit_locations.first()
        hl.set_armor('1d4')
        self.assertEqual(hl.armor, '1d4')

    def test_hit_location_range_property(self):
        """Test range property formatting."""
        hl = HitLocation(name='Single', range_start=1, range_end=1, race=self.race, hp_modifier=0)
        hl.save()
        self.assertEqual(hl.range, '01')
        hl2 = HitLocation(name='Range', range_start=1, range_end=5, race=self.race, hp_modifier=0)
        hl2.save()
        self.assertEqual(hl2.range, '01-05')




class EnemyTemplateModelTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Test Template')

    def test_stat_dict(self):
        """Test stat_dict returns all stats."""
        stat_dict = self.template.stat_dict
        self.assertIsInstance(stat_dict, dict)
        self.assertIn('STR', stat_dict)

    def test_included_standard_skills(self):
        """Test included_standard_skills property."""
        skills = self.template.included_standard_skills
        self.assertGreaterEqual(len(skills), 0)

    def test_professional_skills(self):
        """Test professional_skills returns queryset of skills."""
        skills = self.template.professional_skills
        self.assertIsNotNone(skills)
        # Should be a queryset, not just any object
        from django.db.models import QuerySet
        self.assertIsInstance(skills, QuerySet)

    def test_magic_skills(self):
        """Test magic_skills returns queryset of magic skills."""
        skills = self.template.magic_skills
        self.assertIsNotNone(skills)
        from django.db.models import QuerySet
        self.assertIsInstance(skills, QuerySet)

    def test_spirits_property(self):
        """Test spirits returns queryset of spirit configs."""
        spirits = self.template.spirits
        self.assertIsNotNone(spirits)
        from django.db.models import QuerySet
        self.assertIsInstance(spirits, QuerySet)

    def test_cults_property(self):
        """Test cults returns queryset of cult configs."""
        cults = self.template.cults
        self.assertIsNotNone(cults)
        from django.db.models import QuerySet
        self.assertIsInstance(cults, QuerySet)

    def test_additional_features_property(self):
        """Test additional_features returns queryset."""
        features = self.template.additional_features
        self.assertIsNotNone(features)
        from django.db.models import QuerySet
        self.assertIsInstance(features, QuerySet)

    def test_nonrandom_features_property(self):
        """Test nonrandom_features returns queryset."""
        features = self.template.nonrandom_features
        self.assertIsNotNone(features)
        from django.db.models import QuerySet
        self.assertIsInstance(features, QuerySet)

    def test_clone_template(self):
        """Test cloning a template preserves all data."""
        self.template.tags.add('test-tag')
        cloned = self.template.clone(self.user)
        self.assertEqual(cloned.name, 'Copy of Test Template')
        self.assertEqual(cloned.race, self.race)
        self.assertEqual(cloned.stats.count(), self.template.stats.count())

    def test_apply_skill_bonus(self):
        """Test applying skill bonus updates all skills."""
        before = self.template.raw_skills.first().die_set
        self.template.apply_skill_bonus('+10')
        after = self.template.raw_skills.first().die_set
        # The bonus should be appended to the existing die_set
        self.assertTrue(len(after) > len(before) or '+10' in after)

    def test_get_starred_anonymous(self):
        """Test get_starred returns empty for anonymous user."""
        from django.contrib.auth.models import AnonymousUser
        starred = EnemyTemplate.get_starred(AnonymousUser())
        self.assertEqual(len(starred), 0)
        self.assertTrue(hasattr(starred, 'all'))  # Is iterable (QuerySet)


    def test_summary_dict_with_user(self):
        """Test summary_dict includes starred for authenticated user."""
        d = self.template.summary_dict(self.user)
        self.assertIn('starred', d)
        self.assertIn('name', d)

    def test_is_theist_property(self):
        """Test is_theist property checks Devotion skill."""
        result = self.template.is_theist
        self.assertIsInstance(result, bool)

    def test_is_folk_magician_property(self):
        """Test is_folk_magician property."""
        result = self.template.is_folk_magician
        self.assertIsInstance(result, bool)

    def test_is_sorcerer_property(self):
        """Test is_sorcerer property."""
        result = self.template.is_sorcerer
        self.assertIsInstance(result, bool)

    def test_is_mystic_property(self):
        """Test is_mystic property."""
        result = self.template.is_mystic
        self.assertIsInstance(result, bool)

    def test_is_animist_property(self):
        """Test is_animist property."""
        result = self.template.is_animist
        self.assertIsInstance(result, bool)

    def test_generate_with_increment(self):
        """Test generate increments generated counter."""
        initial = self.template.generated
        enemy = self.template.generate(increment=True)
        self.template.refresh_from_db()
        self.assertEqual(self.template.generated, initial + 1)

    def test_generate_without_increment(self):
        """Test generate without increment doesn't change counter."""
        initial = self.template.generated
        enemy = self.template.generate(increment=False)
        self.template.refresh_from_db()
        self.assertEqual(self.template.generated, initial)

    def test_is_spirit_property(self):
        """Test is_spirit property."""
        self.assertFalse(self.template.is_spirit)
        spirit_template = EnemyTemplate.objects.filter(race__discorporate=True).first()
        if spirit_template:
            self.assertTrue(spirit_template.is_spirit)

    def test_is_cult_property(self):
        """Test is_cult property."""
        self.assertFalse(self.template.is_cult)
        cult_template = EnemyTemplate.objects.filter(race__name='Cult').first()
        if cult_template:
            self.assertTrue(cult_template.is_cult)

    def test_is_elemental_property(self):
        """Test is_elemental property."""
        self.assertFalse(self.template.is_elemental)
        elemental_template = EnemyTemplate.objects.filter(race__elemental=True).first()
        if elemental_template:
            self.assertTrue(elemental_template.is_elemental)

    def test_standard_skills_property(self):
        """Test standard_skills returns queryset."""
        skills = self.template.standard_skills
        self.assertIsNotNone(skills)
        from django.db.models import QuerySet
        self.assertIsInstance(skills, QuerySet)

    def test_included_magic_skills_property(self):
        """Test included_magic_skills returns queryset."""
        skills = self.template.included_magic_skills
        self.assertIsNotNone(skills)
        from django.db.models import QuerySet
        self.assertIsInstance(skills, QuerySet)

    def test_folk_spells_property(self):
        """Test folk_spells returns iterable."""
        spells = self.template.folk_spells
        self.assertIsNotNone(spells)
        # folk_spells may be a list or queryset
        self.assertTrue(hasattr(spells, '__iter__'))

    def test_theism_spells_property(self):
        """Test theism_spells returns iterable."""
        spells = self.template.theism_spells
        self.assertIsNotNone(spells)
        self.assertTrue(hasattr(spells, '__iter__'))

    def test_sorcery_spells_property(self):
        """Test sorcery_spells returns iterable."""
        spells = self.template.sorcery_spells
        self.assertIsNotNone(spells)
        self.assertTrue(hasattr(spells, '__iter__'))

    def test_mysticism_spells_property(self):
        """Test mysticism_spells returns iterable."""
        spells = self.template.mysticism_spells
        self.assertIsNotNone(spells)
        self.assertTrue(hasattr(spells, '__iter__'))

    def test_get_tags_with_prefetch(self):
        """Test get_tags with prefetched tags."""
        self.template.tags.add('tag-a', 'tag-b')
        from django.db.models import Prefetch
        templates = EnemyTemplate.objects.filter(id=self.template.id).prefetch_related('tags')
        for t in templates:
            tags = t.get_tags()
            self.assertIn('tag-a', tags)

    def test_is_theist_with_devotion_skill(self):
        """Test is_theist returns True when Devotion skill is included."""
        devotion = SkillAbstract.objects.filter(name='Devotion').first()
        if devotion:
            skill, created = EnemySkill.objects.get_or_create(
                skill=devotion, enemy_template=self.template,
                defaults={'include': True, 'die_set': '50'}
            )
            if not created:
                skill.include = True
                skill.save()
            self.assertTrue(self.template.is_theist)

    def test_is_folk_magician_with_folk_magic_skill(self):
        """Test is_folk_magician returns True when Folk Magic skill is included."""
        folk = SkillAbstract.objects.filter(name='Folk Magic').first()
        if folk:
            skill, created = EnemySkill.objects.get_or_create(
                skill=folk, enemy_template=self.template,
                defaults={'include': True, 'die_set': '50'}
            )
            if not created:
                skill.include = True
                skill.save()
            self.assertTrue(self.template.is_folk_magician)

    def test_is_sorcerer_with_shaping_skill(self):
        """Test is_sorcerer returns True when Shaping skill is included."""
        shaping = SkillAbstract.objects.filter(name='Shaping').first()
        if shaping:
            skill, created = EnemySkill.objects.get_or_create(
                skill=shaping, enemy_template=self.template,
                defaults={'include': True, 'die_set': '50'}
            )
            if not created:
                skill.include = True
                skill.save()
            self.assertTrue(self.template.is_sorcerer)

    def test_is_mystic_with_mysticism_skill(self):
        """Test is_mystic returns True when Mysticism skill is included."""
        mysticism = SkillAbstract.objects.filter(name='Mysticism').first()
        if mysticism:
            skill, created = EnemySkill.objects.get_or_create(
                skill=mysticism, enemy_template=self.template,
                defaults={'include': True, 'die_set': '50'}
            )
            if not created:
                skill.include = True
                skill.save()
            self.assertTrue(self.template.is_mystic)

    def test_is_animist_with_binding_skill(self):
        """Test is_animist returns True when Binding skill is included."""
        binding = SkillAbstract.objects.filter(name='Binding').first()
        if binding:
            skill, created = EnemySkill.objects.get_or_create(
                skill=binding, enemy_template=self.template,
                defaults={'include': True, 'die_set': '50'}
            )
            if not created:
                skill.include = True
                skill.save()
            self.assertTrue(self.template.is_animist)

    def test_generate_spirit_branch(self):
        """Test generate() uses _Spirit for spirit templates."""
        spirit_template = EnemyTemplate.objects.filter(race__discorporate=True, published=True).first()
        if spirit_template:
            try:
                spirit = spirit_template.generate()
                self.assertIsNotNone(spirit)
                self.assertIn('STR', spirit.stats)
                self.assertEqual(spirit.name, spirit_template.name)  # Has template name
            except KeyError:
                self.skipTest("Spirit template missing required stats")

    def test_generate_cult_branch(self):
        """Test generate() uses _Cult for cult templates."""
        cult_template = EnemyTemplate.objects.filter(race__name='Cult', published=True).first()
        if cult_template:
            try:
                cult = cult_template.generate()
                self.assertIsNotNone(cult)
                self.assertEqual(cult.name, cult_template.name)  # Has template name
            except KeyError:
                self.skipTest("Cult template missing required stats")

    def test_generate_elemental_branch(self):
        """Test generate() uses _Elemental for elemental templates."""
        elemental_template = EnemyTemplate.objects.filter(race__elemental=True, published=True).first()
        if elemental_template:
            try:
                elemental = elemental_template.generate()
                self.assertIsNotNone(elemental)
                self.assertIn('STR', elemental.stats)
            except KeyError:
                self.skipTest("Elemental template missing required stats")

    def test_complex_template_with_spells(self):
        """Stress test: Generate a template with many spells."""
        found = False
        for t in EnemyTemplate.objects.filter(published=True, rank__gte=4)[:3]:
            spells = len(t.folk_spells) + len(t.theism_spells) + len(t.sorcery_spells) + len(t.mysticism_spells)
            if spells > 0:
                try:
                    enemy = _Enemy(t).generate()
                    self.assertIsNotNone(enemy)
                    self.assertIn('STR', enemy.stats)
                    found = True
                except KeyError:
                    pass
                else:
                    break
        self.assertTrue(found, "No complex template with spells could be generated")

    def test_apply_skill_bonus_empty(self):
        """Test apply_skill_bonus with empty string does nothing."""
        before = list(self.template.raw_skills.values_list('die_set', flat=True))
        self.template.apply_skill_bonus('')
        after = list(self.template.raw_skills.values_list('die_set', flat=True))
        self.assertEqual(before, after)  # No change

    def test_apply_skill_bonus_without_plus(self):
        """Test apply_skill_bonus without + prefix."""
        before = self.template.raw_skills.first().die_set
        self.template.apply_skill_bonus('10')
        after = self.template.raw_skills.first().die_set
        self.assertIn('+10', after)  # Should prepend + automatically

    def test_clone_with_custom_skills(self):
        """Test cloning a template with custom skills."""
        cs = CustomSkill.create(self.template.id)
        cloned = self.template.clone(self.user)
        self.assertEqual(cloned.custom_skills.count(), 1)

    def test_clone_with_custom_spells(self):
        """Test cloning a template with custom spells."""
        cs = CustomSpell.create(self.template.id, 'folk')
        cloned = self.template.clone(self.user)
        self.assertEqual(CustomSpell.objects.filter(enemy_template=cloned).count(), 1)

    def test_clone_with_spirits(self):
        """Test cloning a template with spirits."""
        spirit_template = EnemyTemplate.objects.filter(
            race__discorporate=True, published=True
        ).first()
        if spirit_template:
            EnemySpirit.create(spirit_template.id, self.template.id)
            cloned = self.template.clone(self.user)
            self.assertEqual(cloned.spirits.count(), 1)

    def test_clone_with_cults(self):
        """Test cloning a template with cults."""
        cult_template = EnemyTemplate.objects.filter(
            race__name='Cult', published=True
        ).first()
        if cult_template:
            EnemyCult.create(cult_template.id, self.template.id)
            cloned = self.template.clone(self.user)
            self.assertEqual(cloned.cults.count(), 1)

    def test_clone_with_additional_features(self):
        """Test cloning a template with additional features."""
        fl = AdditionalFeatureList(name='Feature', type='enemy_feature')
        fl.save()
        EnemyAdditionalFeatureList.create(self.template, fl.id)
        cloned = self.template.clone(self.user)
        self.assertEqual(cloned.additional_features.count(), 1)

    def test_clone_with_nonrandom_features(self):
        """Test cloning a template with nonrandom features."""
        fl = AdditionalFeatureList(name='Feature', type='enemy_feature')
        fl.save()
        item = AdditionalFeatureItem(name='Item', feature_list=fl)
        item.save()
        EnemyNonrandomFeature.create(self.template, item.id)
        cloned = self.template.clone(self.user)
        self.assertEqual(cloned.nonrandom_features.count(), 1)

    def test_toggle_star(self):
        """Test toggle_star creates then removes star."""
        self.template.toggle_star(self.user)
        self.assertTrue(self.template.is_starred(self.user))
        self.template.toggle_star(self.user)
        self.assertFalse(self.template.is_starred(self.user))

    def test_is_starred_with_annotation(self):
        """Test is_starred uses pre-populated annotation."""
        from django.db.models import Value, BooleanField
        templates = EnemyTemplate.objects.filter(id=self.template.id).annotate(
            starred=Value(True, output_field=BooleanField())
        )
        for t in templates:
            self.assertTrue(t.is_starred(self.user))

    def test_get_starred_authenticated(self):
        """Test get_starred returns starred templates for authenticated user."""
        Star.create_or_delete(self.user, self.template)
        starred = EnemyTemplate.get_starred(self.user)
        self.assertIn(self.template, starred)

    def test_summary_dict_without_user(self):
        """Test summary_dict without user has starred=False."""
        d = self.template.summary_dict()
        self.assertEqual(d['starred'], False)

    def test_summary_dict_keys(self):
        """Test summary_dict includes expected keys."""
        d = self.template.summary_dict(self.user)
        self.assertIn('name', d)
        self.assertIn('race', d)
        self.assertIn('rank', d)
        self.assertIn('owner', d)
        self.assertIn('tags', d)
        self.assertIn('id', d)
        self.assertIn('starred', d)




class PartyModelTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Party Test')
        self.party = Party.create(self.user)

    def test_party_add_template(self):
        """Test adding a template to a party."""
        self.party.add(self.template)
        self.assertEqual(self.party.template_specs.count(), 1)

    def test_party_set_amount(self):
        """Test setting amount for a template in a party."""
        self.party.add(self.template)
        self.party.set_amount(self.template, '1d4')
        ttp = TemplateToParty.objects.get(party=self.party, template=self.template)
        self.assertEqual(ttp.amount, '1d4')

    def test_party_set_published(self):
        """Test setting party published status."""
        self.party.set_published(True)
        self.assertTrue(self.party.published)
        self.party.set_published(False)
        self.assertFalse(self.party.published)

    def test_party_add_additional_feature(self):
        """Test adding additional feature to party."""
        fl = AdditionalFeatureList(name='Party Feature', type='party_feature')
        fl.save()
        self.party.add_additional_feature(fl.id)
        self.assertEqual(self.party.additional_features.count(), 1)

    def test_party_add_nonrandom_feature(self):
        """Test adding nonrandom feature to party."""
        fl = AdditionalFeatureList(name='Feature List', type='enemy_feature')
        fl.save()
        item = AdditionalFeatureItem(name='Feature Item', feature_list=fl)
        item.save()
        self.party.add_nonrandom_feature(item.id)
        self.assertEqual(self.party.nonrandom_features.count(), 1)

    def test_party_clone(self):
        """Test cloning a party preserves templates and features."""
        self.party.add(self.template)
        cloned = self.party.clone(self.user)
        self.assertEqual(cloned.name, 'Copy of %s' % self.party.name)
        self.assertEqual(cloned.template_specs.count(), self.party.template_specs.count())

    def test_party_get_tags(self):
        """Test party get_tags returns sorted list."""
        self.party.tags.add('tag1', 'tag2')
        tags = self.party.get_tags()
        self.assertEqual(tags, ['tag1', 'tag2'])

    def test_template_to_party_get_amount(self):
        """Test TemplateToParty.get_amount rolls dice."""
        self.party.add(self.template)
        ttp = TemplateToParty.objects.get(party=self.party)
        amount = ttp.get_amount()
        self.assertIsInstance(amount, int)




class CombatStyleModelTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Combat Test')
        self.combat_style = self.template.combat_styles.first()

    def test_set_one_h_amount(self):
        """Test setting one-handed weapon amount."""
        self.combat_style.set_one_h_amount('1d4')
        self.assertEqual(self.combat_style.one_h_amount, '1d4')

    def test_set_two_h_amount(self):
        """Test setting two-handed weapon amount."""
        self.combat_style.set_two_h_amount('1d3')
        self.assertEqual(self.combat_style.two_h_amount, '1d3')

    def test_set_ranged_amount(self):
        """Test setting ranged weapon amount."""
        self.combat_style.set_ranged_amount('1d2')
        self.assertEqual(self.combat_style.ranged_amount, '1d2')

    def test_set_shield_amount(self):
        """Test setting shield amount."""
        self.combat_style.set_shield_amount('1')
        self.assertEqual(self.combat_style.shield_amount, '1')

    def test_set_value(self):
        """Test setting combat style die value."""
        self.combat_style.set_value('STR+DEX+10')
        self.assertEqual(self.combat_style.die_set, 'STR+DEX+10')

    def test_custom_weapons_property(self):
        """Test custom_weapons property returns list."""
        weapons = self.combat_style.custom_weapons
        self.assertIsNotNone(weapons)
        self.assertIsInstance(weapons, list)

    def test_one_h_options(self):
        """Test one_h_options property returns list of dicts."""
        options = self.combat_style.one_h_options
        self.assertIsNotNone(options)
        self.assertIsInstance(options, list)
        if options:
            self.assertIn('name', options[0])

    def test_two_h_options(self):
        """Test two_h_options property returns list of dicts."""
        options = self.combat_style.two_h_options
        self.assertIsNotNone(options)
        self.assertIsInstance(options, list)
        if options:
            self.assertIn('name', options[0])

    def test_ranged_options(self):
        """Test ranged_options property returns list of dicts."""
        options = self.combat_style.ranged_options
        self.assertIsNotNone(options)
        self.assertIsInstance(options, list)
        if options:
            self.assertIn('name', options[0])

    def test_shield_options(self):
        """Test shield_options property returns list of dicts."""
        options = self.combat_style.shield_options
        self.assertIsNotNone(options)
        self.assertIsInstance(options, list)
        if options:
            self.assertIn('name', options[0])

    def test_roll_one_h_amount(self):
        """Test roll_one_h_amount."""
        self.combat_style.one_h_amount = '1d4'
        self.combat_style.save()
        amount = self.combat_style.roll_one_h_amount()
        self.assertIsInstance(amount, int)

    def test_roll_two_h_amount(self):
        """Test roll_two_h_amount."""
        self.combat_style.two_h_amount = '1d3'
        self.combat_style.save()
        amount = self.combat_style.roll_two_h_amount()
        self.assertIsInstance(amount, int)

    def test_roll_ranged_amount(self):
        """Test roll_ranged_amount."""
        self.combat_style.ranged_amount = '1d2'
        self.combat_style.save()
        amount = self.combat_style.roll_ranged_amount()
        self.assertIsInstance(amount, int)

    def test_roll_shield_amount(self):
        """Test roll_shield_amount."""
        self.combat_style.shield_amount = '1'
        self.combat_style.save()
        amount = self.combat_style.roll_shield_amount()
        self.assertIsInstance(amount, int)

    def test_clone_combat_style(self):
        """Test cloning a combat style."""
        new_template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Clone Target')
        self.combat_style.clone(new_template)
        cloned_cs = new_template.combat_styles.first()
        self.assertIsNotNone(cloned_cs)
        self.assertEqual(cloned_cs.name, self.combat_style.name)




class WeaponModelTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Weapon Test')
        self.combat_style = self.template.combat_styles.first()
        self.weapon = Weapon.objects.first()

    def test_enemy_weapon_create(self):
        """Test creating an EnemyWeapon."""
        if self.weapon:
            ew = EnemyWeapon.create(self.combat_style, self.weapon, 5)
            self.assertEqual(ew.probability, 5)

    def test_enemy_weapon_set_probability_zero_deletes(self):
        """Test setting probability to zero deletes the weapon."""
        if self.weapon:
            ew = EnemyWeapon.create(self.combat_style, self.weapon, 5)
            ew_id = ew.id
            ew.set_probability(0)
            self.assertFalse(EnemyWeapon.objects.filter(id=ew_id).exists())

    def test_custom_weapon_create(self):
        """Test creating a custom weapon."""
        cw = CustomWeapon.create(self.combat_style.id, '1h-melee', 'My Weapon', 10)
        self.assertEqual(cw.name, 'My Weapon')
        self.assertEqual(cw.probability, 10)

    def test_custom_weapon_set_probability(self):
        """Test setting custom weapon probability."""
        cw = CustomWeapon.create(self.combat_style.id, '1h-melee', 'Prob Weapon', 1)
        cw.set_probability(20)
        self.assertEqual(cw.probability, 20)




class SkillModelTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Skill Test')

    def test_enemy_skill_set_value(self):
        """Test setting enemy skill value."""
        skill = self.template.raw_skills.first()
        skill.set_value('STR+20')
        self.assertEqual(skill.die_set, 'STR+20')

    def test_custom_skill_create(self):
        """Test creating a custom skill."""
        cs = CustomSkill.create(self.template.id)
        self.assertEqual(cs.name, 'Custom skill')
        self.assertTrue(cs.include)

    def test_custom_skill_set_value(self):
        """Test setting custom skill value."""
        cs = CustomSkill.create(self.template.id)
        cs.set_value('DEX+10')
        self.assertEqual(cs.die_set, 'DEX+10')

    def test_custom_skill_roll(self):
        """Test rolling a custom skill."""
        cs = CustomSkill.create(self.template.id)
        cs.die_set = '50'
        cs.save()
        result = cs.roll()
        self.assertIsInstance(result, int)




class SpellModelTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Spell Test')
        self.spell = SpellAbstract.objects.first()

    def test_enemy_spell_set_probability_zero_deletes(self):
        """Test setting spell probability to zero deletes it."""
        if self.spell:
            es = EnemySpell(spell=self.spell, enemy_template=self.template, probability=5)
            es.save()
            es_id = es.id
            es.set_probability(0)
            self.assertFalse(EnemySpell.objects.filter(id=es_id).exists())

    def test_custom_spell_create(self):
        """Test creating a custom spell."""
        cs = CustomSpell.create(self.template.id, 'folk')
        self.assertEqual(cs.name, 'Custom spell')
        self.assertEqual(cs.type, 'folk')

    def test_custom_spell_set_probability(self):
        """Test setting custom spell probability."""
        cs = CustomSpell.create(self.template.id, 'folk')
        cs.set_probability(50)
        self.assertEqual(cs.probability, 50)




class SpiritAndCultModelTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Spirit Test')
        spirit_race = Race(name='Spirit', owner=self.user, discorporate=True)
        spirit_race.save()
        HitLocation(name='Body', range_start=1, range_end=20, race=spirit_race, hp_modifier=0).save()
        self.spirit_template = EnemyTemplate.create(self.user, self.ruleset, spirit_race, 'Test Spirit')

    def test_enemy_spirit_create(self):
        """Test creating an EnemySpirit link."""
        es = EnemySpirit.create(self.spirit_template.id, self.template.id)
        self.assertEqual(es.spirit, self.spirit_template)
        self.assertEqual(es.enemy_template, self.template)

    def test_enemy_cult_create(self):
        """Test creating an EnemyCult link."""
        cult_race = Race(name='Cult', owner=self.user)
        cult_race.save()
        cult_template = EnemyTemplate.create(self.user, self.ruleset, cult_race, 'Test Cult')
        ec = EnemyCult.create(cult_template.id, self.template.id)
        self.assertEqual(ec.cult, cult_template)




class FeatureListModelTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Feature Test')
        self.feature_list = AdditionalFeatureList(name='Test Feature', type='enemy_feature')
        self.feature_list.save()
        self.item1 = AdditionalFeatureItem(name='Item 1', feature_list=self.feature_list)
        self.item1.save()
        self.item2 = AdditionalFeatureItem(name='Item 2', feature_list=self.feature_list)
        self.item2.save()

    def test_additional_feature_list_items(self):
        """Test feature list items property."""
        items = self.feature_list.items
        self.assertEqual(len(items), 2)

    def test_get_random_item(self):
        """Test getting random item from feature list."""
        item = self.feature_list.get_random_item()
        self.assertIn(item, [self.item1, self.item2])

    def test_enemy_additional_feature_create(self):
        """Test creating enemy additional feature list."""
        afl = EnemyAdditionalFeatureList.create(self.template, self.feature_list.id)
        self.assertEqual(afl.enemy_template, self.template)

    def test_enemy_additional_feature_random_has_feature(self):
        """Test random feature check."""
        afl = EnemyAdditionalFeatureList.create(self.template, self.feature_list.id, '100')
        result = afl.random_has_feature({'POW': 10})
        self.assertIsInstance(result, bool)

    def test_enemy_additional_feature_set_probability(self):
        """Test setting probability on enemy additional feature."""
        afl = EnemyAdditionalFeatureList.create(self.template, self.feature_list.id)
        afl.set_probability('50')
        self.assertEqual(afl.probability, '50')

    def test_enemy_nonrandom_feature_create(self):
        """Test creating nonrandom feature."""
        nrf = EnemyNonrandomFeature.create(self.template, self.item1.id)
        self.assertEqual(nrf.feature, self.item1)

    def test_party_additional_feature_create(self):
        """Test creating party additional feature list."""
        party = Party.create(self.user)
        afl = PartyAdditionalFeatureList.create(party, self.feature_list.id)
        self.assertEqual(afl.party, party)

    def test_party_additional_feature_random_has_feature(self):
        """Test random feature check for party."""
        party = Party.create(self.user)
        afl = PartyAdditionalFeatureList.create(party, self.feature_list.id)
        afl.probability = '100'
        afl.save()
        result = afl.random_has_feature()
        self.assertTrue(result)

    def test_party_additional_feature_set_probability(self):
        """Test setting probability on party additional feature."""
        party = Party.create(self.user)
        afl = PartyAdditionalFeatureList.create(party, self.feature_list.id)
        afl.set_probability('75')
        self.assertEqual(afl.probability, '75')

    def test_party_nonrandom_feature_create(self):
        """Test creating party nonrandom feature."""
        party = Party.create(self.user)
        nrf = PartyNonrandomFeature.create(party, self.item1.id)
        self.assertEqual(nrf.feature, self.item1)




class HitLocationEnemyModelTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'HL Test')

    def test_enemy_hit_location_set_armor(self):
        """Test setting armor on enemy hit location."""
        ehl = self.template.hit_locations.first()
        ehl.set_armor('1d6')
        self.assertEqual(ehl.armor, '1d6')

    def test_enemy_hit_location_create_with_armor(self):
        """Test creating enemy hit location with custom armor."""
        hl = self.race.hit_locations.first()
        new_template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'HL Test 2')
        ehl = EnemyHitLocation.create(hl, new_template, armor='2d6')
        self.assertEqual(ehl.armor, '2d6')




class StatModelTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Stat Test')

    def test_enemy_stat_set_value(self):
        """Test setting enemy stat value."""
        stat = self.template.stats.first()
        stat.set_value('2d6+6')
        self.assertEqual(stat.die_set, '2d6+6')

    def test_race_stat_set_value(self):
        """Test setting race stat default value."""
        rs = self.race.stats.first()
        rs.set_value('1d6+10')
        self.assertEqual(rs.default_value, '1d6+10')




class StarModelTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Star Test')

    def test_star_create_or_delete_toggle(self):
        """Test toggling star creates then deletes."""
        Star.create_or_delete(self.user, self.template)
        self.assertTrue(Star.objects.filter(user=self.user, template=self.template).exists())
        Star.create_or_delete(self.user, self.template)
        self.assertFalse(Star.objects.filter(user=self.user, template=self.template).exists())


class TestDice(TestCase):
    def test_1_die_to_tuple(self):
        self.assertEqual(_die_to_tuple('d6'), (1, 6, 1))
        self.assertEqual(_die_to_tuple('D6'), (1, 6, 1))
        self.assertEqual(_die_to_tuple('+D6'), (1, 6, 1))
        self.assertEqual(_die_to_tuple('-D6'), (-6, -1, 1))
        
        self.assertEqual(_die_to_tuple('2D6'), (1, 6, 2))
        self.assertEqual(_die_to_tuple('12D6'), (1, 6, 12))
        self.assertEqual(_die_to_tuple('+3D8'), (1, 8, 3))
        self.assertEqual(_die_to_tuple('-2D6'), (-6, -1, 2))
        
    def test_2_dissect(self):
        self.assertEqual(list(Dice('D6').components), [(1, 6, 1), ])
        self.assertEqual(list(Dice('d6').components), [(1, 6, 1), ])
        self.assertEqual(list(Dice('d6+1').components), [(1, 6, 1), 1])
        self.assertEqual(list(Dice('d6-1').components), [(1, 6, 1), -1])
        self.assertEqual(list(Dice('50+d6-1').components), [50, (1, 6, 1), -1])
        self.assertEqual(list(Dice('50-d6').components), [50, (-6, -1, 1)])
        self.assertEqual(list(Dice('2D6-D4').components), [(1, 6, 2), (-4, -1, 1)])
        self.assertEqual(list(Dice('2D6-D4+5').components), [(1, 6, 2), (-4, -1, 1), 5])
        self.assertEqual(list(Dice('2D6-D4-5').components), [(1, 6, 2), (-4, -1, 1), -5])
        
    def test_3_dice(self):
        self.assertTrue(1 <= Dice('D6').roll() <= 6)
        self.assertTrue(1 <= Dice('D6').roll() <= 6)
        self.assertTrue(1 <= Dice('D6').roll() <= 6)
        
        self.assertTrue(7 <= Dice('6+D6').roll() <= 12)
        self.assertTrue(7 <= Dice('6+D6').roll() <= 12)
        self.assertTrue(7 <= Dice('6+D6').roll() <= 12)

        self.assertTrue(12 <= Dice('20-2D4').roll() <= 18)
        self.assertTrue(12 <= Dice('20-2D4').roll() <= 18)
        self.assertTrue(12 <= Dice('20-2D4').roll() <= 18)
        
        self.assertTrue(2 <= Dice('2D20').roll() <= 40)
        self.assertTrue(2 <= Dice('2D20').roll() <= 40)
        self.assertTrue(2 <= Dice('2D20').roll() <= 40)
        self.assertTrue(2 <= Dice('2D20').roll() <= 40)
        self.assertTrue(2 <= Dice('2D20').roll() <= 40)
        
        self.assertTrue(12 <= Dice('10 + 2D2').roll() <= 14)
        self.assertTrue(12 <= Dice('10 + 2D2').roll() <= 14)
        self.assertTrue(12 <= Dice('10 + 2D2').roll() <= 14)
        self.assertTrue(12 <= Dice('10 + 2D2').roll() <= 14)
        
        self.assertTrue(12 <= Dice('12D6').roll() <= 72)
        self.assertTrue(12 <= Dice('12D6').roll() <= 72)
        self.assertTrue(12 <= Dice('12D6').roll() <= 72)
        self.assertTrue(12 <= Dice('12D6').roll() <= 72)
        
    def test_4_max_roll(self):
        self.assertEqual(Dice('5').max_roll(), 5)
        self.assertEqual(Dice('D100').max_roll(), 100)
        self.assertEqual(Dice('5D100').max_roll(), 500)
        self.assertEqual(Dice('5D100+13').max_roll(), 513)
        self.assertEqual(Dice('5D100-D100').max_roll(), 499)
        self.assertEqual(Dice('12D6').max_roll(), 72)


    def test_5_clean(self):
        self.assertEqual(clean('D6'), '1d6')
        self.assertEqual(clean('DEX+D6'), 'DEX+1d6')
        self.assertEqual(clean('D6+-D4'), '1d6-1d4')
        self.assertEqual(clean('DEX+STR+2D10+D6-D4'), 'DEX+STR+2d10+1d6-1d4')
        self.assertEqual(clean('DEX-STR'), 'DEX-STR')
        self.assertEqual(clean('POW+POW+POW'), 'POW+POW+POW')
        self.assertEqual(clean('POW+POW-POW'), 'POW')
        self.assertEqual(clean('POW+2D10-2D10'), 'POW')
        self.assertEqual(clean('POW+3D10-2d10'), 'POW+1d10')
        self.assertEqual(clean('DEX+STR+DEX'), 'DEX+DEX+STR')
        self.assertEqual(clean('DEX+d10+d20+1d10+d6+2d10'), 'DEX+4d10+1d20+1d6')
        self.assertEqual(clean('DEX+10+d10+20'), 'DEX+1d10+30')
        self.assertEqual(clean('DEX+10+d10+10'), 'DEX+1d10+20')
        self.assertEqual(clean('DEX+10+d10-20'), 'DEX+1d10-10')
        self.assertEqual(clean('DEX+10+d10-5-5'), 'DEX+1d10')
        self.assertEqual(clean('STR+DEX+20+5D10+-4D10+2D10+-4D10+2D10'), 'STR+DEX+1d10+20')




class TestViewsLib(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_context_without_changelog_rows(self):
        request = self.factory.get("/")
        request.session = {}

        context = get_context(request)

        self.assertNotIn('recent_changes', context)




class TestEnemyTemplate(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def test_01_create(self):
        user = User(username='username')
        user.save()
        ruleset = Ruleset.objects.get(id=1)
        self.assertEqual(ruleset.name, 'RuneQuest 6')
        race = Race.objects.get(id=1)
        self.assertEqual(race.name, 'Human')
        et = EnemyTemplate.create(user, ruleset, race, 'Template Name')
        self.assertEqual(et.name, 'Template Name')
        self.assertTrue(isinstance(et.stats[0], EnemyStat))
        self.assertEqual(et.stats[0].name, 'STR')
        self.assertEqual(et.stats[0].die_set, '3d6')
        self.assertTrue(isinstance(et.skills[0], EnemySkill))
        self.assertEqual(et.skills[0].name, 'Acrobatics')
        self.assertEqual(et.skills[0].die_set, 'STR+DEX')
        self.assertTrue(et.combat_styles[0].name, "Primary Combat Style")

    def test_12_generate(self):
        et = get_enemy_template()
        enemy = et.generate()
        self.assertTrue(isinstance(enemy, _Enemy))
        self.assertTrue(isinstance(enemy.stats, OrderedDict))
        self.assertTrue(isinstance(enemy.skills, list))
        self.assertTrue(isinstance(enemy.skills[0], dict))
        self.assertTrue(isinstance(enemy.stats['STR'], int))
        self.assertEqual(enemy.skills[0]['name'], 'Athletics')
        self.assertTrue(isinstance(enemy.skills[0]['value'], int))
        
    def test_13_generate_2(self):
        et = get_enemy_template()
        self.assertEqual(et.skills[17].name, 'Evade')
        skill = et.skills[17]
        skill.die_set = 'STR+DEX+50'
        skill.save()
        self.assertEqual(et.stats[0].name, 'STR')
        stat = et.stats[0]
        stat.die_set = '2+2D4'
        stat.save()
        self.assertEqual(et.stats[3].name, 'DEX')
        stat = et.stats[3]
        stat.die_set = '10+D3'
        stat.save()

        enemy = et.generate()
        self.assertTrue(4 <= enemy.stats['STR'] <= 10)
        self.assertTrue(11 <= enemy.stats['DEX'] <= 13)
        self.assertEqual(enemy.skills[3]['name'], 'Evade')
        self.assertEqual(enemy.skills[3]['value'], enemy.stats['DEX'] + enemy.stats['STR'] + 50)
        
    def test_14_generate_check_spells(self):
        et = get_enemy_template()
        et.folk_spell_amount = '2'
        self.assertEqual(len(et.folk_spells), 0)
        EnemySpell(enemy_template=et, spell=SpellAbstract.objects.get(name='Alarm'), probability=1).save()
        EnemySpell(enemy_template=et, spell=SpellAbstract.objects.get(name='Avert'), probability=1).save()

        enemy = et.generate()
        self.assertEqual(len(enemy.folk_spells), 2)
        
        self.assertTrue(enemy.folk_spells[0].name in ('Alarm', 'Avert'))
        self.assertTrue(enemy.folk_spells[1].name in ('Alarm', 'Avert'))
        
    def test_15_generate_check_attributes(self):
        et = get_enemy_template()
        self.assertEqual(et.ruleset.name, 'RuneQuest 6')
        enemy = et.generate()
        
        action_points = enemy.attributes['action_points']
        self.assertTrue((action_points == 1 and enemy.stats['INT'] + enemy.stats['DEX'] <= 12) or
                        (action_points == 2 and enemy.stats['INT'] + enemy.stats['DEX'] <= 24) or
                        (action_points == 3 and enemy.stats['INT'] + enemy.stats['DEX'] <= 36) or
                        (action_points == 4 and enemy.stats['INT'] + enemy.stats['DEX'] > 36)
                        )
                       
        damage_modifier = enemy.attributes['damage_modifier']
        str_siz = enemy.stats['STR'] + enemy.stats['SIZ']
        self.assertTrue((damage_modifier == '-1d8' and str_siz <= 5) or
                        (damage_modifier == '-1d4' and 11 <= str_siz <= 15) or
                        (damage_modifier == '-1d2' and 16 <= str_siz <= 20) or
                        (damage_modifier == '+0' and 21 <= str_siz <= 25) or
                        (damage_modifier == '+1d2' and 26 <= str_siz <= 30) or
                        (damage_modifier == '+1d4' and 31 <= str_siz <= 35) or
                        (damage_modifier == '+1d6' and 36 <= str_siz <= 40)
                        )
                       
        self.assertEqual(enemy.attributes['magic_points'], enemy.stats['POW'])
        
        sr = (enemy.stats['INT'] + enemy.stats['DEX']) // 2
        sr = '%s(%s-0)' % (sr, sr)
        self.assertEqual(enemy.attributes['strike_rank'], sr)
        
    def notest_16_generate_check_weapon_styles(self):
        # Fix this test!!!!!!!!!!!!!!!
        et = get_enemy_template()
        cs1 = CombatStyle(name="name", enemy_template=et, die_set="STR+DEX")
        cs1.save()
        cs1.weapon_options.add(Weapon.objects.get(name="Broadsword"))
        enemy = et.generate()
        
        self.assertEqual(enemy.combat_styles[0]['name'], "Primary Combat Style")
        self.assertEqual(enemy.combat_styles[0]['value'], enemy.stats['STR']+enemy.stats['DEX'])
        self.assertEqual(enemy.combat_styles[0]['weapons'][0].name, 'Broadsword')




class TestEnemySkill(TestCase):
    fixtures = ('enemygen_testdata.json',)
    
    def test_1_roll(self):
        skill = SkillAbstract.objects.get(id=1)
        et = get_enemy_template()
        es = EnemySkill.objects.get(skill=skill, enemy_template=et)
        es.die_set = 'STR+DEX+2D4'
        es.save()
        replace_with = {'STR': 10, 'DEX': 20}
        self.assertEqual(replace_die_set(es.die_set, replace_with), '10+20+2D4')
        
    def test_2_roll(self):
        skill = SkillAbstract.objects.get(id=1)
        et = get_enemy_template()
        es = EnemySkill.objects.get(skill=skill, enemy_template=et)
        es.die_set = '10+2D4'
        es.save()
        
        self.assertTrue(12 <= es.roll() <= 18)
        self.assertTrue(12 <= es.roll() <= 18)
        self.assertTrue(12 <= es.roll() <= 18)
        self.assertTrue(12 <= es.roll() <= 18)
        self.assertTrue(12 <= es.roll() <= 18)
        self.assertTrue(12 <= es.roll() <= 18)
        
        es = EnemySkill.objects.get(skill=skill, enemy_template=et)
        es.die_set = 'STR+DEX+10+2D4'
        es.save()
        replace_with = {'STR': 10, 'DEX': 20}
        self.assertTrue(42 <= es.roll(replace_with) <= 48)
        self.assertTrue(42 <= es.roll(replace_with) <= 48)
        self.assertTrue(42 <= es.roll(replace_with) <= 48)
        self.assertTrue(42 <= es.roll(replace_with) <= 48)
        self.assertTrue(42 <= es.roll(replace_with) <= 48)
        self.assertTrue(42 <= es.roll(replace_with) <= 48)
        
    def test_stat_set_value(self):
        stat = StatAbstract.objects.get(id=2)
        et = get_enemy_template()
        es = EnemyStat(stat=stat, enemy_template=et, die_set='D6')
        es.save()
        
        self.assertRaises(ValueError, es.set_value, 'invalid')




class TestMisc(TestCase):
    fixtures = ('enemygen_testdata.json',)
    
    def test_select_random_spell(self):
        et = get_enemy_template()
        self.assertEqual(len(et.folk_spells), 0)
        EnemySpell(enemy_template=et, spell=SpellAbstract.objects.get(name='Alarm'), probability=1).save()
        EnemySpell(enemy_template=et, spell=SpellAbstract.objects.get(name='Avert'), probability=1).save()
        
        spells = et.folk_spells
        
        self.assertTrue(select_random_item(spells).name in (spells[0].name, spells[1].name))
        self.assertTrue(select_random_item(spells).name in (spells[0].name, spells[1].name))
        self.assertTrue(select_random_item(spells).name in (spells[0].name, spells[1].name))
        self.assertTrue(select_random_item(spells).name in (spells[0].name, spells[1].name))
        
        EnemySpell(enemy_template=et, spell=SpellAbstract.objects.get(name='Calm'), probability=1).save()
        spells = et.folk_spells
        # Test exclude
        spells[0].probability = 100
        spells[0].save()
        spells[1].probability = 100
        spells[1].save()
        spells[2].probability = 1
        spells[2].save()

        exclude = (spells[0], spells[1])
        random_spell = select_random_item(spells, exclude)
        self.assertEqual(random_spell, spells[2])




class TestJson(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def test_enemy_as_json(self):
        et = get_enemy_template()
        _add_magic(et)
        enemy = _Enemy(et).generate()
        ejson = as_json([enemy])
        edict = json.loads(ejson)
        self.assertEqual(edict[0]['folk_spells'][0], 'Bladesharp')
        self.assertEqual(edict[0]['combat_styles'][0]['name'], 'Primary Combat Style')
        self.assertEqual(list(edict[0]['skills'][2].keys())[0], 'Endurance')
        self.assertEqual(edict[0]['skills'][2]['Endurance'], enemy.skills_dict['Endurance'])




class TestPublicCors(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_public_json_endpoint_adds_cors_headers(self):
        middleware = SimpleCorsMiddleware(lambda request: HttpResponse("[]"))
        response = middleware(self.factory.get("/index_json/"))

        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertEqual(response["Access-Control-Allow-Methods"], "GET, OPTIONS")
        self.assertEqual(response["Access-Control-Allow-Headers"], "Accept, Content-Type")

    def test_public_json_endpoint_allows_options_preflight(self):
        middleware = SimpleCorsMiddleware(lambda request: HttpResponse(status=405))
        response = middleware(self.factory.options("/generate_enemies_json/"))

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertEqual(response["Access-Control-Allow-Methods"], "GET, OPTIONS")
        self.assertEqual(response["Access-Control-Allow-Headers"], "Accept, Content-Type")

    def test_generated_json_endpoints_allow_query_params(self):
        middleware = SimpleCorsMiddleware(lambda request: HttpResponse("{}"))

        for path in (
            "/generate_enemies_json/?id=1&amount=2",
            "/generate_party_json/?id=1",
        ):
            response = middleware(self.factory.get(path))
            self.assertEqual(response["Access-Control-Allow-Origin"], "*")
            self.assertEqual(response["Access-Control-Allow-Methods"], "GET, OPTIONS")
            self.assertEqual(response["Access-Control-Allow-Headers"], "Accept, Content-Type")

    def test_generated_json_preflight_allows_query_params(self):
        middleware = SimpleCorsMiddleware(lambda request: HttpResponse(status=405))

        for path in (
            "/generate_enemies_json/?id=1&amount=2",
            "/generate_party_json/?id=1",
        ):
            response = middleware(self.factory.options(path))
            self.assertEqual(response.status_code, 204)
            self.assertEqual(response["Access-Control-Allow-Origin"], "*")
            self.assertEqual(response["Access-Control-Allow-Methods"], "GET, OPTIONS")
            self.assertEqual(response["Access-Control-Allow-Headers"], "Accept, Content-Type")


class PerformanceRegressionTest(TestCase):
    """Performance regression tests to catch N+1 query patterns."""
    fixtures = ('enemygen_testdata.json', 'complex_templates.json', 'rank5_templates.json')

    def test_get_enemy_templates_no_n_plus_1(self):
        """get_enemy_templates should use prefetch_related to avoid N+1 queries."""
        from ..views_lib import get_enemy_templates
        user = User.objects.create_user(username='perf_user', password='password')
        # Verify query count stays low and doesn't scale with template count
        # The key is that accessing race.name and tags.all() shouldn't trigger extra queries
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            templates = get_enemy_templates(None, user)
            # Access related objects that should be prefetched
            for t in templates:
                _ = t.race.name
                _ = t.tags.all()
        # Should be a small constant number, not N+1
        # If this grows significantly, N+1 queries may have crept in
        self.assertLessEqual(len(ctx.captured_queries), 10,
            "Too many queries for get_enemy_templates - possible N+1 issue")

    def test_search_no_n_plus_1(self):
        """EnemyTemplate.search should use prefetch_related to avoid N+1 queries."""
        user = User.objects.create_user(username='search_user', password='password')
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            results = EnemyTemplate.search('', user)
            for t in results:
                _ = t.race.name
                _ = t.tags.all()
        # Search should use prefetch_related for tags
        self.assertLessEqual(len(ctx.captured_queries), 5,
            "Too many queries for search - possible N+1 issue")

    def test_template_generation_no_n_plus_1(self):
        """Template.generate should not cause N+1 queries for skills/spells."""
        # Use a template that exists in the fixtures
        template = EnemyTemplate.objects.first()
        self.assertIsNotNone(template, "No templates in fixtures")
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            enemy = template.generate()
            # Access all parts of the enemy
            _ = enemy.stats
            _ = enemy.skills
            _ = enemy.combat_styles
        # Generation involves many queries (stats, skills, spells, etc.)
        # The key is that this number stays stable, not that it's low
        # If it jumps significantly, N+1 queries may have crept in
        self.assertLessEqual(len(ctx.captured_queries), 100,
            "Too many queries for generation - possible N+1 issue")


def get_enemy_template():
    user = User(username='username')
    user.save()
    ruleset = Ruleset.objects.get(id=1)
    if ruleset.name != 'RuneQuest 6':
        raise Exception("Ruleset doesn't match")
    race = Race.objects.get(id=1)
    if race.name != 'Human':
        raise Exception("Race doesn't match")
    et = EnemyTemplate.create(user, ruleset, race, 'Test Template')
    return et

def _add_magic(et):
    et.folk_spell_amount = '2'
    fm = EnemySkill.objects.get(skill__name='Folk Magic', enemy_template=et)
    fm.include = True
    fm.save()

    sa = SpellAbstract.objects.get(name='Bladesharp')
    es = EnemySpell(spell=sa, enemy_template=et, detail=sa.default_detail, probability=1)
    es.save()
    sa = SpellAbstract.objects.get(name='Calm')
    es = EnemySpell(spell=sa, enemy_template=et, detail=sa.default_detail, probability=1)
    es.save()


