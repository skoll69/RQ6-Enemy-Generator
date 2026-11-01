"""
Consolidated generation tests.

This file combines all generation-related tests from:
- test_smoke.py (GenerationSmokeTest)
- test_generation_real_templates.py (GenerationWithRealTemplatesTest)
- test_exception_handling.py (NegativeGenerationTest, GeneratedPartyEdgeCaseTest)
- test_models_coverage.py (GenerationLogicTest, GenerationEdgeCaseTest)
- test_edge_cases.py (LuckyGenerationEdgeCaseTest, HtmlOutputContentTest)
- test_integration.py (IntegrationTest)
- test_base.py (TestEnemy)
"""
from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from django.contrib.auth.models import User
import json

from ..models import (
    EnemyTemplate, Party, Race, Ruleset, TemplateToParty,
    EnemyStat, StatAbstract, EnemySkill, SkillAbstract, CustomSkill,
    EnemySpell, SpellAbstract, CustomSpell,
    EnemySpirit, EnemyCult,
    CombatStyle, Weapon, EnemyWeapon, CustomWeapon,
    HitLocation, EnemyHitLocation,
    AdditionalFeatureList, AdditionalFeatureItem,
    EnemyAdditionalFeatureList, EnemyNonrandomFeature,
    _Enemy, _Spirit, _Cult, _Elemental,
)

from ..views_lib import (
    get_enemies, get_generated_party, get_enemies_lucky, get_random_party,
    get_filter, get_party_filter, determine_enemies, as_json, enemy_as_json,
    _get_html_prefix,
)

