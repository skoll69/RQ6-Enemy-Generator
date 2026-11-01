"""
Consolidated AJAX endpoint tests.

This file combines all AJAX-related tests from:
- test_ajax_coverage.py (AjaxEndpointTest)
- test_base.py (TestAjax)
- test_coverage_gap.py (AjaxSubmitCoverageTest)
- test_edge_cases.py (AjaxErrorMessageTest)
- test_exception_handling.py (AjaxErrorBranchTest)
"""
from django.test import TestCase, RequestFactory, Client, SimpleTestCase
from django.contrib.auth.models import User
from django.urls import reverse
import json
import os
import tempfile

from ..models import (
    EnemyTemplate, Party, Race, Ruleset, CombatStyle, Weapon,
    AdditionalFeatureList, AdditionalFeatureItem, CustomSpell, CustomSkill,
    CustomWeapon, HitLocation, EnemySpirit, EnemyCult,
    EnemyAdditionalFeatureList, EnemyNonrandomFeature,
    PartyAdditionalFeatureList, PartyNonrandomFeature, TemplateToParty,
    EnemyStat, StatAbstract, SpellAbstract, EnemySpell, EnemySkill,
    SkillAbstract, EnemyWeapon, RaceStat,
)
from ..views_lib import (
    get_enemy_templates, get_party_templates,
)
from ..ajax import change_template
from django.conf import settings
from django.test import override_settings


class AjaxEndpointTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = Client()
        self.client.login(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Ajax Test')
        self.party = Party.create(self.user)
        self.party.add(self.template)

    def test_add_template_to_party(self):
        """Test adding a template to a party via AJAX."""
        new_template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'New Template')
        response = self.client.post(
            reverse('add_template_to_party', args=[self.party.id]),
            data=json.dumps({'template_ids': [new_template.id]}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.party.refresh_from_db()
        self.assertEqual(self.party.template_specs.count(), 2)

    def test_add_template_to_party_empty(self):
        """Test adding empty template list returns failure."""
        response = self.client.post(
            reverse('add_template_to_party', args=[self.party.id]),
            data=json.dumps({'template_ids': []}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])

    def test_add_custom_spell(self):
        """Test adding a custom spell via AJAX."""
        response = self.client.post(
            reverse('add_custom_spell', args=[self.template.id, 'folk']),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(CustomSpell.objects.filter(enemy_template=self.template, type='folk').count(), 1)

    def test_add_custom_skill(self):
        """Test adding a custom skill via AJAX."""
        response = self.client.post(
            reverse('add_custom_skill', args=[self.template.id]),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.template.refresh_from_db()
        self.assertEqual(self.template.custom_skills.count(), 1)

    def test_add_spirit(self):
        """Test adding a spirit via AJAX."""
        spirit_template = EnemyTemplate.objects.filter(
            race__discorporate=True, published=True
        ).first()
        if spirit_template:
            response = self.client.post(
                reverse('add_spirit', args=[self.template.id]),
                data=json.dumps({'spirit_ids': [spirit_template.id]}),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.template.refresh_from_db()
            self.assertEqual(self.template.spirits.count(), 1)

    def test_add_cult(self):
        """Test adding a cult via AJAX."""
        cult_template = EnemyTemplate.objects.filter(
            race__name='Cult', published=True
        ).first()
        if cult_template:
            response = self.client.post(
                reverse('add_cult', args=[self.template.id]),
                data=json.dumps({'cult_ids': [cult_template.id]}),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.template.refresh_from_db()
            self.assertEqual(self.template.cults.count(), 1)

    def test_add_cult_empty(self):
        """Test adding empty cult list returns failure."""
        response = self.client.post(
            reverse('add_cult', args=[self.template.id]),
            data=json.dumps({'cult_ids': []}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])

    def test_add_nonrandom_feature(self):
        """Test adding nonrandom feature via AJAX."""
        fl = AdditionalFeatureList(name='Test Feature', type='enemy_feature')
        fl.save()
        item = AdditionalFeatureItem(name='Feature Item', feature_list=fl)
        item.save()
        response = self.client.post(
            reverse('add_nonrandom_feature', args=[item.id]),
            data=json.dumps({'et_id': self.template.id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_add_nonrandom_feature_to_party(self):
        """Test adding nonrandom feature to party via AJAX."""
        fl = AdditionalFeatureList(name='Party Feature', type='party_feature')
        fl.save()
        item = AdditionalFeatureItem(name='Party Item', feature_list=fl)
        item.save()
        response = self.client.post(
            reverse('add_nonrandom_feature', args=[item.id]),
            data=json.dumps({'party_id': self.party.id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_add_custom_weapon(self):
        """Test adding a custom weapon via AJAX."""
        cs = self.template.combat_styles.first()
        response = self.client.post(
            reverse('add_custom_weapon', args=[cs.id, '1h-melee']),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_add_hit_location(self):
        """Test adding a hit location via AJAX."""
        response = self.client.post(
            reverse('add_hit_location', args=[self.race.id]),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_del_item_hit_location(self):
        """Test deleting a hit location via AJAX."""
        hl = HitLocation.create(self.race.id)
        response = self.client.post(
            reverse('del_item', args=[hl.id, 'hit_location']),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_del_item_custom_weapon(self):
        """Test deleting a custom weapon via AJAX."""
        cs = self.template.combat_styles.first()
        cw = CustomWeapon.create(cs.id, '1h-melee', 'Test Weapon', 10)
        response = self.client.post(
            reverse('del_item', args=[cw.id, 'custom_weapon']),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_del_item_party_template_spec(self):
        """Test deleting a party template spec via AJAX."""
        ttp = TemplateToParty.objects.get(party=self.party)
        response = self.client.post(
            reverse('del_item', args=[ttp.id, 'party_template_spec']),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_del_item_et_spirit(self):
        """Test deleting an enemy spirit via AJAX."""
        spirit_template = EnemyTemplate.objects.filter(
            race__discorporate=True, published=True
        ).first()
        if spirit_template:
            es = EnemySpirit.create(spirit_template.id, self.template.id)
            response = self.client.post(
                reverse('del_item', args=[es.id, 'et_spirit']),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])

    def test_del_item_et_cult(self):
        """Test deleting an enemy cult via AJAX."""
        cult_template = EnemyTemplate.objects.filter(
            race__name='Cult', published=True
        ).first()
        if cult_template:
            ec = EnemyCult.create(cult_template.id, self.template.id)
            response = self.client.post(
                reverse('del_item', args=[ec.id, 'et_cult']),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])

    def test_del_item_et_additional_feature(self):
        """Test deleting an enemy additional feature via AJAX."""
        fl = AdditionalFeatureList(name='Feature', type='enemy_feature')
        fl.save()
        afl = EnemyAdditionalFeatureList.create(self.template, fl.id)
        response = self.client.post(
            reverse('del_item', args=[afl.id, 'et_additional_feature']),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_del_item_party_additional_feature(self):
        """Test deleting a party additional feature via AJAX."""
        fl = AdditionalFeatureList(name='Party Feature', type='party_feature')
        fl.save()
        afl = PartyAdditionalFeatureList.create(self.party, fl.id)
        response = self.client.post(
            reverse('del_item', args=[afl.id, 'party_additional_feature']),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_del_item_et_custom_spell(self):
        """Test deleting a custom spell via AJAX."""
        cs = CustomSpell.create(self.template.id, 'folk')
        response = self.client.post(
            reverse('del_item', args=[cs.id, 'et_custom_spell']),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_del_item_et_nonrandom_feature(self):
        """Test deleting a nonrandom feature via AJAX."""
        fl = AdditionalFeatureList(name='Feature', type='enemy_feature')
        fl.save()
        item = AdditionalFeatureItem(name='Item', feature_list=fl)
        item.save()
        nrf = EnemyNonrandomFeature.create(self.template, item.id)
        response = self.client.post(
            reverse('del_item', args=[nrf.id, 'et_nonrandom_feature']),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_del_item_party_nonrandom_feature(self):
        """Test deleting a party nonrandom feature via AJAX."""
        fl = AdditionalFeatureList(name='Feature', type='party_feature')
        fl.save()
        item = AdditionalFeatureItem(name='Item', feature_list=fl)
        item.save()
        nrf = PartyNonrandomFeature.create(self.party, item.id)
        response = self.client.post(
            reverse('del_item', args=[nrf.id, 'party_nonrandom_feature']),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_get_feature_list_items(self):
        """Test getting feature list items via AJAX."""
        fl = AdditionalFeatureList(name='Feature List', type='enemy_feature')
        fl.save()
        item = AdditionalFeatureItem(name='Item 1', feature_list=fl)
        item.save()
        response = self.client.get(
            reverse('get_feature_list_items', args=[fl.id])
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('data', data)
        self.assertEqual(len(data['data']), 1)

    def test_submit_et_name(self):
        """Test submitting enemy template name via AJAX."""
        response = self.client.post(
            reverse('submit', args=[self.template.id]),
            data=json.dumps({
                'value': 'New Name',
                'object': 'et_name'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_rank(self):
        """Test submitting enemy template rank via AJAX."""
        response = self.client.post(
            reverse('submit', args=[self.template.id]),
            data=json.dumps({
                'value': '5',
                'object': 'et_rank'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_published(self):
        """Test submitting enemy template published status via AJAX."""
        response = self.client.post(
            reverse('submit', args=[self.template.id]),
            data=json.dumps({
                'value': 'true',
                'object': 'et_published'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_movement(self):
        """Test submitting enemy template movement via AJAX."""
        response = self.client.post(
            reverse('submit', args=[self.template.id]),
            data=json.dumps({
                'value': '8',
                'object': 'et_movement'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_natural_armor(self):
        """Test submitting natural armor via AJAX."""
        response = self.client.post(
            reverse('submit', args=[self.template.id]),
            data=json.dumps({
                'value': 'true',
                'object': 'et_natural_armor'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_folk_spell_amount(self):
        """Test submitting folk spell amount via AJAX."""
        response = self.client.post(
            reverse('submit', args=[self.template.id]),
            data=json.dumps({
                'value': '1d4',
                'object': 'et_folk_spell_amount'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_spirit_amount(self):
        """Test submitting spirit amount via AJAX."""
        response = self.client.post(
            reverse('submit', args=[self.template.id]),
            data=json.dumps({
                'value': '1d3',
                'object': 'et_spirit_amount'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_cult_amount(self):
        """Test submitting cult amount via AJAX."""
        response = self.client.post(
            reverse('submit', args=[self.template.id]),
            data=json.dumps({
                'value': '1',
                'object': 'et_cult_amount'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_cult_rank(self):
        """Test submitting cult rank via AJAX."""
        response = self.client.post(
            reverse('submit', args=[self.template.id]),
            data=json.dumps({
                'value': '2',
                'object': 'et_cult_rank'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_stat_value(self):
        """Test submitting stat value via AJAX."""
        stat = self.template.stats.first()
        response = self.client.post(
            reverse('submit', args=[stat.id]),
            data=json.dumps({
                'value': '2d6+6',
                'object': 'et_stat_value'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_stat_value_invalid(self):
        """Test submitting invalid stat value returns error."""
        stat = self.template.stats.first()
        response = self.client.post(
            reverse('submit', args=[stat.id]),
            data=json.dumps({
                'value': 'invalid',
                'object': 'et_stat_value'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])

    def test_submit_et_skill_value(self):
        """Test submitting skill value via AJAX."""
        skill = self.template.raw_skills.first()
        response = self.client.post(
            reverse('submit', args=[skill.id]),
            data=json.dumps({
                'value': 'STR+20',
                'object': 'et_skill_value'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_skill_include(self):
        """Test submitting skill include status via AJAX."""
        skill = self.template.raw_skills.first()
        response = self.client.post(
            reverse('submit', args=[skill.id]),
            data=json.dumps({
                'value': 'false',
                'object': 'et_skill_include'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_custom_skill_value(self):
        """Test submitting custom skill value via AJAX."""
        cs = CustomSkill.create(self.template.id)
        response = self.client.post(
            reverse('submit', args=[cs.id]),
            data=json.dumps({
                'value': 'DEX+10',
                'object': 'et_custom_skill_value'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_custom_skill_name(self):
        """Test submitting custom skill name via AJAX."""
        cs = CustomSkill.create(self.template.id)
        response = self.client.post(
            reverse('submit', args=[cs.id]),
            data=json.dumps({
                'value': 'My Custom Skill',
                'object': 'et_custom_skill_name'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_custom_spell_name(self):
        """Test submitting custom spell name via AJAX."""
        cs = CustomSpell.create(self.template.id, 'folk')
        response = self.client.post(
            reverse('submit', args=[cs.id]),
            data=json.dumps({
                'value': 'My Custom Spell',
                'object': 'et_custom_spell_name'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_custom_spell_prob(self):
        """Test submitting custom spell probability via AJAX."""
        cs = CustomSpell.create(self.template.id, 'folk')
        response = self.client.post(
            reverse('submit', args=[cs.id]),
            data=json.dumps({
                'value': '50',
                'object': 'et_custom_spell_prob'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_combat_style_name(self):
        """Test submitting combat style name via AJAX."""
        cs = self.template.combat_styles.first()
        response = self.client.post(
            reverse('submit', args=[cs.id]),
            data=json.dumps({
                'value': 'My Combat Style',
                'object': 'et_combat_style_name'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_combat_style_value(self):
        """Test submitting combat style value via AJAX."""
        cs = self.template.combat_styles.first()
        response = self.client.post(
            reverse('submit', args=[cs.id]),
            data=json.dumps({
                'value': 'STR+DEX+10',
                'object': 'et_combat_style_value'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_one_h_amount(self):
        """Test submitting one-handed weapon amount via AJAX."""
        cs = self.template.combat_styles.first()
        response = self.client.post(
            reverse('submit', args=[cs.id]),
            data=json.dumps({
                'value': '1d4',
                'object': 'et_one_h_amount'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_two_h_amount(self):
        """Test submitting two-handed weapon amount via AJAX."""
        cs = self.template.combat_styles.first()
        response = self.client.post(
            reverse('submit', args=[cs.id]),
            data=json.dumps({
                'value': '1d3',
                'object': 'et_two_h_amount'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_ranged_amount(self):
        """Test submitting ranged weapon amount via AJAX."""
        cs = self.template.combat_styles.first()
        response = self.client.post(
            reverse('submit', args=[cs.id]),
            data=json.dumps({
                'value': '1d2',
                'object': 'et_ranged_amount'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_submit_et_shield_amount(self):
        """Test submitting shield amount via AJAX."""
        cs = self.template.combat_styles.first()
        response = self.client.post(
            reverse('submit', args=[cs.id]),
            data=json.dumps({
                'value': '1',
                'object': 'et_shield_amount'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_add_additional_feature(self):
        """Test adding additional feature to enemy template via AJAX."""
        fl = AdditionalFeatureList(name='Feature', type='enemy_feature')
        fl.save()
        response = self.client.post(
            reverse('add_additional_feature', args=[self.template.id]),
            data=json.dumps({
                'feature_list_id': fl.id,
                'type': 'et'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_add_additional_feature_to_party(self):
        """Test adding additional feature to party via AJAX."""
        fl = AdditionalFeatureList(name='Party Feature', type='party_feature')
        fl.save()
        response = self.client.post(
            reverse('add_additional_feature', args=[self.party.id]),
            data=json.dumps({
                'feature_list_id': fl.id,
                'type': 'party'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_apply_notes_to_templates(self):
        """Test applying notes to templates via AJAX."""
        response = self.client.post(
            reverse('apply_notes_to_templates', args=[self.race.id]),
            data=json.dumps({'notes': 'Test note'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_ajax_requires_login(self):
        """Test that AJAX endpoints require login."""
        self.client.logout()
        response = self.client.post(
            reverse('add_custom_spell', args=[self.template.id, 'folk']),
            content_type='application/json'
        )
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)  # Redirects to login


class TestAjax(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.override = override_settings(TEMP=self.temp_dir.name)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        self.temp_dir.cleanup()

    def test_change_template_updates_generated_html(self):
        html_path = os.path.join(settings.TEMP, 'generated.html')
        with open(html_path, 'w') as ff:
            ff.write('<span id="enemy_name" class="editable name">Old</span>')

        request = self.factory.post('/rest/change_template/', {
            'html_file': 'generated.html',
            'id': 'enemy_name',
            'value': '<New Name>',
        }, content_type='application/json')

        response = change_template(request)

        self.assertEqual(response.status_code, 200)
        with open(html_path, 'r') as ff:
            html = ff.read()
        self.assertIn('&lt;New Name&gt;', html)
        self.assertIn('class="editable name"', html)

    def test_change_template_rejects_path_traversal(self):
        request = self.factory.post('/rest/change_template/', {
            'html_file': '../generated.html',
            'id': 'enemy_name',
            'value': 'New Name',
        }, content_type='application/json')

        response = change_template(request)

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data.get('success', True))  # Returns error

    def test_change_template_returns_error_when_span_missing(self):
        html_path = os.path.join(settings.TEMP, 'generated.html')
        with open(html_path, 'w') as ff:
            ff.write('<span id="enemy_name">Old</span>')
        request = self.factory.post('/rest/change_template/', {
            'html_file': 'generated.html',
            'id': 'missing',
            'value': 'New Name',
        }, content_type='application/json')

        response = change_template(request)

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertFalse(data.get('success', True))  # Returns error




class AjaxSubmitCoverageTest(TestCase):
    """Cover the submit() branches in ajax.py using parameterized tests."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user, _ = User.objects.get_or_create(username='test_15', defaults={'password': 'password'})
        if not self.user.check_password('password'):
            self.user.set_password('password')
            self.user.save()
        self.client = Client()
        self.client.login(username='test_15', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Ajax Submit Test')
        self.template.published = True
        self.template.save()
        self.party = Party.create(self.user)
        self.party.add(self.template)

    def _post_submit(self, obj_id, value, obj_type, parent_id=None):
        """Helper: POST to submit endpoint and return (response, data)."""
        payload = {'value': value, 'object': obj_type}
        if parent_id is not None:
            payload['parent_id'] = parent_id
        response = self.client.post(
            reverse('submit', args=[obj_id]),
            data=json.dumps(payload),
            content_type='application/json',
        )
        return response, json.loads(response.content)

    # --- Weapon probability ---

    def test_submit_et_weapon_prob(self):
        """Test submitting weapon probability (valid and invalid)."""
        cs = self.template.combat_styles.first()
        weapon = Weapon.objects.first()
        if not (weapon and cs):
            self.skipTest("No weapon or combat style available")
        with self.subTest('valid weapon probability'):
            resp, data = self._post_submit(weapon.id, '50', 'et_weapon_prob', cs.id)
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
        with self.subTest('invalid weapon probability'):
            resp, data = self._post_submit(weapon.id, 'invalid', 'et_weapon_prob', cs.id)
            self.assertEqual(resp.status_code, 200)
            self.assertFalse(data['success'])

    # --- Custom weapon fields (parameterized) ---

    def test_submit_et_custom_weapon_fields(self):
        """Test all custom weapon fields via parameterized subTests."""
        cs = self.template.combat_styles.first()
        # Valid field submissions with data verification
        fields = [
            ('et_custom_weapon_damage', '1d6', 'damage', '1d6'),
            ('et_custom_weapon_ap', '2', 'ap', 2),
            ('et_custom_weapon_hp', '5', 'hp', 5),
            ('et_custom_weapon_size', 'S', 'size', 'S'),
            ('et_custom_weapon_reach', '1', 'reach', '1'),
            ('et_custom_weapon_range', '100/200/300', 'range', '100/200/300'),
            ('et_custom_weapon_type', '1h-melee', 'type', '1h-melee'),
            ('et_custom_weapon_damage_modifier', 'true', 'damage_modifier', True),
            ('et_custom_weapon_natural_weapon', 'true', 'natural_weapon', True),
            ('et_custom_weapon_ap_hp_as_per', 'S', 'ap_hp_as_per', 'S'),
            ('et_custom_weapon_special_effects', 'Special effect text', 'special_effects', 'Special effect text'),
        ]
        for obj_type, value, attr, expected in fields:
            with self.subTest(field=obj_type):
                cw = CustomWeapon.create(cs.id, '1h-melee', 'Test Weapon', 10)
                resp, data = self._post_submit(cw.id, value, obj_type)
                self.assertEqual(resp.status_code, 200)
                self.assertTrue(data['success'])
                cw.refresh_from_db()
                self.assertEqual(getattr(cw, attr), expected)

    def test_submit_et_custom_weapon_invalid(self):
        """Test invalid custom weapon AP and HP submissions."""
        cs = self.template.combat_styles.first()
        for obj_type in ['et_custom_weapon_ap', 'et_custom_weapon_hp']:
            with self.subTest(field=obj_type):
                cw = CustomWeapon.create(cs.id, '1h-melee', 'Test Weapon', 10)
                resp, data = self._post_submit(cw.id, 'invalid', obj_type)
                self.assertEqual(resp.status_code, 200)
                self.assertFalse(data['success'])

    # --- Race fields (parameterized) ---

    def test_submit_race_fields(self):
        """Test all race fields via parameterized subTests."""
        fields = [
            ('race_name', 'New Race Name', 'name', 'New Race Name'),
            ('race_movement', '9', 'movement', '9'),
            ('race_notes', 'Race notes', 'special', 'Race notes'),
            ('race_discorporate', 'true', 'discorporate', True),
        ]
        for obj_type, value, attr, expected in fields:
            with self.subTest(field=obj_type):
                resp, data = self._post_submit(self.race.id, value, obj_type)
                self.assertEqual(resp.status_code, 200)
                self.assertTrue(data['success'])
                self.race.refresh_from_db()
                self.assertEqual(getattr(self.race, attr), expected)

    def test_submit_race_stat_value(self):
        """Test race stat value (valid and invalid)."""
        rs = self.race.stats.first()
        if not rs:
            self.skipTest("No race stats available")
        with self.subTest('valid stat value'):
            resp, data = self._post_submit(rs.id, '2d6+6', 'race_stat_value')
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
            rs.refresh_from_db()
            self.assertEqual(rs.default_value, '2d6+6')
        with self.subTest('invalid stat value'):
            resp, data = self._post_submit(rs.id, 'invalid', 'race_stat_value')
            self.assertEqual(resp.status_code, 200)
            self.assertFalse(data['success'])

    def test_submit_race_hl_fields(self):
        """Test all hit location fields via parameterized subTests."""
        hl = HitLocation.objects.filter(race=self.race).first()
        if not hl:
            self.skipTest("No hit locations available")
        # Valid fields
        fields = [
            ('race_hl_name', 'Head', 'name', 'Head'),
            ('race_hl_range_start', '1', 'range_start', 1),
            ('race_hl_range_end', '10', 'range_end', 10),
            ('race_hl_hp_modifier', '1d4', 'hp_modifier', '1d4'),
            ('race_hl_armor', '2', 'armor', '2'),
        ]
        for obj_type, value, attr, expected in fields:
            with self.subTest(field=obj_type):
                resp, data = self._post_submit(hl.id, value, obj_type)
                self.assertEqual(resp.status_code, 200)
                self.assertTrue(data['success'])
                hl.refresh_from_db()
                self.assertEqual(getattr(hl, attr), expected)
        # Invalid fields
        for obj_type in ['race_hl_range_start', 'race_hl_range_end', 'race_hl_hp_modifier']:
            with self.subTest(field=obj_type + '_invalid'):
                resp, data = self._post_submit(hl.id, 'invalid', obj_type)
                self.assertEqual(resp.status_code, 200)
                self.assertFalse(data['success'])

    # --- Party fields (parameterized) ---

    def test_submit_party_fields(self):
        """Test party name, notes, and tags."""
        with self.subTest('party name'):
            resp, data = self._post_submit(self.party.id, 'New Party Name', 'party_name')
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
            self.party.refresh_from_db()
            self.assertEqual(self.party.name, 'New Party Name')
        with self.subTest('party notes'):
            resp, data = self._post_submit(self.party.id, 'Party notes', 'party_notes')
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
            self.party.refresh_from_db()
            self.assertEqual(self.party.notes, 'Party notes')
        with self.subTest('party newtag'):
            resp, data = self._post_submit(self.party.id, 'tag1,tag2', 'party_newtag')
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
            self.party.refresh_from_db()
            self.assertIn('Tag1', self.party.get_tags())
            self.assertIn('Tag2', self.party.get_tags())
        with self.subTest('party deltag'):
            self.party.tags.add('Testtag')
            resp, data = self._post_submit(self.party.id, 'testtag', 'party_deltag')
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
        with self.subTest('party template amount'):
            resp, data = self._post_submit(self.template.id, '1d4', 'party_template_amount', self.party.id)
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
            ttp = TemplateToParty.objects.get(party=self.party, template=self.template)
            self.assertEqual(ttp.amount, '1d4')

    # --- ET tags and notes (parameterized) ---

    def test_submit_et_tags_and_notes(self):
        """Test enemy template notes and tags."""
        with self.subTest('et notes'):
            resp, data = self._post_submit(self.template.id, 'Template notes', 'et_notes')
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
            self.template.refresh_from_db()
            self.assertEqual(self.template.notes, 'Template notes')
        with self.subTest('et newtag'):
            resp, data = self._post_submit(self.template.id, 'tag1,tag2', 'et_newtag')
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
            self.template.refresh_from_db()
            self.assertIn('Tag1', self.template.get_tags())
            self.assertIn('Tag2', self.template.get_tags())
        with self.subTest('et deltag'):
            self.template.tags.add('Testtag')
            resp, data = self._post_submit(self.template.id, 'testtag', 'et_deltag')
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
            self.template.refresh_from_db()
            self.assertNotIn('Testtag', self.template.get_tags())

    # --- Feature probability ---

    def test_submit_feature_prob(self):
        """Test enemy and party feature probability."""
        with self.subTest('enemy feature prob'):
            fl = AdditionalFeatureList(name='Feature', type='enemy_feature')
            fl.save()
            afl = EnemyAdditionalFeatureList.create(self.template, fl.id)
            resp, data = self._post_submit(afl.id, '50', 'et_feature_prob')
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
            afl.refresh_from_db()
            self.assertEqual(afl.probability, '50')
        with self.subTest('party feature prob'):
            fl = AdditionalFeatureList(name='Party Feature', type='party_feature')
            fl.save()
            afl = PartyAdditionalFeatureList.create(self.party, fl.id)
            resp, data = self._post_submit(afl.id, '50', 'party_feature_prob')
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
            afl.refresh_from_db()
            self.assertEqual(afl.probability, '50')

    # --- Spirit and cult probability ---

    def test_submit_spirit_cult_prob(self):
        """Test spirit and cult probability (valid and invalid)."""
        spirit_template = EnemyTemplate.objects.filter(
            race__discorporate=True, published=True
        ).first()
        if spirit_template:
            with self.subTest('spirit prob valid'):
                es = EnemySpirit.create(spirit_template.id, self.template.id)
                resp, data = self._post_submit(es.id, '50', 'et_spirit_prob')
                self.assertEqual(resp.status_code, 200)
                self.assertTrue(data['success'])
                es.refresh_from_db()
                self.assertEqual(es.probability, 50)
            with self.subTest('spirit prob invalid'):
                es = EnemySpirit.create(spirit_template.id, self.template.id)
                resp, data = self._post_submit(es.id, 'invalid', 'et_spirit_prob')
                self.assertEqual(resp.status_code, 200)
                self.assertFalse(data['success'])
        cult_template = EnemyTemplate.objects.filter(
            race__name='Cult', published=True
        ).first()
        if cult_template:
            with self.subTest('cult prob valid'):
                ec = EnemyCult.create(cult_template.id, self.template.id)
                resp, data = self._post_submit(ec.id, '50', 'et_cult_prob')
                self.assertEqual(resp.status_code, 200)
                self.assertTrue(data['success'])
                ec.refresh_from_db()
                self.assertEqual(ec.probability, 50)
            with self.subTest('cult prob invalid'):
                ec = EnemyCult.create(cult_template.id, self.template.id)
                resp, data = self._post_submit(ec.id, 'invalid', 'et_cult_prob')
                self.assertEqual(resp.status_code, 200)
                self.assertFalse(data['success'])

    # --- Spell fields ---

    def test_submit_spell_fields(self):
        """Test spell probability and detail."""
        sa = SpellAbstract.objects.first()
        if not sa:
            self.skipTest("No spells available")
        with self.subTest('spell prob valid'):
            resp, data = self._post_submit(sa.id, '50', 'et_spell_prob', self.template.id)
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
            es = EnemySpell.objects.get(spell=sa, enemy_template=self.template)
            self.assertEqual(es.probability, 50)
        with self.subTest('spell prob invalid'):
            resp, data = self._post_submit(sa.id, 'invalid', 'et_spell_prob', self.template.id)
            self.assertEqual(resp.status_code, 200)
            self.assertFalse(data['success'])
        with self.subTest('spell detail'):
            resp, data = self._post_submit(sa.id, 'Spell detail text', 'et_spell_detail', self.template.id)
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
            es = EnemySpell.objects.get(spell=sa, enemy_template=self.template)
            self.assertEqual(es.detail, 'Spell detail text')

    def test_submit_spell_amounts(self):
        """Test theism, sorcery, and mysticism spell amounts."""
        spell_amounts = [
            ('et_theism_spell_amount', 'theism_spell_amount'),
            ('et_sorcery_spell_amount', 'sorcery_spell_amount'),
            ('et_mysticism_spell_amount', 'mysticism_spell_amount'),
        ]
        for obj_type, attr in spell_amounts:
            with self.subTest(field=obj_type):
                resp, data = self._post_submit(self.template.id, '1d3', obj_type)
                self.assertEqual(resp.status_code, 200)
                self.assertTrue(data['success'])
                self.template.refresh_from_db()
                self.assertEqual(getattr(self.template, attr), '1d3')

    # --- ET namelist ---

    def test_submit_et_namelist(self):
        """Test submitting enemy template namelist."""
        fl = AdditionalFeatureList(name='Name List', type='name')
        fl.save()
        resp, data = self._post_submit(self.template.id, str(fl.id), 'et_namelist')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data['success'])
        self.template.refresh_from_db()
        self.assertEqual(self.template.namelist, fl)

    # --- Invalid value submissions ---

    def test_submit_invalid_values(self):
        """Test various invalid value submissions."""
        with self.subTest('skill value invalid'):
            skill = self.template.raw_skills.first()
            if skill:
                resp, data = self._post_submit(skill.id, 'invalid', 'et_skill_value')
                self.assertEqual(resp.status_code, 200)
                self.assertFalse(data['success'])
        with self.subTest('custom skill value invalid'):
            cs = CustomSkill.create(self.template.id)
            resp, data = self._post_submit(cs.id, 'invalid', 'et_custom_skill_value')
            self.assertEqual(resp.status_code, 200)
            self.assertFalse(data['success'])
        with self.subTest('custom spell prob invalid'):
            cs = CustomSpell.create(self.template.id, 'folk')
            resp, data = self._post_submit(cs.id, 'invalid', 'et_custom_spell_prob')
            self.assertEqual(resp.status_code, 200)
            self.assertFalse(data['success'])
        with self.subTest('combat style value invalid'):
            cs = self.template.combat_styles.first()
            resp, data = self._post_submit(cs.id, 'invalid', 'et_combat_style_value')
            self.assertEqual(resp.status_code, 200)
            self.assertFalse(data['success'])

    # --- Custom skill include ---

    def test_submit_et_custom_skill_include(self):
        """Test submitting custom skill include."""
        cs = CustomSkill.create(self.template.id)
        resp, data = self._post_submit(cs.id, 'false', 'et_custom_skill_include')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data['success'])
        cs.refresh_from_db()
        self.assertTrue(cs.include)

    # --- HL armor ---

    def test_submit_et_hl_armor(self):
        """Test enemy hit location armor (valid and invalid)."""
        ehl = self.template.enemyhitlocation_set.first()
        if not ehl:
            self.skipTest("No enemy hit locations available")
        with self.subTest('valid HL armor'):
            resp, data = self._post_submit(ehl.id, '3', 'et_hl_armor')
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(data['success'])
            ehl.refresh_from_db()
            self.assertEqual(ehl.armor, '3')
        with self.subTest('invalid HL armor'):
            resp, data = self._post_submit(ehl.id, 'invalid', 'et_hl_armor')
            self.assertEqual(resp.status_code, 200)
            self.assertFalse(data['success'])

    # --- Non-login endpoints ---

    def test_toggle_star_ajax(self):
        """Test toggling star for authenticated and anonymous users."""
        with self.subTest('authenticated'):
            response = self.client.post(reverse('toggle_star', args=[self.template.id]))
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertTrue(self.template.is_starred(self.user))
        with self.subTest('anonymous'):
            self.client.logout()
            response = self.client.post(reverse('toggle_star', args=[self.template.id]))
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertFalse(data['success'])

    def test_get_weapons(self):
        """Test getting weapons list."""
        cs = self.template.combat_styles.first()
        if cs:
            response = self.client.get(reverse('get_weapons', args=[cs.id]), {'filter': 'melee'})
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertIn('weapons', data)




class AjaxErrorMessageTest(TestCase):
    """Verify that AJAX endpoints return meaningful error messages.
    
    Uses self-created objects rather than fixture data to avoid fragility.
    """
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='error_msg_user', password='password')
        self.factory = RequestFactory()
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Error Message Test')
        self.template.published = True
        self.template.save()
        self.cs = CombatStyle(name='Test CS', enemy_template=self.template)
        self.cs.save()

    def _post_submit(self, obj_id, value, obj_type, parent_id=None):
        """Helper: POST to submit endpoint and return parsed JSON."""
        payload = {'value': value, 'object': obj_type}
        if parent_id is not None:
            payload['parent_id'] = parent_id
        request = self.factory.post(
            reverse('submit', args=[obj_id]),
            data=json.dumps(payload),
            content_type='application/json',
        )
        request.user = self.user
        from ..ajax import submit
        response = submit(request, str(obj_id))
        return json.loads(response.content)

    def test_invalid_combat_style_value_message(self):
        """Invalid combat style value returns descriptive error message."""
        data = self._post_submit(self.cs.id, 'abc', 'et_combat_style_value')
        self.assertFalse(data['success'])
        self.assertIn('number', data['message'].lower())

    def test_invalid_probability_message(self):
        """Invalid feature probability returns descriptive error message."""
        afl = EnemyAdditionalFeatureList.create(self.template, 1)
        data = self._post_submit(afl.id, 'abc', 'et_feature_prob')
        self.assertFalse(data['success'])
        self.assertIn('message', data)  # Has error message

    def test_invalid_custom_weapon_ap_message(self):
        """Invalid custom weapon AP returns error message."""
        cw = CustomWeapon.create(self.cs.id, '1h-melee', 'Test', 10)
        data = self._post_submit(cw.id, 'abc', 'et_custom_weapon_ap')
        self.assertFalse(data['success'])
        self.assertIn('number', data['message'].lower())

    def test_invalid_custom_weapon_hp_message(self):
        """Invalid custom weapon HP returns error message."""
        cw = CustomWeapon.create(self.cs.id, '1h-melee', 'Test', 10)
        data = self._post_submit(cw.id, 'abc', 'et_custom_weapon_hp')
        self.assertFalse(data['success'])
        self.assertIn('number', data['message'].lower())

    def test_invalid_custom_weapon_prob_message(self):
        """Invalid custom weapon probability returns error message."""
        cw = CustomWeapon.create(self.cs.id, '1h-melee', 'Test', 10)
        data = self._post_submit(cw.id, 'abc', 'et_custom_weapon_prob')
        self.assertFalse(data['success'])
        self.assertIn('number', data['message'].lower())

    def test_invalid_custom_spell_prob_message(self):
        """Invalid custom spell probability returns error message."""
        spell = CustomSpell.create(self.template.id, 'folk')
        data = self._post_submit(spell.id, 'abc', 'et_custom_spell_prob')
        self.assertFalse(data['success'])
        self.assertIn('number', data['message'].lower())

    def test_invalid_spirit_prob_message(self):
        """Invalid spirit probability returns error message."""
        spirit = EnemyTemplate.objects.filter(race__name='Spirit', published=True).first()
        if not spirit:
            self.skipTest("No spirit templates available")
        from ..models import EnemySpirit
        es = EnemySpirit.create(spirit.id, self.template.id)
        data = self._post_submit(es.id, 'abc', 'et_spirit_prob')
        self.assertFalse(data['success'])
        self.assertIn('number', data['message'].lower())

    def test_invalid_cult_prob_message(self):
        """Invalid cult probability returns error message."""
        cult = EnemyTemplate.objects.filter(race__name='Cult', published=True).first()
        if not cult:
            self.skipTest("No cult templates available")
        from ..models import EnemyCult
        ec = EnemyCult.create(cult.id, self.template.id)
        data = self._post_submit(ec.id, 'abc', 'et_cult_prob')
        self.assertFalse(data['success'])
        self.assertIn('number', data['message'].lower())

    def test_movement_accepts_any_string(self):
        """Movement field accepts any string value."""
        data = self._post_submit(self.template.id, 'abc', 'et_movement')
        self.assertTrue(data['success'])
        self.template.refresh_from_db()
        self.assertEqual(self.template.movement, 'abc')  # Value was saved

    def test_submit_returns_json_structure(self):
        """Submit endpoint always returns success, message, value, original_value."""
        data = self._post_submit(self.template.id, 'Test Name', 'et_name')
        self.assertIn('success', data)
        self.assertIn('message', data)
        self.assertIn('value', data)
        self.assertIn('original_value', data)

    def test_submit_invalid_object_type(self):
        """Submit with unknown object type returns success without error."""
        data = self._post_submit(self.template.id, 'value', 'unknown_object_type')
        # Unknown object types are silently ignored (success=True, no change)
        self.assertTrue(data['success'])
        self.assertIn('message', data)  # Has response message

    def test_invalid_hit_location_armor_message(self):
        """Invalid hit location armor returns error message."""
        # Race 1 has hit locations in the fixture
        hl = HitLocation.objects.filter(race_id=1).first()
        if not hl:
            self.skipTest("No hit locations for race 1")
        ehl = hl.enemyhitlocation_set.create(enemy_template=self.template)
        data = self._post_submit(ehl.id, 'abc', 'et_hl_armor')
        self.assertFalse(data['success'])
        self.assertIn('valid', data['message'].lower())

    def test_invalid_stat_value_message(self):
        """Invalid stat die value returns descriptive error message."""
        es = EnemyStat.objects.filter(enemy_template=self.template).first()
        if not es:
            self.skipTest("No stats for this template")
        data = self._post_submit(es.id, 'abc', 'et_stat_value')
        self.assertFalse(data['success'])
        self.assertIn('not a valid die value', data['message'])

    def test_invalid_skill_include_message(self):
        """Invalid skill include value is handled gracefully."""
        es = EnemySkill.objects.filter(enemy_template=self.template).first()
        if not es:
            self.skipTest("No skills for this template")
        data = self._post_submit(es.id, 'abc', 'et_skill_include')
        # to_bool('abc') returns False, so this succeeds
        self.assertTrue(data['success'])
        self.assertIn('message', data)  # Has response message

    def test_invalid_weapon_probability_message(self):
        """Invalid weapon probability returns error message."""
        # Need a weapon and combat style from the fixture
        weapon = Weapon.objects.first()
        if not weapon:
            self.skipTest("No weapons available")
        data = self._post_submit(weapon.id, 'abc', 'et_weapon_prob', self.cs.id)
        self.assertFalse(data['success'])
        self.assertIn('number', data['message'].lower())

    def _post_submit_as_user(self, user, obj_id, value, obj_type, parent_id=None):
        """Helper: POST to submit endpoint as a specific user."""
        payload = {'value': value, 'object': obj_type}
        if parent_id is not None:
            payload['parent_id'] = parent_id
        request = self.factory.post(
            reverse('submit', args=[obj_id]),
            data=json.dumps(payload),
            content_type='application/json',
        )
        request.user = user
        from ..ajax import submit
        response = submit(request, str(obj_id))
        return json.loads(response.content)

    def test_invalid_race_stat_value_message(self):
        """Invalid race stat die value returns descriptive error message."""
        # Race 1 (Human) is owned by test_15 in the fixture
        rs = RaceStat.objects.filter(race_id=1).first()
        if not rs:
            self.skipTest("No race stats for race 1")
        race_owner = User.objects.get(username='test_15')
        data = self._post_submit_as_user(race_owner, rs.id, 'abc', 'race_stat_value')
        self.assertFalse(data['success'])
        self.assertIn('not a valid die set', data['message'])

    def test_invalid_race_hl_range_start_message(self):
        """Invalid hit location range start returns error message."""
        hl = HitLocation.objects.filter(race_id=1).first()
        if not hl:
            self.skipTest("No hit locations for race 1")
        race_owner = User.objects.get(username='test_15')
        data = self._post_submit_as_user(race_owner, hl.id, 'abc', 'race_hl_range_start')
        self.assertFalse(data['success'])
        self.assertIn('number', data['message'].lower())

    def test_invalid_race_hl_range_end_message(self):
        """Invalid hit location range end returns error message."""
        hl = HitLocation.objects.filter(race_id=1).first()
        if not hl:
            self.skipTest("No hit locations for race 1")
        race_owner = User.objects.get(username='test_15')
        data = self._post_submit_as_user(race_owner, hl.id, 'abc', 'race_hl_range_end')
        self.assertFalse(data['success'])
        self.assertIn('number', data['message'].lower())

    def test_invalid_race_hl_hp_modifier_message(self):
        """Invalid hit location HP modifier returns error message."""
        hl = HitLocation.objects.filter(race_id=1).first()
        if not hl:
            self.skipTest("No hit locations for race 1")
        race_owner = User.objects.get(username='test_15')
        data = self._post_submit_as_user(race_owner, hl.id, 'abc', 'race_hl_hp_modifier')
        self.assertFalse(data['success'])
        self.assertIn('number', data['message'].lower())

    def test_invalid_race_hl_armor_message(self):
        """Invalid hit location armor returns error message."""
        hl = HitLocation.objects.filter(race_id=1).first()
        if not hl:
            self.skipTest("No hit locations for race 1")
        race_owner = User.objects.get(username='test_15')
        data = self._post_submit_as_user(race_owner, hl.id, 'abc', 'race_hl_armor')
        self.assertFalse(data['success'])
        self.assertIn('valid', data['message'].lower())




class AjaxErrorBranchTest(TestCase):
    """Test ajax.py error handling branches."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='ajax_error_user', password='password')
        self.other_user = User.objects.create_user(username='ajax_other_user', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Ajax Error Test')
        self.template.published = True
        self.template.save()
        self.client = Client()
        self.client.login(username='ajax_error_user', password='password')
        self.factory = RequestFactory()

    def test_add_spirit_empty_list(self):
        """add_spirit with empty spirit_ids list returns success."""
        spirit = EnemyTemplate.objects.filter(race__name='Spirit', published=True).first()
        if not spirit:
            self.skipTest("No spirit templates available")
        url = reverse('add_spirit', args=[self.template.id])
        response = self.client.post(url, data=json.dumps({'spirit_ids': []}), content_type='application/json')
        data = json.loads(response.content)
        self.assertTrue(data.get('success', False))

    def test_add_cult_empty_list(self):
        """add_cult with empty cult_ids list returns success False."""
        url = reverse('add_cult', args=[self.template.id])
        response = self.client.post(url, data=json.dumps({'cult_ids': []}), content_type='application/json')
        data = json.loads(response.content)
        self.assertFalse(data.get('success', True))

    def test_add_template_to_party_empty_list(self):
        """add_template_to_party with empty template_ids returns success False."""
        party = Party.create(self.user)
        party.published = True
        party.save()
        url = reverse('add_template_to_party', args=[party.id])
        response = self.client.post(url, data=json.dumps({'template_ids': []}), content_type='application/json')
        data = json.loads(response.content)
        self.assertFalse(data.get('success', True))

    def test_add_spirit_invalid_spirit_id(self):
        """add_spirit with invalid spirit ID returns error."""
        url = reverse('add_spirit', args=[self.template.id])
        response = self.client.post(url, data=json.dumps({'spirit_ids': [99999]}), content_type='application/json')
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_add_cult_invalid_cult_id(self):
        """add_cult with invalid cult ID returns error."""
        url = reverse('add_cult', args=[self.template.id])
        response = self.client.post(url, data=json.dumps({'cult_ids': [99999]}), content_type='application/json')
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_add_template_to_party_invalid_template(self):
        """add_template_to_party with invalid template ID raises DoesNotExist.
        
        The endpoint does not handle missing templates gracefully - it raises
        EnemyTemplate.DoesNotExist. This documents the current behavior.
        """
        party = Party.create(self.user)
        party.published = True
        party.save()
        from ..ajax import add_template_to_party
        request = self.factory.post(
            reverse('add_template_to_party', args=[party.id]),
            data=json.dumps({'template_ids': [99999]}),
            content_type='application/json',
        )
        request.user = self.user
        with self.assertRaises(EnemyTemplate.DoesNotExist):
            add_template_to_party(request, str(party.id))

    def test_add_additional_feature_wrong_permission(self):
        """add_additional_feature rejects templates owned by other users."""
        other_template = EnemyTemplate.create(self.other_user, self.ruleset, self.race, 'Other Template')
        other_template.published = True
        other_template.save()
        afl = AdditionalFeatureList.objects.first()
        if not afl:
            self.skipTest("No feature lists available")
        url = reverse('add_additional_feature', args=[other_template.id])
        response = self.client.post(url, data=json.dumps({'feature_list_id': afl.id, 'type': 'et'}), content_type='application/json')
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_ajax_endpoints_require_login(self):
        """All AJAX endpoints redirect to login when not authenticated."""
        self.client.logout()
        endpoints = [
            (reverse('add_custom_spell', args=[self.template.id, 'folk']), {}),
            (reverse('add_custom_skill', args=[self.template.id]), {}),
            (reverse('add_spirit', args=[self.template.id]), {'spirit_ids': []}),
            (reverse('add_cult', args=[self.template.id]), {'cult_ids': []}),
            (reverse('del_item', args=[self.template.id, 'et']), {'item_id': 1}),
            (reverse('submit', args=[self.template.id]), {'value': 'test', 'object': 'et_name'}),
        ]
        for url, data in endpoints:
            with self.subTest(url=url):
                response = self.client.post(url, data=json.dumps(data), content_type='application/json')
                self.assertEqual(response.status_code, 302, f'{url} should redirect to login')
                # Verify it redirects to login page
                self.assertIn('/login', response.url)