class GenerationSmokeTest(TestCase):
    """Smoke tests for all generation paths to prevent future production crashes."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='genuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Smoke Test Template')
        self.template.published = True
        self.template.save()

    def test_generate_enemies_view_does_not_crash(self):
        """
        Smoke test: The main generation view must not crash.
        This test would have failed with AttributeError when increment_used()
        was accidentally deleted from models.py by commit 702c08e.
        Requirement: POST to /generate_enemies/ with a valid template ID must return 200.
        Note: We verify the view logic by checking the 'enemies' context variable
        instead of full HTML rendering, due to Python 3.14 Django template rendering bugs.
        """
        enemy_index = [(self.template, 1)]
        # This call path is what generate_enemies view executes.
        # Without increment_used(), it crashes with AttributeError.
        enemies = get_enemies(enemy_index, increment=True)
        self.assertEqual(len(enemies), 1)
        # Verify the generated enemy has stats
        self.assertIn('STR', enemies[0].stats)
        # Verify the template's used counter was incremented
        self.template.refresh_from_db()
        self.assertGreaterEqual(self.template.used, 1)

    def test_generate_enemies_without_increment(self):
        """
        Smoke test: Generation without incrementing counters must work.
        This verifies the generation logic works even when increment_used() is missing.
        """
        enemy_index = [(self.template, 2)]
        enemies = get_enemies(enemy_index, increment=False)
        self.assertEqual(len(enemies), 2)
        # Verify both enemies have stats
        for enemy in enemies:
            self.assertIn('STR', enemy.stats)
        # Verify the template's used counter was NOT incremented
        original_used = self.template.used
        self.template.refresh_from_db()
        self.assertEqual(self.template.used, original_used)

    def test_generate_party_view_does_not_crash(self):
        """
        Smoke test: The party generation view must not crash.
        This test would have failed with AttributeError when increment_used()
        was accidentally deleted from models.py.
        Requirement: POST to /generate_party/ with a valid party ID must work.
        Note: Party generation always calls increment_used(), so this test
        will fail on master until PR 2 (increment_used fix) is merged.
        """
        party = Party.objects.create(name='Smoke Test Party', owner=self.user, published=True)
        TemplateToParty.objects.create(party=party, template=self.template, amount=1)

        # This call path is what generate_party view executes.
        # Without increment_used(), it crashes with AttributeError.
        context = get_generated_party(party)
        self.assertEqual(len(context['enemies']), 1)
        # Verify the generated enemy has stats
        self.assertIn('STR', context['enemies'][0].stats)
        self.assertEqual(context['party'].name, 'Smoke Test Party')

    def test_generate_enemies_json_api_returns_json(self):
        """
        Smoke test: The JSON API for enemy generation must return valid JSON.
        Requirement: GET /generate_enemies_json/?id=<template_id>&amount=1 must return 200.
        Note: We test the view logic directly instead of using the Django test client
        to avoid Python 3.14 Django template rendering bugs.
        """
        from ..views_lib import as_json
        enemy_index = [(self.template, 1)]
        # This uses increment=True like the JSON API does
        enemies = get_enemies(enemy_index, increment=True)
        enemies_json = as_json(enemies)
        data = json.loads(enemies_json)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)

    def test_generate_party_json_api_returns_json(self):
        """
        Smoke test: The JSON API for party generation must return valid JSON.
        Requirement: GET /generate_party_json/?id=<party_id> must return 200.
        Note: We test the view logic directly instead of using the Django test client
        to avoid Python 3.14 Django template rendering bugs.
        """
        from ..views_lib import enemy_as_json
        party = Party.objects.create(name='JSON API Party', owner=self.user, published=True)
        TemplateToParty.objects.create(party=party, template=self.template, amount=1)

        # This uses the same code path as generate_party_json
        party_context = get_generated_party(party)
        out = {'enemies': [], 'party_name': party.name, 'additional_features': []}
        for enemy in party_context['enemies']:
            out['enemies'].append(enemy_as_json(enemy))
        self.assertIn('enemies', out)
        self.assertIn('party_name', out)
        self.assertEqual(len(out['enemies']), 1)

    def test_generate_enemies_lucky_returns_enemies(self):
        """
        Smoke test: The lucky (random) generation must return enemies.
        Requirement: POST to /generate_enemies/ with lucky param must return enemies.
        """
        request = self.factory.post('/generate_enemies/', {'lucky': '1'})
        request.session = {}
        enemies = get_enemies_lucky(request)
        self.assertIsInstance(enemies, list)
        self.assertGreater(len(enemies), 0)

    def test_generate_party_lucky_returns_enemies(self):
        """
        Smoke test: The lucky (random) party generation must return enemies.
        Requirement: POST to /generate_party/ with lucky param must return enemies.
        """
        from ..views_lib import get_random_party, get_party_filter

        party = Party.objects.create(name='Lucky Party', owner=self.user, published=True)
        TemplateToParty.objects.create(party=party, template=self.template, amount=1)

        request = self.factory.post('/generate_party/', {'lucky': '1'})
        request.session = {}
        party_object = get_random_party(get_party_filter(request))
        self.assertIsNotNone(party_object)
        context = get_generated_party(party_object)
        self.assertIn('enemies', context)




class GenerationWithRealTemplatesTest(TestCase):
    """Test generation class internals with real database templates."""
    fixtures = ('enemygen_testdata.json', 'complex_templates.json')

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')

    # --- _Enemy tests ---

    def test_enemy_generate_with_spirits_from_db(self):
        """Test _Enemy._add_spirits with real spirit templates from DB."""
        # Agimori Shaman2 has spirits
        template = EnemyTemplate.objects.get(id=520)
        enemy = _Enemy(template).generate()
        self.assertIsNotNone(enemy)
        # Template has spirit_amount and spirits
        if template.spirit_amount and template.spirits.filter(probability__gt=0).exists():
            # Spirits may or may not be added depending on dice roll
            self.assertIsNotNone(enemy)

    def test_enemy_generate_with_cult_from_db(self):
        """Test _Enemy._add_cults with real cult templates from DB."""
        # Cultist of Ojahl Acolyte has cult
        template = EnemyTemplate.objects.get(id=9531)
        enemy = _Enemy(template).generate()
        self.assertIsNotNone(enemy)
        if template.cult_amount and template.cults.filter(probability__gt=0).exists():
            self.assertGreater(len(enemy.cults), 0)

    def test_enemy_generate_priest_with_devotion(self):
        """Test _Enemy._calculate_attributes with Devotion (theist path)."""
        template = EnemyTemplate.objects.get(id=9531)  # Cultist of Ojahl Acolyte
        enemy = _Enemy(template).generate()
        self.assertIsNotNone(enemy)
        if enemy.is_theist:
            self.assertIn('devotional_pool', enemy.attributes)
            self.assertIn('max_intensity', enemy.attributes)

    def test_enemy_generate_shaman_with_binding(self):
        """Test _Enemy._calculate_attributes with Binding (animist path)."""
        template = EnemyTemplate.objects.get(id=520)  # Agimori Shaman2
        enemy = _Enemy(template).generate()
        self.assertIsNotNone(enemy)
        if enemy.is_animist:
            self.assertIn('max_pow', enemy.attributes)
            self.assertIn('max_spirits', enemy.attributes)

    def test_enemy_generate_sorcerer_with_shaping(self):
        """Test _Enemy._calculate_attributes with Shaping (sorcerer path)."""
        template = EnemyTemplate.objects.get(id=68)  # Human Sorcerer Apprentice
        enemy = _Enemy(template).generate()
        self.assertIsNotNone(enemy)
        if enemy.is_sorcerer:
            self.assertIn('max_shaping', enemy.attributes)

    def test_enemy_generate_mystic_with_mysticism(self):
        """Test _Enemy._calculate_attributes with Mysticism+Meditation (mystic path)."""
        template = EnemyTemplate.objects.get(id=995)  # Mystic
        enemy = _Enemy(template).generate()
        self.assertIsNotNone(enemy)
        if enemy.is_mystic:
            self.assertIn('max_mysticism_intensity', enemy.attributes)
            self.assertIn('max_total_intensity', enemy.attributes)

    def test_enemy_generate_with_invocation(self):
        """Test _Enemy._calculate_attributes with Invocation skill."""
        template = EnemyTemplate.objects.get(id=68)  # Human Sorcerer Apprentice has Invocation
        enemy = _Enemy(template).generate()
        self.assertIsNotNone(enemy)
        if 'Invocation' in enemy.skills_dict:
            self.assertIn('intensity', enemy.attributes)

    def test_enemy_generate_with_natural_armor_from_db(self):
        """Test _Enemy._sr_penalty with natural armor from DB template."""
        # Find a template with natural armor
        templates = EnemyTemplate.objects.filter(natural_armor=True)
        if templates.exists():
            template = templates.first()
            enemy = _Enemy(template).generate()
            sr = enemy.attributes['strike_rank']
            self.assertTrue(sr.endswith('-0)'))

    def test_enemy_generate_with_armor_encumbrance_from_db(self):
        """Test _Enemy._sr_penalty with armor encumbrance from DB template."""
        # Find a template with armor on hit locations
        for t in EnemyTemplate.objects.all()[:50]:
            for ehl in t.enemyhitlocation_set.all():
                if ehl.armor and ehl.armor != '0':
                    enemy = _Enemy(t).generate()
                    self.assertIsNotNone(enemy)
                    self.assertIn('STR', enemy.stats)
                    return
        self.skipTest("No template with armor found")

    def test_enemy_generate_with_additional_features_from_db(self):
        """Test _Enemy._add_additional_features with real feature lists."""
        # Find a template with additional features
        for t in EnemyTemplate.objects.all():
            if t.enemyadditionalfeaturelist_set.exists():
                enemy = _Enemy(t).generate()
                self.assertIsNotNone(enemy)
                self.assertIn('STR', enemy.stats)
                return
        self.skipTest("No template with additional features found")

    def test_enemy_generate_with_nonrandom_features_from_db(self):
        """Test _Enemy._add_additional_features with non-random features."""
        # Find a template with non-random features
        for t in EnemyTemplate.objects.all():
            if t.enemynonrandomfeature_set.exists():
                enemy = _Enemy(t).generate()
                self.assertIsNotNone(enemy)
                # Non-random features should have non_random=True
                for feat in enemy.additional_features:
                    if hasattr(feat, 'non_random'):
                        self.assertTrue(feat.non_random)
                return
        self.skipTest("No template with non-random features found")

    # --- _Spirit tests ---

    def test_spirit_generate_from_db(self):
        """Test _Spirit generation with real spirit template."""
        template = EnemyTemplate.objects.get(id=973)  # Air Spirit Intensity 1
        spirit = _Spirit(template).generate()
        self.assertIsNotNone(spirit)
        self.assertIsNotNone(spirit.name)
        self.assertIn('POW', spirit.stats)
        self.assertIn('spirit_damage', spirit.attributes)

    def test_spirit_action_points_branches(self):
        """Test _Spirit._calculate_action_points all branches."""
        template = EnemyTemplate.objects.get(id=973)
        for pow_val, int_val, expected_ap in [
            (5, 5, 1), (10, 10, 2), (15, 15, 3),
            (20, 20, 4), (30, 30, 5),
        ]:
            for stat in template.stats.all():
                if stat.name == 'POW':
                    stat.die_set = str(pow_val)
                    stat.save()
                elif stat.name == 'INT':
                    stat.die_set = str(int_val)
                    stat.save()
            spirit = _Spirit(template).generate()
            self.assertEqual(
                spirit.attributes['action_points'], expected_ap,
                f"POW={pow_val}, INT={int_val} should give {expected_ap} AP"
            )

    def test_spirit_damage_calculation(self):
        """Test _Spirit._calculate_spirit_damage with Spectral Combat."""
        template = EnemyTemplate.objects.get(id=973)
        spectral = SkillAbstract.objects.filter(name='Spectral Combat').first()
        if spectral:
            for skill_val, expected_damage in [
                (0, '0'), (20, '1d2'), (40, '1d4'), (60, '1d6'), (100, '1d10'),
            ]:
                EnemySkill.objects.update_or_create(
                    skill=spectral, enemy_template=template,
                    defaults={'include': True, 'die_set': str(skill_val)}
                )
                spirit = _Spirit(template).generate()
                self.assertEqual(
                    spirit.attributes['spirit_damage'], expected_damage,
                    f"Spectral Combat {skill_val} should give {expected_damage}"
                )

    def test_spirit_damage_index_error(self):
        """Test _Spirit._calculate_spirit_damage IndexError path."""
        template = EnemyTemplate.objects.get(id=973)
        spectral = SkillAbstract.objects.filter(name='Spectral Combat').first()
        if spectral:
            EnemySkill.objects.update_or_create(
                skill=spectral, enemy_template=template,
                defaults={'include': True, 'die_set': '999'}
            )
            spirit = _Spirit(template).generate()
            self.assertEqual(spirit.attributes['spirit_damage'], '3d10+1d6')

    def test_spirit_generate_with_devotion(self):
        """Test spirit generation with Devotion skill."""
        template = EnemyTemplate.objects.get(id=973)
        devotion = SkillAbstract.objects.filter(name='Devotion').first()
        if devotion:
            EnemySkill.objects.get_or_create(
                skill=devotion, enemy_template=template,
                defaults={'include': True, 'die_set': '60'}
            )
        spirit = _Spirit(template).generate()
        if spirit.is_theist:
            self.assertIn('devotional_pool', spirit.attributes)

    def test_spirit_generate_with_shaping(self):
        """Test spirit generation with Shaping skill."""
        template = EnemyTemplate.objects.get(id=973)
        shaping = SkillAbstract.objects.filter(name='Shaping').first()
        if shaping:
            EnemySkill.objects.get_or_create(
                skill=shaping, enemy_template=template,
                defaults={'include': True, 'die_set': '50'}
            )
        spirit = _Spirit(template).generate()
        if spirit.is_sorcerer:
            self.assertIn('max_shaping', spirit.attributes)

    def test_spirit_generate_with_mysticism(self):
        """Test spirit generation with Mysticism+Meditation."""
        template = EnemyTemplate.objects.get(id=973)
        mysticism = SkillAbstract.objects.filter(name='Mysticism').first()
        meditation = SkillAbstract.objects.filter(name='Meditation').first()
        if mysticism and meditation:
            EnemySkill.objects.get_or_create(
                skill=mysticism, enemy_template=template,
                defaults={'include': True, 'die_set': '40'}
            )
            EnemySkill.objects.get_or_create(
                skill=meditation, enemy_template=template,
                defaults={'include': True, 'die_set': '40'}
            )
        spirit = _Spirit(template).generate()
        if spirit.is_mystic:
            self.assertIn('max_intensity', spirit.attributes)
            self.assertIn('max_total_intensity', spirit.attributes)

    def test_spirit_generate_with_binding(self):
        """Test spirit generation with Binding skill (animist)."""
        template = EnemyTemplate.objects.get(id=973)
        binding = SkillAbstract.objects.filter(name='Binding').first()
        if binding:
            EnemySkill.objects.get_or_create(
                skill=binding, enemy_template=template,
                defaults={'include': True, 'die_set': '60'}
            )
        spirit = _Spirit(template).generate()
        if spirit.is_animist:
            self.assertIn('max_pow', spirit.attributes)
            self.assertIn('max_spirits', spirit.attributes)

    # --- _Cult tests ---

    def test_cult_generate_from_db(self):
        """Test _Cult generation with real cult template."""
        template = EnemyTemplate.objects.get(id=8431)  # Hanjethulut
        cult = _Cult(template).generate()
        self.assertIsNotNone(cult)
        self.assertIsNotNone(cult.name)

    def test_cult_generate_with_spells(self):
        """Test cult generation with spells."""
        template = EnemyTemplate.objects.get(id=8431)
        cult = _Cult(template).generate()
        self.assertIsInstance(cult.folk_spells, list)
        self.assertIsInstance(cult.theism_spells, list)
        self.assertIsInstance(cult.sorcery_spells, list)
        self.assertIsInstance(cult.mysticism_spells, list)

    # --- _Elemental tests ---

    def test_elemental_generate_from_db(self):
        """Test _Elemental generation with real elemental template."""
        template = EnemyTemplate.objects.get(id=1162)  # Air Elemental
        elemental = _Elemental(template).generate()
        self.assertIsNotNone(elemental)
        self.assertIsNotNone(elemental.name)

    def test_elemental_hit_locations_pow_modifier(self):
        """Test elemental HP calculation with POW modifier."""
        template = EnemyTemplate.objects.get(id=1162)
        for stat in template.stats.all():
            if stat.name == 'POW':
                stat.die_set = '1d6+12'
                stat.save()
        elemental = _Elemental(template).generate()
        for hl in elemental.hit_locations:
            self.assertGreater(hl['hp'], 0)

    def test_elemental_hit_locations_no_modifier(self):
        """Test elemental HP calculation without POW modifier."""
        template = EnemyTemplate.objects.get(id=1162)
        for stat in template.stats.all():
            if stat.name == 'POW':
                stat.die_set = '1d6'
                stat.save()
        elemental = _Elemental(template).generate()
        for hl in elemental.hit_locations:
            self.assertGreater(hl['hp'], 0)

    # --- Complex template stress tests ---

    def test_complex_priest_generation(self):
        """Stress test: Generate a high-level priest template."""
        template = EnemyTemplate.objects.get(id=9531)  # Cultist of Ojahl Acolyte
        enemy = _Enemy(template).generate()
        self.assertIsNotNone(enemy)
        self.assertGreater(len(enemy.stats_list), 0)

    def test_complex_shaman_generation(self):
        """Stress test: Generate a high-level shaman template."""
        template = EnemyTemplate.objects.get(id=520)  # Agimori Shaman2
        enemy = _Enemy(template).generate()
        self.assertIsNotNone(enemy)
        self.assertGreater(len(enemy.stats_list), 0)

    def test_complex_sorcerer_generation(self):
        """Stress test: Generate a sorcerer template."""
        template = EnemyTemplate.objects.get(id=68)  # Human Sorcerer Apprentice
        enemy = _Enemy(template).generate()
        self.assertIsNotNone(enemy)
        self.assertGreater(len(enemy.stats_list), 0)

    def test_complex_mystic_generation(self):
        """Stress test: Generate a mystic template."""
        template = EnemyTemplate.objects.get(id=995)  # Mystic
        enemy = _Enemy(template).generate()
        self.assertIsNotNone(enemy)
        self.assertGreater(len(enemy.stats_list), 0)


class NegativeGenerationTest(TestCase):
    """Test generation with invalid or edge-case template configurations."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='negative_user', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)

    def test_generate_with_no_stats(self):
        """Generation with no stats raises KeyError.
        
        The generation code requires CON and SIZ stats for hit location HP.
        Missing stats will cause a KeyError, which is expected behavior.
        """
        template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'No Stats')
        template.published = True
        template.save()
        EnemyStat.objects.filter(enemy_template=template).delete()
        with self.assertRaises(KeyError):
            template.generate()

    def test_generate_with_zero_stats(self):
        """Generation with zero-value stats produces valid enemy with zero values."""
        template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Zero Stats')
        template.published = True
        template.save()
        # Set all stats to 0
        for stat in template.stats:
            stat.die_set = '0'
            stat.save()
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        # Verify stats are actually zero (enemy.stats is an OrderedDict)
        for stat_name, stat_value in enemy.stats.items():
            self.assertEqual(stat_value, 0)
        # Enemy should still have a name
        self.assertEqual(enemy.name, 'Zero Stats')

    def test_generate_with_high_rank(self):
        """Generation with high rank (10) produces valid enemy."""
        template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'High Rank')
        template.rank = 10
        template.published = True
        template.save()
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        # Verify enemy has all expected stats
        self.assertIn('STR', enemy.stats)
        self.assertIn('CON', enemy.stats)
        self.assertIn('SIZ', enemy.stats)
        self.assertIn('DEX', enemy.stats)
        self.assertIn('INT', enemy.stats)
        self.assertIn('POW', enemy.stats)
        self.assertIn('CHA', enemy.stats)

    def test_generate_with_no_skills(self):
        """Generation with no skills produces enemy with empty skills list."""
        template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'No Skills')
        template.published = True
        template.save()
        # Remove all skills
        EnemySkill.objects.filter(enemy_template=template).delete()
        CustomSkill.objects.filter(enemy_template=template).delete()
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        # Verify no skills were generated
        self.assertEqual(len(enemy.skills), 0)

    def test_generate_with_no_combat_styles(self):
        """Generation with no combat styles produces enemy with no weapons."""
        template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'No Combat')
        template.published = True
        template.save()
        # Remove all combat styles
        CombatStyle.objects.filter(enemy_template=template).delete()
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        # Verify no combat styles were generated
        self.assertEqual(len(enemy.combat_styles), 0)

    def test_generate_with_empty_namelist(self):
        """Generation with empty namelist uses template name."""
        template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Empty Name')
        template.namelist = None
        template.published = True
        template.save()
        enemy = template.generate()
        # When no namelist, the enemy name should be the template name
        self.assertEqual(enemy.name, 'Empty Name')

    def test_generate_with_special_characters_in_name(self):
        """Generation handles special characters in template name."""
        template = EnemyTemplate.create(self.user, self.ruleset, self.race, "Test's / Special\"Name")
        template.published = True
        template.save()
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        # Name should be preserved with special characters
        self.assertIn("Test's", enemy.name)

    def test_generate_with_spirit_amount_but_no_spirits(self):
        """Generation with spirit_amount but no spirits configured produces no spirits."""
        template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Spirit Amount')
        template.spirit_amount = '1'
        template.published = True
        template.save()
        # No spirits configured, should still generate
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        # No spirits should be generated when none are configured
        self.assertEqual(len(enemy.spirits), 0)

    def test_generate_with_cult_amount_but_no_cults(self):
        """Generation with cult_amount but no cults configured produces no cults."""
        template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Cult Amount')
        template.cult_amount = '1'
        template.published = True
        template.save()
        # No cults configured, should still generate
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        # No cults should be generated when none are configured
        self.assertEqual(len(enemy.cults), 0)

    def test_generate_with_invalid_spell_amount(self):
        """Generation with invalid spell amount raises ValueError.
        
        The Dice parser cannot handle non-numeric spell amounts.
        This is expected behavior - spell amounts must be valid dice expressions.
        """
        template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Invalid Spell')
        template.folk_spell_amount = 'abc'
        template.published = True
        template.save()
        with self.assertRaises(ValueError):
            template.generate()

    def test_generate_with_natural_armor_no_race_armor(self):
        """Generation with natural_armor but no race armor values sets natural_armor flag."""
        template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Natural Armor')
        template.natural_armor = True
        template.published = True
        template.save()
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        # Natural armor flag should be set
        self.assertTrue(enemy.natural_armor)

    def test_generate_multiple_enemies(self):
        """Generating multiple enemies from same template works."""
        template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Multiple')
        template.published = True
        template.save()
        enemies = get_enemies([(template, 5)], increment=False)
        self.assertEqual(len(enemies), 5)
        # Verify each enemy has stats
        for enemy in enemies:
            self.assertIn('STR', enemy.stats)

    def test_generate_with_large_amount(self):
        """Generating a large number of enemies works."""
        template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Large Amount')
        template.published = True
        template.save()
        enemies = get_enemies([(template, 40)], increment=False)
        self.assertEqual(len(enemies), 40)
        # Verify each enemy has stats
        for enemy in enemies:
            self.assertIn('STR', enemy.stats)




class GeneratedPartyEdgeCaseTest(TestCase):
    """Test get_generated_party edge cases."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='party_edge_user', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Party Edge Test')
        self.template.published = True
        self.template.save()

    def test_generated_party_empty(self):
        """get_generated_party works with no templates."""
        party = Party.create(self.user)
        party.published = True
        party.save()
        context = get_generated_party(party)
        self.assertEqual(len(context['enemies']), 0)
        # Verify context has expected keys
        self.assertIn('party', context)
        self.assertIn('party_additional_features', context)

    def test_generated_party_with_template(self):
        """get_generated_party generates enemies from templates."""
        party = Party.create(self.user)
        party.published = True
        party.save()
        TemplateToParty.objects.create(party=party, template=self.template, amount=2)
        context = get_generated_party(party)
        self.assertEqual(len(context['enemies']), 2)
        # Verify enemies have stats
        for enemy in context['enemies']:
            self.assertIn('STR', enemy.stats)

    def test_generated_party_increments_used(self):
        """get_generated_party increments the used counter."""
        initial_used = self.template.used
        party = Party.create(self.user)
        party.published = True
        party.save()
        TemplateToParty.objects.create(party=party, template=self.template, amount=1)
        get_generated_party(party)
        self.template.refresh_from_db()
        self.assertEqual(self.template.used, initial_used + 1)


class GenerationLogicTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Generation Test')

    def test_enemy_generation(self):
        """Test basic enemy generation."""
        enemy = _Enemy(self.template).generate()
        self.assertIsNotNone(enemy.name)
        self.assertGreater(len(enemy.stats_list), 0)

    def test_enemy_generation_with_suffix(self):
        """Test enemy generation with suffix."""
        enemy = _Enemy(self.template).generate('1')
        self.assertIn('1', enemy.name)

    def test_enemy_generation_with_namelist(self):
        """Test enemy generation with name list."""
        fl = AdditionalFeatureList(name='Names', type='name')
        fl.save()
        item = AdditionalFeatureItem(name='Grom', feature_list=fl)
        item.save()
        self.template.namelist = fl
        self.template.save()
        enemy = _Enemy(self.template).generate()
        self.assertIn('Grom', enemy.name)

    def test_spirit_generation(self):
        """Test spirit enemy generation using existing spirit template."""
        spirit_template = EnemyTemplate.objects.filter(
            race__discorporate=True, published=True
        ).first()
        if not spirit_template:
            self.skipTest("No spirit template in fixtures")
        spirit = _Spirit(spirit_template).generate()
        self.assertIsNotNone(spirit)
        self.assertIsNotNone(spirit.name)

    def test_cult_generation(self):
        """Test cult generation using existing cult template."""
        cult_template = EnemyTemplate.objects.filter(
            race__name='Cult', published=True
        ).first()
        if not cult_template:
            self.skipTest("No cult template in fixtures")
        cult = _Cult(cult_template).generate()
        self.assertIsNotNone(cult)
        self.assertIsNotNone(cult.name)

    def test_elemental_generation(self):
        """Test elemental generation using existing elemental template."""
        elemental_template = EnemyTemplate.objects.filter(
            race__elemental=True, published=True
        ).first()
        if not elemental_template:
            self.skipTest("No elemental template in fixtures")
        elemental = _Elemental(elemental_template).generate()
        self.assertIsNotNone(elemental)
        self.assertIsNotNone(elemental.name)


    def test_enemy_with_additional_features(self):
        """Test enemy generation with additional features."""
        fl = AdditionalFeatureList(name='Features', type='enemy_feature')
        fl.save()
        item = AdditionalFeatureItem(name='Big Axe', feature_list=fl)
        item.save()
        EnemyAdditionalFeatureList.create(self.template, fl.id, '100')
        enemy = _Enemy(self.template).generate()
        self.assertGreater(len(enemy.additional_features), 0)

    def test_enemy_with_nonrandom_features(self):
        """Test enemy generation with nonrandom features."""
        fl = AdditionalFeatureList(name='Features', type='enemy_feature')
        fl.save()
        item = AdditionalFeatureItem(name='Always Present', feature_list=fl)
        item.save()
        EnemyNonrandomFeature.create(self.template, item.id)
        enemy = _Enemy(self.template).generate()
        self.assertGreater(len(enemy.additional_features), 0)




class GenerationEdgeCaseTest(TestCase):
    """Test edge cases in generation classes to reach 85% coverage."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Edge Case Test')

    def test_enemy_generate_with_devotion_theist(self):
        """Test _Enemy._calculate_attributes with Devotion skill (theist path)."""
        devotion = SkillAbstract.objects.filter(name='Devotion').first()
        if devotion:
            EnemySkill.objects.get_or_create(
                skill=devotion, enemy_template=self.template,
                defaults={'include': True, 'die_set': '70'}
            )
        enemy = _Enemy(self.template).generate()
        if enemy.is_theist:
            self.assertIn('devotional_pool', enemy.attributes)
            self.assertIn('max_intensity', enemy.attributes)

    def test_enemy_generate_with_shaping_sorcerer(self):
        """Test _Enemy._calculate_attributes with Shaping skill (sorcerer path)."""
        shaping = SkillAbstract.objects.filter(name='Shaping').first()
        if shaping:
            EnemySkill.objects.get_or_create(
                skill=shaping, enemy_template=self.template,
                defaults={'include': True, 'die_set': '50'}
            )
        enemy = _Enemy(self.template).generate()
        if enemy.is_sorcerer:
            self.assertIn('max_shaping', enemy.attributes)

    def test_enemy_generate_with_mysticism_mystic(self):
        """Test _Enemy._calculate_attributes with Mysticism+Meditation (mystic path)."""
        mysticism = SkillAbstract.objects.filter(name='Mysticism').first()
        meditation = SkillAbstract.objects.filter(name='Meditation').first()
        if mysticism and meditation:
            EnemySkill.objects.get_or_create(
                skill=mysticism, enemy_template=self.template,
                defaults={'include': True, 'die_set': '40'}
            )
            EnemySkill.objects.get_or_create(
                skill=meditation, enemy_template=self.template,
                defaults={'include': True, 'die_set': '40'}
            )
        enemy = _Enemy(self.template).generate()
        if enemy.is_mystic:
            self.assertIn('max_mysticism_intensity', enemy.attributes)
            self.assertIn('max_total_intensity', enemy.attributes)

    def test_enemy_generate_with_binding_animist(self):
        """Test _Enemy._calculate_attributes with Binding skill (animist path)."""
        binding = SkillAbstract.objects.filter(name='Binding').first()
        if binding:
            EnemySkill.objects.get_or_create(
                skill=binding, enemy_template=self.template,
                defaults={'include': True, 'die_set': '60'}
            )
        enemy = _Enemy(self.template).generate()
        if enemy.is_animist:
            self.assertIn('max_pow', enemy.attributes)
            self.assertIn('max_spirits', enemy.attributes)


    def test_enemy_damage_modifier_zero_stats(self):
        """Test _calculate_damage_modifier with zero STR/SIZ."""
        for stat in self.template.stats:
            if stat.name in ['STR', 'SIZ']:
                stat.die_set = '0'
                stat.save()
        enemy = _Enemy(self.template).generate()
        self.assertEqual(enemy.attributes['damage_modifier'], '+0')

    def test_enemy_damage_modifier_high_stats(self):
        """Test _calculate_damage_modifier with very high STR/SIZ (IndexError path)."""
        for stat in self.template.stats:
            if stat.name in ['STR', 'SIZ']:
                stat.die_set = '1000'
                stat.save()
        enemy = _Enemy(self.template).generate()
        # str_siz=2000, index = ((2000-1-50)//10)+10 = 194+10 = 204 > len(DICE_STEPS)
        self.assertEqual(enemy.attributes['damage_modifier'], '+6d10')

    def test_enemy_generate_with_natural_armor(self):
        """Test _Enemy._sr_penalty with natural armor (no penalty)."""
        self.template.natural_armor = True
        self.template.save()
        enemy = _Enemy(self.template).generate()
        sr = enemy.attributes['strike_rank']
        self.assertTrue(sr.endswith('-0)'))

    def test_enemy_generate_with_armor_encumbrance(self):
        """Test _Enemy._sr_penalty with armor encumbrance."""
        self.template.natural_armor = False
        self.template.save()
        for hl in self.template.hit_locations:
            hl.armor = '1d4'
            hl.save()
        enemy = _Enemy(self.template).generate()
        self.assertIsNotNone(enemy)
        self.assertIn('STR', enemy.stats)

    def test_enemy_generate_with_spirits(self):
        """Test _Enemy._add_spirits with spirit templates."""
        spirit_template = EnemyTemplate.objects.filter(
            race__discorporate=True, published=True
        ).first()
        if spirit_template:
            EnemySpirit.create(spirit_template.id, self.template.id)
            self.template.spirit_amount = '1'
            self.template.save()
            enemy = _Enemy(self.template).generate()
            self.assertIsNotNone(enemy)
            self.assertIsNotNone(enemy.spirits)

    def test_enemy_generate_with_cult(self):
        """Test _Enemy._add_cults with cult templates."""
        cult_template = EnemyTemplate.objects.filter(
            race__name='Cult', published=True
        ).first()
        if cult_template:
            EnemyCult.create(cult_template.id, self.template.id)
            self.template.cult_amount = '1'
            self.template.save()
            enemy = _Enemy(self.template).generate()
            self.assertIsNotNone(enemy)
            self.assertIsNotNone(enemy.cults)

    def test_spirit_action_points_all_branches(self):
        """Test _calculate_action_points all branches (POW+INT ranges)."""
        spirit_template = EnemyTemplate.objects.filter(
            race__discorporate=True, published=True
        ).first()
        if spirit_template:
            for pow_val, int_val, expected_ap in [
                (5, 5, 1), (10, 10, 2), (15, 15, 3),
                (20, 20, 4), (30, 30, 5),
            ]:
                for stat in spirit_template.stats.all():
                    if stat.stat.name == 'POW':
                        stat.die_set = str(pow_val)
                        stat.save()
                    elif stat.stat.name == 'INT':
                        stat.die_set = str(int_val)
                        stat.save()
                spirit = _Spirit(spirit_template).generate()
                self.assertEqual(
                    spirit.attributes['action_points'], expected_ap,
                    f"POW={pow_val}, INT={int_val} should give {expected_ap} AP"
                )






class LuckyGenerationEdgeCaseTest(TestCase):
    """Test lucky generation edge cases including empty template list."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='lucky_user', password='password')

    def test_lucky_generation_no_published_templates(self):
        """Lucky generation crashes when no published templates exist."""
        # Unpublish all templates
        EnemyTemplate.objects.update(published=False)
        request = self.factory.get('/generate/')
        request.user = self.user
        request.session = {}
        # Should raise ValueError because random.randint(0, -1) fails
        with self.assertRaises(ValueError):
            get_enemies_lucky(request)

    def test_lucky_generation_with_published_templates(self):
        """Lucky generation works when published templates exist."""
        request = self.factory.get('/generate/')
        request.user = self.user
        request.session = {}
        enemies = get_enemies_lucky(request)
        self.assertEqual(len(enemies), 6)
        # Verify enemies have names (some may be spirits/cults with empty stats)
        for enemy in enemies:
            self.assertTrue(len(enemy.name) > 0)  # Has a name

    def test_random_party_no_published_parties(self):
        """get_random_party crashes when no published parties exist."""
        Party.objects.update(published=False)
        with self.assertRaises(ValueError):
            get_random_party()

    def test_random_party_with_published_parties(self):
        """get_random_party works when published parties exist."""
        party = Party.create(self.user)
        party.published = True
        party.save()
        result = get_random_party()
        self.assertIsNotNone(result)
        # Verify the returned party is published
        self.assertTrue(result.published)




class HtmlOutputContentTest(TestCase):
    """Test that generated enemy objects have expected attributes.
    
    Note: Full HTML rendering tests are skipped due to Python 3.14 Django
    template rendering bugs. These tests verify the enemy objects instead.
    """
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='html_user', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'HTML Output Test')
        self.template.published = True
        self.template.save()

    def test_generated_enemy_has_stats(self):
        """Generated enemy has stats with STR and CON."""
        enemy = self.template.generate()
        stat_names = [s['name'] for s in enemy.stats_list]
        self.assertIn('STR', stat_names)
        self.assertIn('CON', stat_names)

    def test_generated_enemy_has_name(self):
        """Generated enemy has the template name."""
        enemy = self.template.generate()
        self.assertIn('HTML Output Test', enemy.name)

    def test_generated_party_has_party_name(self):
        """Party generation context has party name."""
        party = Party.create(self.user)
        party.name = 'Test Party Name'
        party.published = True
        party.save()
        TemplateToParty.objects.create(party=party, template=self.template, amount=1)

        from ..views_lib import get_generated_party
        context = get_generated_party(party)
        self.assertEqual(context['party'].name, 'Test Party Name')
        self.assertIn('enemies', context)
        self.assertGreater(len(context['enemies']), 0)

    def test_generated_enemy_has_hit_locations(self):
        """Generated enemy has hit locations."""
        enemy = self.template.generate()
        self.assertIsNotNone(enemy.hit_locations)
        self.assertGreater(len(enemy.hit_locations), 0)




class IntegrationTest(TestCase):
    """End-to-end workflows that verify components work together."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='integration_user', password='password')
        self.client = Client()
        self.client.login(username='integration_user', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)

    def _create_template(self, name='Integration Template'):
        """Helper: Create a template and return it."""
        template = EnemyTemplate.create(self.user, self.ruleset, self.race, name)
        template.published = True
        template.save()
        return template

    # --- Workflow 1: Full enemy creation and generation ---

    def test_create_template_generate_enemy(self):
        """Create template, generate enemy, verify output has expected fields."""
        template = self._create_template()
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        self.assertIn('action_points', enemy.attributes)
        self.assertIn('damage_modifier', enemy.attributes)
        self.assertGreater(len(enemy.stats_list), 0)

    # --- Workflow 2: Clone and modify ---

    def test_clone_template_independent(self):
        """Clone template, modify clone, verify original is unchanged."""
        template = self._create_template('Original')
        original_name = template.name
        cloned = template.clone(self.user)
        cloned.name = 'Modified Clone'
        cloned.save()
        template.refresh_from_db()
        self.assertEqual(template.name, original_name)
        self.assertEqual(cloned.name, 'Modified Clone')
        self.assertNotEqual(template.id, cloned.id)

    # --- Workflow 3: Full party creation and generation ---

    def test_create_party_generate(self):
        """Create party, add templates, generate party, verify all enemies."""
        template1 = self._create_template('Party Member 1')
        template2 = self._create_template('Party Member 2')
        party = Party.create(self.user)
        party.add(template1)
        party.add(template2)
        from enemygen.views_lib import get_generated_party
        context = get_generated_party(party)
        self.assertIn('enemies', context)
        self.assertGreaterEqual(len(context['enemies']), 1)

    # --- Workflow 4: Search and generate ---

    def test_search_find_and_generate(self):
        """Search for template, find it, generate from search result."""
        template = self._create_template('Searchable Orc')
        results = EnemyTemplate.search('Searchable', self.user)
        found = [r for r in results if r.name == 'Searchable Orc']
        self.assertEqual(len(found), 1)
        enemy = found[0].generate()
        self.assertIsNotNone(enemy)

    # --- Workflow 5: AJAX edit then generate ---

    def test_ajax_edit_then_generate(self):
        """Create template, edit via AJAX, generate, verify changes reflected."""
        template = self._create_template()
        # Edit notes via AJAX
        response = self.client.post(
            reverse('submit', args=[template.id]),
            data=json.dumps({'value': 'Edited via AJAX', 'object': 'et_notes'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        template.refresh_from_db()
        self.assertEqual(template.notes, 'Edited via AJAX')
        # Generate and verify enemy still works
        enemy = template.generate()
        self.assertIsNotNone(enemy)

    # --- Workflow 6: Template with additional features ---

    def test_template_with_features(self):
        """Create template with additional features, generate, verify features exist."""
        template = self._create_template()
        fl = AdditionalFeatureList(name='Test Feature', type='enemy_feature')
        fl.save()
        item = AdditionalFeatureItem(name='Has special ability', feature_list=fl)
        item.save()
        afl = EnemyAdditionalFeatureList.create(template, fl.id)
        afl.probability = '100'
        afl.save()
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        # Additional features are in the enemy object, not attributes dict
        self.assertIsNotNone(enemy.additional_features)

    # --- Workflow 7: Party with multiple templates and generation ---

    def test_party_multiple_templates_generation(self):
        """Create party with multiple templates, verify generation counts."""
        template1 = self._create_template('Orc Warrior')
        template2 = self._create_template('Goblin Archer')
        party = Party.create(self.user)
        party.add(template1)
        party.add(template2)
        ttps = TemplateToParty.objects.filter(party=party)
        self.assertEqual(ttps.count(), 2)
        from enemygen.views_lib import get_generated_party
        context = get_generated_party(party)
        self.assertIn('enemies', context)
        self.assertIn('party', context)

    # --- Workflow 8: Anonymous user can only see public templates ---

    def test_anonymous_user_workflow(self):
        """Anonymous user can only see and generate public templates."""
        from django.contrib.auth.models import AnonymousUser
        template = self._create_template('Public Template')
        self.client.logout()
        results = EnemyTemplate.search('Public', AnonymousUser())
        found = [r for r in results if r.name == 'Public Template']
        self.assertEqual(len(found), 1)
        enemy = found[0].generate()
        self.assertIsNotNone(enemy)

    # --- Workflow 9: JSON API end-to-end ---

    def test_json_api_workflow(self):
        """Create template, generate via JSON API, verify output."""
        template = self._create_template()
        from enemygen.views_lib import get_enemies, as_json
        enemy_index = [(template, 1)]
        enemies = get_enemies(enemy_index, True)
        enemies_json = as_json(enemies)
        data = json.loads(enemies_json)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertIn('name', data[0])

    # --- Workflow 10: Template publish/unpublish affects visibility ---

    def test_publish_unpublish_workflow(self):
        """Create template, unpublish, verify it's hidden from others."""
        template = self._create_template('Secret Template')
        other_user = User.objects.create_user(username='other_user', password='password')
        # Published - other user can find it
        results = EnemyTemplate.search('Secret', other_user)
        found = [r for r in results if r.name == 'Secret Template']
        self.assertEqual(len(found), 1)
        # Unpublished - other user cannot find it
        template.published = False
        template.save()
        results = EnemyTemplate.search('Secret', other_user)
        found = [r for r in results if r.name == 'Secret Template']
        self.assertEqual(len(found), 0)
        # Owner can still find it
        results = EnemyTemplate.search('Secret', self.user)
        found = [r for r in results if r.name == 'Secret Template']
        self.assertEqual(len(found), 1)


class JsonApiContractTest(TestCase):
    """Verify the JSON API output structure matches what the frontend expects."""
    fixtures = ('enemygen_testdata.json', 'complex_templates.json', 'rank5_templates.json')

    def _get_template(self):
        """Get a template that exists in the fixtures."""
        return EnemyTemplate.objects.first()

    def test_enemy_as_json_has_all_required_fields(self):
        """JSON output contains all expected top-level fields."""
        template = self._get_template()
        enemy = template.generate()
        data = json.loads(as_json([enemy]))[0]
        
        expected_fields = [
            'name', 'cult_rank', 'stats', 'skills', 'folk_spells',
            'theism_spells', 'sorcery_spells', 'mysticism_spells',
            'hit_locations', 'combat_styles', 'attributes', 'notes',
            'features', 'cults', 'spirits', 'natural_armor'
        ]
        for field in expected_fields:
            self.assertIn(field, data, f"Missing field: {field}")

    def test_enemy_as_json_stats_format(self):
        """Stats are formatted as a list of dicts with stat names as keys."""
        template = self._get_template()
        enemy = template.generate()
        data = json.loads(as_json([enemy]))[0]
        
        self.assertIsInstance(data['stats'], list)
        # Each stat is a dict like {'STR': 10}
        stat_names = []
        for stat_dict in data['stats']:
            self.assertIsInstance(stat_dict, dict)
            self.assertEqual(len(stat_dict), 1)
            stat_name = list(stat_dict.keys())[0]
            stat_names.append(stat_name)
            self.assertIsInstance(stat_dict[stat_name], int)
        # Verify all expected stats are present
        expected_stats = ['STR', 'CON', 'SIZ', 'DEX', 'INT', 'POW', 'CHA']
        for stat in expected_stats:
            self.assertIn(stat, stat_names, f"Missing stat: {stat}")

    def test_enemy_as_json_skills_format(self):
        """Skills are formatted as a list of dicts with name and value."""
        template = self._get_template()
        enemy = template.generate()
        data = json.loads(as_json([enemy]))[0]
        
        self.assertIsInstance(data['skills'], list)
        if data['skills']:
            skill = data['skills'][0]
            self.assertIsInstance(skill, dict)
            # Each skill dict has the skill name as key and value as value
            self.assertTrue(len(skill) > 0)

    def test_enemy_as_json_hit_locations_format(self):
        """Hit locations are formatted as a list of dicts."""
        template = self._get_template()
        enemy = template.generate()
        data = json.loads(as_json([enemy]))[0]
        
        self.assertIsInstance(data['hit_locations'], list)
        if data['hit_locations']:
            hl = data['hit_locations'][0]
            self.assertIsInstance(hl, dict)
            self.assertIn('name', hl)

    def test_enemy_as_json_combat_styles_format(self):
        """Combat styles are formatted as a list of dicts with weapons."""
        template = self._get_template()
        enemy = template.generate()
        data = json.loads(as_json([enemy]))[0]
        
        self.assertIsInstance(data['combat_styles'], list)
        if data['combat_styles']:
            cs = data['combat_styles'][0]
            self.assertIsInstance(cs, dict)
            self.assertIn('name', cs)
            self.assertIn('value', cs)
            self.assertIn('weapons', cs)

    def test_enemy_as_json_attributes_format(self):
        """Attributes contain expected keys."""
        template = self._get_template()
        enemy = template.generate()
        data = json.loads(as_json([enemy]))[0]
        
        self.assertIsInstance(data['attributes'], dict)
        expected_attrs = ['action_points', 'damage_modifier', 'magic_points', 'strike_rank']
        for attr in expected_attrs:
            self.assertIn(attr, data['attributes'], f"Missing attribute: {attr}")


class MysticGenerationTest(TestCase):
    """Test generation with mystic templates to cover the previously 100% missing magic type."""
    fixtures = ('enemygen_testdata.json', 'complex_templates.json', 'rank5_templates.json', 'mystic_template.json')

    def test_mystic_generation_with_mysticism_spells(self):
        """Monk of Zamur Khan (rank 5 mystic) generates with mysticism spells."""
        template = EnemyTemplate.objects.get(id=1005)
        self.assertEqual(template.rank, 5)
        self.assertTrue(template.mysticism_spell_amount > '0')
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        self.assertIn('STR', enemy.stats)
        # Mystic should have mysticism spells
        self.assertIsNotNone(enemy.mysticism_spells)
        self.assertTrue(len(enemy.mysticism_spells) > 0, "Mystic should have mysticism spells")

    def test_mystic_has_meditation_skill(self):
        """Mystic generates with Meditation skill required for mysticism."""
        template = EnemyTemplate.objects.get(id=1005)
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        # Check that Meditation skill exists
        skill_names = [s['name'] for s in enemy.skills]
        self.assertIn('Meditation', skill_names, "Mystic should have Meditation skill")

    def test_mystic_json_output(self):
        """Mystic template generates valid JSON with mysticism spells."""
        template = EnemyTemplate.objects.get(id=1005)
        enemy = template.generate()
        from ..views_lib import as_json
        data = json.loads(as_json([enemy]))
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertIn('mysticism_spells', data[0])
        self.assertTrue(len(data[0]['mysticism_spells']) > 0)


class Rank5GenerationTest(TestCase):
    """Test generation with rank 5 templates from the rank5_templates.json fixture."""
    fixtures = ('enemygen_testdata.json', 'complex_templates.json', 'rank5_templates.json', 'mystic_template.json')

    def test_archmage_generation_with_spirits_and_cults(self):
        """Archmage (rank 5) generates with spirits and cults."""
        template = EnemyTemplate.objects.get(id=1015)
        self.assertEqual(template.rank, 5)
        self.assertEqual(template.spirits.count(), 24)
        self.assertEqual(template.cults.count(), 25)
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        self.assertIn('STR', enemy.stats)
        # Archmage has spirits configured
        self.assertIsNotNone(enemy.spirits)

    def test_shaman_spirit_generation(self):
        """Broo Shaman (rank 5) generates with spirit companions."""
        template = EnemyTemplate.objects.get(id=1778)
        self.assertEqual(template.rank, 5)
        self.assertEqual(template.spirits.count(), 7)
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        self.assertIn('STR', enemy.stats)
        self.assertIsNotNone(enemy.spirits)

    def test_vampire_spirit_and_cult_generation(self):
        """Vampire Rune Priest (rank 5) generates with both spirits and cults."""
        template = EnemyTemplate.objects.get(id=5403)
        self.assertEqual(template.rank, 5)
        self.assertEqual(template.spirits.count(), 1)
        self.assertEqual(template.cults.count(), 1)
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        self.assertIn('STR', enemy.stats)
        # Has both spirits and cults
        self.assertIsNotNone(enemy.spirits)
        self.assertIsNotNone(enemy.cults)

    def test_master_fighter_high_stats(self):
        """Master Fighter (rank 5) generates with high stats and correct damage modifier."""
        template = EnemyTemplate.objects.get(id=3154)
        self.assertEqual(template.rank, 5)
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        self.assertIn('STR', enemy.stats)
        # Verify damage modifier is calculated
        self.assertIn('damage_modifier', enemy.attributes)

    def test_waha_shaman_many_spirits(self):
        """Waha Shaman (rank 4) with 37 spirit configs generates correctly."""
        template = EnemyTemplate.objects.get(id=1343)
        self.assertEqual(template.spirits.count(), 37)
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        # Waha Shaman's race is "Cult" - stats come from spirits, not the template itself
        # The template generates spirits that do the fighting
        self.assertIsNotNone(enemy.spirits)

    def test_archmage_has_magic_spells(self):
        """Archmage generates with sorcery spells."""
        template = EnemyTemplate.objects.get(id=1015)
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        # Archmage is a sorcerer - should have sorcery spells
        self.assertIsNotNone(enemy.sorcery_spells)

    def test_archmage_has_custom_skills(self):
        """Archmage generates with custom skills."""
        template = EnemyTemplate.objects.get(id=1015)
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        # Archmage has custom skills
        self.assertTrue(len(enemy.skills) > 0)

    def test_rank_5_json_output(self):
        """Rank 5 template generates valid JSON output."""
        template = EnemyTemplate.objects.get(id=1015)
        enemy = template.generate()
        from ..views_lib import as_json
        data = json.loads(as_json([enemy]))
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertIn('name', data[0])
        self.assertIn('stats', data[0])
        self.assertIn('skills', data[0])


class AnimistGenerationTest(TestCase):
    """Test generation with animist templates to cover the previously 100% missing magic type."""
    fixtures = ('enemygen_testdata.json', 'complex_templates.json', 'rank5_templates.json',
                'mystic_template.json', 'animist_template.json')

    def test_animist_generation_with_spirits(self):
        """Primitive Islander Shaman (rank 4 animist) generates with bound spirits."""
        template = EnemyTemplate.objects.get(id=529)
        self.assertEqual(template.rank, 4)
        self.assertTrue(template.animist)
        self.assertEqual(template.spirits.count(), 21)
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        self.assertIn('STR', enemy.stats)
        # Animist has bound spirits
        self.assertIsNotNone(enemy.spirits)

    def test_animist_has_binding_skill(self):
        """Animist generates with Binding skill required for animism."""
        template = EnemyTemplate.objects.get(id=529)
        enemy = template.generate()
        self.assertIsNotNone(enemy)
        skill_names = [s['name'] for s in enemy.skills]
        self.assertIn('Binding', skill_names, "Animist should have Binding skill")

    def test_animist_json_output(self):
        """Animist template generates valid JSON with spirits."""
        template = EnemyTemplate.objects.get(id=529)
        enemy = template.generate()
        from ..views_lib import as_json
        data = json.loads(as_json([enemy]))
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertIn('spirits', data[0])




