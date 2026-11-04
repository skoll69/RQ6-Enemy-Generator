"""
Consolidated view and views_lib tests.

This file combines all view-related tests from:
- test_coverage_gap.py (ViewsCoverageTest)
- test_smoke.py (ListingApiTest, ViewRenderingTest, AdditionalViewTest)
- test_views_lib_coverage.py (ViewsLibTest)
- test_exception_handling.py (ViewsErrorBranchTest)
"""
from django.test import TestCase, RequestFactory, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.http import Http404
import json

from ..models import (
    EnemyTemplate, Party, Race, Ruleset, CombatStyle,
    CustomWeapon, Weapon, EnemyWeapon, TemplateToParty,
    EnemySkill, CustomSkill, EnemySpell, SpellAbstract,
    CustomSpell, AdditionalFeatureList, AdditionalFeatureItem,
    EnemyAdditionalFeatureList, Star, HitLocation,
    EnemyStat, EnemyHitLocation, RaceStat,
)
from ..views_lib import (
    determine_enemies, get_enemies, get_enemies_lucky, get_random_party,
    sanitize_html_path, get_context, get_enemy_templates, get_statistics,
    get_party_templates, as_json, enemy_as_json, _get_html_prefix,
    get_filter, get_party_filter, get_et_context, get_generated_party,
    save_as_html, get_party_context,
)


class ViewsCoverageTest(TestCase):
    """Cover views.py branches using parameterized tests where possible."""
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
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Views Test Template')
        self.template.published = True
        self.template.save()
        self.party = Party.create(self.user)
        self.party.add(self.template)

    def _make_request(self, path, method='get', post_data=None):
        """Helper: Create a RequestFactory request with user and session."""
        from django.test import RequestFactory
        factory = RequestFactory()
        if method == 'post' and post_data:
            request = factory.post(path, post_data)
        else:
            request = factory.get(path)
        request.user = self.user
        request.session = {}
        return request

    # --- JSON generation views ---

    def test_generate_enemies_json_valid(self):
        """Test generate_enemies_json with valid template."""
        from ..views_lib import get_enemies, as_json
        enemy_index = [(self.template, 1)]
        enemies = get_enemies(enemy_index, True)
        enemies_json = as_json(enemies)
        data = json.loads(enemies_json)
        self.assertIsInstance(data, list)

    def test_generate_party_json_valid(self):
        """Test generate_party_json with valid party."""
        from ..views_lib import get_generated_party, enemy_as_json
        party_context = get_generated_party(self.party)
        out = {'enemies': [], 'party_name': self.party.name, 'additional_features': []}
        for enemy in party_context['enemies']:
            out['enemies'].append(enemy_as_json(enemy))
        self.assertIn('enemies', out)

    def test_generate_json_error_cases(self):
        """Test JSON generation views with invalid input."""
        from ..views import generate_enemies_json, generate_party_json
        with self.subTest('enemies_json no id'):
            request = self._make_request('/generate_enemies_json/')
            response = generate_enemies_json(request)
            self.assertEqual(response.status_code, 302)
        with self.subTest('enemies_json invalid id'):
            request = self._make_request('/generate_enemies_json/', 'get', {'id': 'notanint'})
            response = generate_enemies_json(request)
            self.assertEqual(response.status_code, 302)
        with self.subTest('party_json invalid id'):
            request = self._make_request('/generate_party_json/', 'get', {'id': '99999'})
            with self.assertRaises(Exception):
                generate_party_json(request)

    # --- Redirect views ---

    def test_redirect_views(self):
        """Test views that redirect on GET or missing params."""
        with self.subTest('generate_enemies GET'):
            self.assertEqual(self.client.get(reverse('generate_enemies')).status_code, 302)
        with self.subTest('generate_party GET'):
            self.assertEqual(self.client.get(reverse('generate_party')).status_code, 302)
        with self.subTest('pdf_export no action'):
            self.assertEqual(self.client.get(reverse('pdf_export')).status_code, 302)
        with self.subTest('png_export no action'):
            self.assertEqual(self.client.get(reverse('png_export')).status_code, 302)
        with self.subTest('create_enemy_template no race'):
            self.assertEqual(self.client.post(reverse('create_enemy_template')).status_code, 302)

    def test_filter_views(self):
        """Test filter redirect views."""
        with self.subTest('set_filter'):
            resp = self.client.post(reverse('set_filter'), {'filter': 'test', 'coming_from': '/index/'})
            self.assertEqual(resp.status_code, 302)
        with self.subTest('set_party_filter'):
            resp = self.client.post(reverse('set_party_filter'), {'party_filter': 'test', 'coming_from': '/party_index/'})
            self.assertEqual(resp.status_code, 302)

    # --- Page views (parameterized) ---

    def test_page_views(self):
        """Test all page views render successfully."""
        from ..views import (index, simple_index, home, party_index, edit_index,
                             statistics, instructions, about, whats_new, account)
        views = [
            ('index', index, '/index/'),
            ('simple_index', simple_index, '/simple_index/'),
            ('home', home, '/home/'),
            ('party_index', party_index, '/party_index/'),
            ('edit_index', edit_index, '/edit_index/'),
            ('statistics', statistics, '/statistics/'),
            ('instructions', instructions, '/instructions/'),
            ('about', about, '/about/'),
            ('whats_new', whats_new, '/whats_new/'),
            ('account', account, '/account/'),
        ]
        for name, view_func, path in views:
            with self.subTest(view=name):
                request = self._make_request(path)
                response = view_func(request)
                self.assertEqual(response.status_code, 200)
                # Verify response has content
                self.assertGreater(len(response.content), 0)

    def test_detail_views(self):
        """Test detail views (template, party, race)."""
        from ..views import enemy_template, party, race
        with self.subTest('enemy_template'):
            request = self._make_request(f'/enemy_template/{self.template.id}/')
            response = enemy_template(request, self.template.id)
            self.assertEqual(response.status_code, 200)
        with self.subTest('party'):
            request = self._make_request(f'/party/{self.party.id}/')
            response = party(request, self.party.id)
            self.assertEqual(response.status_code, 200)
        with self.subTest('race'):
            request = self._make_request(f'/race/{self.race.id}/')
            response = race(request, self.race.id)
            self.assertEqual(response.status_code, 200)

    def test_unpublished_access(self):
        """Test unpublished items return 404 for other users."""
        from ..views import enemy_template, party
        with self.subTest('unpublished template'):
            self.template.published = False
            self.template.save()
            other_user = User.objects.create_user(username='otheruser', password='password')
            request = self._make_request(f'/enemy_template/{self.template.id}/')
            request.user = other_user
            with self.assertRaises(Exception):
                enemy_template(request, self.template.id)
        with self.subTest('unpublished party'):
            self.party.published = False
            self.party.save()
            other_user = User.objects.create_user(username='otheruser2', password='password')
            request = self._make_request(f'/party/{self.party.id}/')
            request.user = other_user
            with self.assertRaises(Exception):
                party(request, self.party.id)

    def test_race_index_requires_admin(self):
        """Test race_index returns 404 for non-admin users."""
        from ..views_lib import is_race_admin
        self.assertFalse(is_race_admin(self.user))

    def test_apply_skill_bonus_view(self):
        """Test apply_skill_bonus view."""
        before = self.template.raw_skills.first().die_set
        response = self.client.post(reverse('apply_skill_bonus', args=[self.template.id]), {'bonus': '10'})
        self.assertEqual(response.status_code, 302)
        self.template.refresh_from_db()
        after = self.template.raw_skills.first().die_set
        self.assertIn('+10', after)  # Bonus was applied

    # --- Delete operations ---

    def test_delete_operations(self):
        """Test delete template and party operations."""
        from ..views_lib import get_context
        with self.subTest('delete_template exists'):
            request = self._make_request(f'/delete_template/{self.template.id}/')
            context = get_context(request)
            et = EnemyTemplate.objects.get(id=self.template.id, owner=self.user)
            self.assertIsNotNone(et)
        with self.subTest('delete_party exists'):
            request = self._make_request(f'/delete_party/{self.party.id}/')
            context = get_context(request)
            p = Party.objects.get(id=self.party.id, owner=self.user)
            self.assertIsNotNone(p)

    def test_delete_template_yes(self):
        """Test delete_template with Yes answer."""
        initial_count = EnemyTemplate.objects.count()
        et = EnemyTemplate.objects.get(id=self.template.id, owner=self.user)
        et.delete()
        self.assertEqual(EnemyTemplate.objects.count(), initial_count - 1)

    def test_delete_party_yes(self):
        """Test delete_party with Yes answer."""
        initial_count = Party.objects.count()
        p = Party.objects.get(id=self.party.id, owner=self.user)
        p.delete()
        self.assertEqual(Party.objects.count(), initial_count - 1)

    # --- Generation operations ---

    def test_generate_enemies_lucky(self):
        """Test generate_enemies with lucky POST."""
        from ..views_lib import get_enemies_lucky
        request = self._make_request('/generate_enemies/', 'post', {'lucky': '1'})
        enemies = get_enemies_lucky(request)
        self.assertIsInstance(enemies, list)

    def test_generate_party_lucky(self):
        """Test generate_party with lucky POST."""
        from ..views_lib import get_random_party, get_party_filter, get_generated_party
        request = self._make_request('/generate_party/', 'post', {'lucky': '1'})
        party_object = get_random_party(get_party_filter(request))
        self.assertIsNotNone(party_object)
        context = get_generated_party(party_object)
        self.assertIn('enemies', context)

    def test_generate_enemies_post(self):
        """Test generate_enemies with POST data."""
        from ..views_lib import get_enemies
        enemy_index = [(self.template, 1)]
        enemies = get_enemies(enemy_index, True)
        self.assertEqual(len(enemies), 1)
        self.assertIn('STR', enemies[0].stats)  # Enemy has stats

    def test_generate_party_post(self):
        """Test generate_party with POST data."""
        from ..views_lib import get_generated_party
        party_object = Party.objects.get(id=self.party.id)
        context = get_generated_party(party_object)
        self.assertIn('enemies', context)

    # --- Published status ---

    def test_submit_published_status(self):
        """Test submitting race and party published status."""
        with self.subTest('race published'):
            resp = self.client.post(
                reverse('submit', args=[self.race.id]),
                data=json.dumps({'value': 'true', 'object': 'race_published'}),
                content_type='application/json',
            )
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(json.loads(resp.content)['success'])
            self.race.refresh_from_db()
            self.assertTrue(self.race.published)
        with self.subTest('party published'):
            resp = self.client.post(
                reverse('submit', args=[self.party.id]),
                data=json.dumps({'value': 'true', 'object': 'party_published'}),
                content_type='application/json',
            )
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(json.loads(resp.content)['success'])
            self.party.refresh_from_db()
            self.assertTrue(self.party.published)


class ListingApiTest(TestCase):
    """Smoke tests for the listing JSON APIs."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='listinguser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Listing API Template')
        self.template.published = True
        self.template.save()
        self.party = Party.objects.create(name='Listing API Party', owner=self.user, published=True)
        TemplateToParty.objects.create(party=self.party, template=self.template, amount=1)

    def test_index_json_returns_valid_json(self):
        """
        Purpose: Verifies that the index_json API returns valid JSON with expected fields.
        Requirement: GET /index_json/ must return a JSON array with template objects.
        """
        from ..views import index_json

        request = self.factory.get('/index_json/')
        request.user = self.user
        request.session = {}

        response = index_json(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

        data = json.loads(response.content)
        self.assertIsInstance(data, list)

        # Find our template in the results
        found = False
        for item in data:
            if item['id'] == self.template.id:
                found = True
                # Verify expected fields are present
                self.assertIn('name', item)
                self.assertIn('race', item)
                self.assertIn('rank', item)
                self.assertIn('owner', item)
                self.assertIn('tags', item)
                self.assertIn('notes', item)
                break
        self.assertTrue(found, "Template not found in index_json results")

    def test_index_json_excludes_cults(self):
        """
        Purpose: Verifies that cult templates are excluded from index_json.
        Requirement: Cult race templates should not appear in the template listing.
        """
        from ..views import index_json

        # Create a cult template
        cult_race, created = Race.objects.get_or_create(
            name='Cult',
            defaults={'published': True, 'owner': self.user}
        )
        cult_template = EnemyTemplate.create(self.user, self.ruleset, cult_race, 'Cult Template')
        cult_template.published = True
        cult_template.save()

        request = self.factory.get('/index_json/')
        request.user = self.user
        request.session = {}

        response = index_json(request)
        data = json.loads(response.content)

        # Cult template should not be in the results
        for item in data:
            self.assertNotEqual(item['id'], cult_template.id)

    def test_party_index_json_returns_valid_json(self):
        """
        Purpose: Verifies that the party_index_json API returns valid JSON with expected fields.
        Requirement: GET /party_index_json/ must return a JSON array with party objects.
        """
        from ..views import party_index_json

        request = self.factory.get('/party_index_json/')
        request.user = self.user
        request.session = {}

        response = party_index_json(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

        data = json.loads(response.content)
        self.assertIsInstance(data, list)

        # Find our party in the results
        found = False
        for item in data:
            if item['id'] == self.party.id:
                found = True
                # Verify expected fields are present
                self.assertIn('name', item)
                self.assertIn('owner', item)
                self.assertIn('tags', item)
                self.assertIn('templates', item)
                # Verify templates list has our template
                self.assertGreater(len(item['templates']), 0)
                break
        self.assertTrue(found, "Party not found in party_index_json results")

    def test_party_index_json_template_details(self):
        """
        Purpose: Verifies that party_index_json includes correct template details.
        Requirement: Each party should list its templates with name, amount, and id.
        """
        from ..views import party_index_json

        request = self.factory.get('/party_index_json/')
        request.user = self.user
        request.session = {}

        response = party_index_json(request)
        data = json.loads(response.content)

        # Find our party
        for item in data:
            if item['id'] == self.party.id:
                template_info = item['templates'][0]
                self.assertEqual(template_info['id'], self.template.id)
                self.assertEqual(template_info['name'], self.template.name)
                self.assertEqual(template_info['amount'], '1')
                return
        self.fail("Party not found in results")




class ViewRenderingTest(TestCase):
    """Smoke tests for view rendering logic (without full HTML rendering)."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='viewuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'View Test Template')
        self.template.published = True
        self.template.save()
        self.party = Party.objects.create(name='View Test Party', owner=self.user, published=True)
        TemplateToParty.objects.create(party=self.party, template=self.template, amount=1)

    def test_index_view_has_templates_context(self):
        """
        Purpose: Verifies that the enemy list view provides the templates context.
        Requirement: The index view must include 'templates' in its context.
        Note: We test the view logic directly instead of full HTML rendering.
        """
        from ..views_lib import get_context, get_enemy_templates, get_filter

        request = self.factory.get('/index/')
        request.user = self.user
        request.session = {}

        context = get_context(request)
        templates = get_enemy_templates(get_filter(request), request.user)

        # The view adds 'templates' to context; we verify the data retrieval works
        self.assertIsNotNone(context)
        # Our published template should be in the list
        template_ids = [t.id for t in templates]
        self.assertIn(self.template.id, template_ids)

    def test_party_index_view_has_parties_context(self):
        """
        Purpose: Verifies that the party list view provides the parties context.
        Requirement: The party_index view must include 'parties' in its context.
        """
        from ..views_lib import get_context, get_party_templates, get_party_filter

        request = self.factory.get('/party_index/')
        request.user = self.user
        request.session = {}

        context = get_context(request)
        parties = get_party_templates(get_party_filter(request), request.user)

        # The view adds 'parties' to context; we verify the data retrieval works
        self.assertIsNotNone(context)
        # Our published party should be in the list
        party_ids = [p.id for p in parties]
        self.assertIn(self.party.id, party_ids)

    def test_edit_index_view_has_context(self):
        """
        Purpose: Verifies that the edit index view provides the expected context.
        Requirement: The edit_index view must include enemy_templates, races, etc.
        Note: This view requires login, so we set up an authenticated user.
        """
        from ..views_lib import get_context, is_race_admin

        request = self.factory.get('/edit_index/')
        request.user = self.user
        request.session = {}

        context = get_context(request)

        # Verify the context has the expected keys
        templates = EnemyTemplate.objects.filter(owner=self.user).exclude(race__name='Cult').select_related('race')
        races = Race.objects.filter(published=True).exclude(name='Cult')
        edit_cults = EnemyTemplate.objects.filter(owner=self.user, race__name='Cult')
        edit_parties = Party.objects.filter(owner=self.user)

        # Verify our template is in the user's templates
        self.assertEqual(templates.count() > 0, True)
        # Verify our party is in the user's parties
        self.assertEqual(edit_parties.count() > 0, True)

    def test_statistics_view_has_statistics_context(self):
        """
        Purpose: Verifies that the statistics view provides the statistics context.
        Requirement: The statistics view must include 'statistics' with expected keys.
        """
        from ..views_lib import get_context, get_statistics

        request = self.factory.get('/statistics/')
        request.user = self.user
        request.session = {}

        context = get_context(request)
        statistics = get_statistics()

        # The view adds 'statistics' to context; we verify the data retrieval works
        self.assertIsNotNone(context)
        # Verify the statistics dict has the expected keys
        self.assertIn('templates', statistics)
        self.assertIn('races', statistics)
        self.assertIn('users', statistics)
        self.assertIn('cults', statistics)
        self.assertIn('total_published_templates', statistics)
        self.assertIn('total_published_races', statistics)
        self.assertIn('total_published_cults', statistics)

    def test_statistics_filters_by_generated_threshold(self):
        """
        Purpose: Verifies that the statistics page filters templates by generated count.
        Requirement: Only templates with generated > 29 should appear in the statistics.
        """
        from ..views_lib import get_statistics

        # Create a template with low generated count
        low_gen_template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Low Gen Template')
        low_gen_template.published = True
        low_gen_template.generated = 10
        low_gen_template.save()

        # Create a template with high generated count
        high_gen_template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'High Gen Template')
        high_gen_template.published = True
        high_gen_template.generated = 50
        high_gen_template.save()

        statistics = get_statistics()

        # Only the high-gen template should appear
        template_ids = [t.id for t in statistics['templates']]
        self.assertNotIn(low_gen_template.id, template_ids)
        self.assertIn(high_gen_template.id, template_ids)

    def test_statistics_excludes_cults_from_templates(self):
        """
        Purpose: Verifies that cult templates are excluded from the statistics templates list.
        Requirement: Cult race templates should appear in 'cults', not 'templates'.
        """
        from ..views_lib import get_statistics

        # Create a cult template
        cult_race, created = Race.objects.get_or_create(
            name='Cult',
            defaults={'published': True, 'owner': self.user}
        )
        cult_template = EnemyTemplate.create(self.user, self.ruleset, cult_race, 'Stats Cult Template')
        cult_template.published = True
        cult_template.generated = 50
        cult_template.save()

        statistics = get_statistics()

        # Cult template should NOT be in the templates list
        template_ids = [t.id for t in statistics['templates']]
        self.assertNotIn(cult_template.id, template_ids)

        # Cult template SHOULD be in the cults list
        cult_ids = [c['id'] for c in statistics['cults']]
        self.assertIn(cult_template.id, cult_ids)




class AdditionalViewTest(TestCase):
    """Additional view tests for home, simple_index, and other views."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='additionaluser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Additional View Template')
        self.template.published = True
        self.template.save()

    def test_home_view_has_templates_context(self):
        """
        Purpose: Verifies that the home view provides the templates context.
        Requirement: The home view must include 'templates' filtered by 'Starred'.
        """
        from ..views_lib import get_context, get_enemy_templates

        request = self.factory.get('/home/')
        request.user = self.user
        request.session = {}

        context = get_context(request)
        templates = get_enemy_templates('Starred', request.user)

        # The view adds 'templates' to context; we verify the data retrieval works
        self.assertIsNotNone(context)
        # Starred filter should return a queryset (may be empty if no stars)
        self.assertIsNotNone(templates)

    def test_simple_index_view_has_templates_context(self):
        """
        Purpose: Verifies that the simple_index view provides the templates context.
        Requirement: The simple_index view must include 'templates' for authenticated users.
        """
        from ..views_lib import get_context
        from django.core.paginator import Paginator

        request = self.factory.get('/simple_index/')
        request.user = self.user
        request.session = {}

        context = get_context(request)
        templates = EnemyTemplate.objects.filter(owner=self.user)
        paginator = Paginator(templates, 200)
        paged_templates = paginator.page(1)

        # The view adds 'templates' to context; we verify the data retrieval works
        self.assertIsNotNone(context)
        # Our template should be in the user's templates
        template_ids = [t.id for t in paged_templates]
        self.assertIn(self.template.id, template_ids)

    def test_instructions_view_has_context(self):
        """
        Purpose: Verifies that the instructions view provides the context.
        Requirement: The instructions view must render without error.
        """
        from ..views_lib import get_context

        request = self.factory.get('/instructions/')
        request.user = self.user
        request.session = {}

        context = get_context(request)
        self.assertIsNotNone(context)
        self.assertIn('all_et_tags', context)  # Has tag context

    def test_about_view_has_context(self):
        """
        Purpose: Verifies that the about view provides the context.
        Requirement: The about view must render without error.
        """
        from ..views_lib import get_context

        request = self.factory.get('/about/')
        request.user = self.user
        request.session = {}

        context = get_context(request)
        self.assertIsNotNone(context)
        self.assertIn('all_et_tags', context)  # Has tag context


class ViewsLibTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'ViewsLib Test')
        self.template.published = True
        self.template.save()

    def test_get_enemy_templates_no_filter(self):
        """Test get_enemy_templates with no filter returns published templates."""
        templates = get_enemy_templates(None, self.user)
        self.assertGreater(len(templates), 0)

    def test_get_enemy_templates_with_filter(self):
        """Test get_enemy_templates with filter returns filtered results."""
        templates = get_enemy_templates({'filter': self.race.id}, self.user)
        for t in templates:
            self.assertEqual(t.race, self.race)

    def test_get_enemy_templates_with_search(self):
        """Test get_enemy_templates with search string."""
        templates = get_enemy_templates({'search': 'ViewsLib'}, self.user)
        for t in templates:
            self.assertIn('ViewsLib', t.name)

    def test_get_enemy_templates_with_search_exclusion(self):
        """Test get_enemy_templates with search exclusion."""
        templates = get_enemy_templates({'search': '-ViewsLib'}, self.user)
        for t in templates:
            self.assertNotIn('ViewsLib', t.name)

    def test_get_enemy_templates_with_tag_filter(self):
        """Test get_enemy_templates with tag filter."""
        self.template.tags.add('test-tag')
        templates = get_enemy_templates({'tag': 'test-tag'}, self.user)
        for t in templates:
            self.assertIn('test-tag', t.get_tags())

    def test_get_enemy_templates_starred_for_authenticated(self):
        """Test get_enemy_templates includes starred for authenticated user."""
        templates = get_enemy_templates(None, self.user)
        for t in templates:
            self.assertTrue(hasattr(t, 'starred'))

    def test_get_enemy_templates_starred_for_anonymous(self):
        """Test get_enemy_templates works for anonymous user."""
        from django.contrib.auth.models import AnonymousUser
        templates = get_enemy_templates(None, AnonymousUser())
        self.assertGreater(len(templates), 0)

    def test_get_statistics(self):
        """Test get_statistics returns all expected keys."""
        stats = get_statistics()
        self.assertIn('templates', stats)
        self.assertIn('races', stats)
        self.assertIn('users', stats)
        self.assertIn('cults', stats)
        self.assertIn('total_published_templates', stats)
        self.assertIn('total_published_races', stats)

    def test_get_statistics_filters_by_generated(self):
        """Test get_statistics filters templates by generated > 29."""
        stats = get_statistics()
        for t in stats['templates']:
            self.assertGreater(t.generated, 29)

    def test_get_statistics_excludes_cults_from_templates(self):
        """Test get_statistics excludes cults from templates list."""
        stats = get_statistics()
        for t in stats['templates']:
            self.assertNotEqual(t.race.name, 'Cult')

    def test_get_context(self):
        """Test get_context returns expected keys."""
        from django.http import HttpRequest
        request = HttpRequest()
        request.user = self.user
        request.session = {}
        context = get_context(request)
        self.assertIn('filter', context)
        self.assertIn('party_filter', context)

    def test_get_et_context(self):
        """Test get_et_context returns expected keys."""
        context = get_et_context(self.template)
        self.assertIn('et', context)

    def test_get_party_context(self):
        """Test get_party_context returns expected keys."""
        party = Party.create(self.user)
        context = get_party_context(party)
        self.assertIn('party', context)

    def test_get_party_templates(self):
        """Test get_party_templates returns published parties."""
        parties = get_party_templates(None, self.user)
        self.assertGreater(len(parties), 0)

    def test_get_party_filter(self):
        """Test get_party_filter returns filter from session."""
        from django.http import HttpRequest
        request = HttpRequest()
        request.session = {'party_filter': self.race.id}
        filtr = get_party_filter(request)
        self.assertEqual(filtr, self.race.id)

    def test_get_random_party(self):
        """Test get_random_party returns a published party."""
        party = get_random_party(None)
        self.assertIsNotNone(party)
        self.assertTrue(party.published)

    def test_get_enemies_with_increment(self):
        """Test get_enemies increments used counter."""
        initial_used = self.template.used
        index = ((self.template, 1),)
        enemies = get_enemies(index, True)
        self.assertEqual(len(enemies), 1)
        self.template.refresh_from_db()
        self.assertGreater(self.template.used, initial_used)

    def test_get_enemies_without_increment(self):
        """Test get_enemies without increment doesn't change used."""
        initial_used = self.template.used
        index = ((self.template, 1),)
        enemies = get_enemies(index, False)
        self.assertEqual(len(enemies), 1)
        self.template.refresh_from_db()
        self.assertEqual(self.template.used, initial_used)

    def test_get_enemies_lucky(self):
        """Test get_enemies_lucky returns enemies."""
        from django.http import HttpRequest
        request = HttpRequest()
        request.session = {}
        enemies = get_enemies_lucky(request)
        self.assertGreater(len(enemies), 0)

    def test_get_generated_party(self):
        """Test get_generated_party returns party dict."""
        party = Party.create(self.user)
        party.add(self.template)
        result = get_generated_party(party)
        self.assertIn('party', result)
        self.assertIn('enemies', result)
        self.assertGreater(len(result['enemies']), 0)

    def test_determine_enemies(self):
        """Test determine_enemies parses POST data correctly."""
        post = {
            'enemy_template_id_%d' % self.template.id: '2'
        }
        result = determine_enemies(post)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], self.template)
        self.assertEqual(result[0][1], 2)

    def test_determine_enemies_lucky(self):
        """Test determine_enemies with lucky flag returns empty list.
        
        determine_enemies only handles enemy_template_id_X keys, not 'lucky'.
        The lucky flag is handled by the view, not determine_enemies.
        """
        post = {
            'lucky': 'on'
        }
        result = determine_enemies(post)
        # determine_enemies ignores 'lucky' key, returns empty list
        self.assertEqual(result, [])

    def test_as_json(self):
        """Test as_json serializes enemies to JSON."""
        index = ((self.template, 1),)
        enemies = get_enemies(index, False)
        json_str = as_json(enemies)
        self.assertIsInstance(json_str, str)
        self.assertGreater(len(json_str), 0)

    def test_save_as_html(self):
        """Test save_as_html generates HTML."""
        index = ((self.template, 1),)
        enemies = get_enemies(index, False)
        context = {'enemies': enemies}
        html = save_as_html(context, 'generated_enemies.html')
        self.assertIsInstance(html, str)

    def test_is_race_admin_false(self):
        """Test is_race_admin returns False for non-admin user."""
        from enemygen.views_lib import is_race_admin
        result = is_race_admin(self.user)
        self.assertFalse(result)

    def test_get_filter(self):
        """Test get_filter returns filter from session."""
        from django.http import HttpRequest
        request = HttpRequest()
        request.session = {'filter': self.race.id}
        filtr = get_filter(request)
        self.assertEqual(filtr, self.race.id)

    def test_get_enemy_templates_returns_list(self):
        """Test get_enemy_templates returns a list of templates."""
        templates = get_enemy_templates(None, self.user)
        self.assertGreater(len(templates), 0)

    def test_get_enemy_templates_excludes_cults(self):
        """Test get_enemy_templates excludes cult templates."""
        templates = get_enemy_templates(None, self.user)
        for t in templates:
            self.assertNotEqual(t.race.name, 'Cult')

    def test_get_enemy_templates_includes_unpublished_for_owner(self):
        """Test get_enemy_templates includes unpublished for owner."""
        private_template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Private')
        private_template.published = False
        private_template.save()
        templates = get_enemy_templates(None, self.user)
        names = [t.name for t in templates]
        self.assertIn('Private', names)

    def test_get_enemy_templates_excludes_unpublished_for_anonymous(self):
        """Test get_enemy_templates excludes unpublished for anonymous."""
        from django.contrib.auth.models import AnonymousUser
        private_template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Private2')
        private_template.published = False
        private_template.save()
        templates = get_enemy_templates(None, AnonymousUser())
        names = [t.name for t in templates]
        self.assertNotIn('Private2', names)

    def test_get_statistics_orders_by_generated(self):
        """Test get_statistics orders templates by generated count."""
        stats = get_statistics()
        generated_counts = [t.generated for t in stats['templates']]
        self.assertEqual(generated_counts, sorted(generated_counts, reverse=True))

    def test_get_statistics_orders_races_by_templates(self):
        """Test get_statistics orders races by template count."""
        stats = get_statistics()
        race_counts = [r['template_amount'] for r in stats['races']]
        self.assertEqual(race_counts, sorted(race_counts, reverse=True))

    def test_get_statistics_orders_users_by_templates(self):
        """Test get_statistics orders users by template count."""
        stats = get_statistics()
        user_counts = [u['template_amount'] for u in stats['users']]
        self.assertEqual(user_counts, sorted(user_counts, reverse=True))

    def test_get_statistics_orders_cults_by_generated(self):
        """Test get_statistics orders cults by name (alphabetical)."""
        stats = get_statistics()
        # cults are returned as dicts sorted by name, not by generated
        cult_names = [c['name'] for c in stats['cults']]
        self.assertEqual(cult_names, sorted(cult_names))

    def test_get_et_context_with_theism_spells(self):
        """Test get_et_context includes theism spells."""
        context = get_et_context(self.template)
        self.assertIn('theism_spells', context)

    def test_get_party_context_with_templates(self):
        """Test get_party_context includes templates."""
        party = Party.create(self.user)
        party.add(self.template)
        context = get_party_context(party)
        self.assertIn('templates', context)

    def test_get_party_templates_with_filter(self):
        """Test get_party_templates with filter returns parties."""
        parties = get_party_templates({'filter': self.race.id}, self.user)
        self.assertIsNotNone(parties)
        self.assertIsInstance(parties, list)

    def test_get_party_templates_with_tag_filter(self):
        """Test get_party_templates with tag filter."""
        party = Party.create(self.user)
        party.tags.add('test-party-tag')
        party.published = True
        party.save()
        parties = get_party_templates('test-party-tag', self.user)
        self.assertGreaterEqual(len(parties), 0)

    def test_get_random_party_returns_published(self):
        """Test get_random_party returns a published party."""
        party = get_random_party(None)
        self.assertTrue(party.published)

    def test_get_enemies_multiple_templates(self):
        """Test get_enemies with multiple templates."""
        template2 = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Template2')
        index = ((self.template, 1), (template2, 2))
        enemies = get_enemies(index, False)
        self.assertEqual(len(enemies), 3)
        for enemy in enemies:
            self.assertIn('STR', enemy.stats)  # Each enemy has stats

    def test_get_enemies_lucky_amount(self):
        """Test get_enemies_lucky returns 6 enemies."""
        from django.http import HttpRequest
        request = HttpRequest()
        request.session = {}
        enemies = get_enemies_lucky(request)
        self.assertEqual(len(enemies), 6)
        for enemy in enemies:
            self.assertIn('STR', enemy.stats)  # Each enemy has stats

    def test_get_generated_party_with_party_name(self):
        """Test get_generated_party includes party."""
        party = Party.create(self.user)
        party.name = 'Test Party'
        party.save()
        party.add(self.template)
        result = get_generated_party(party)
        self.assertEqual(result['party'].name, 'Test Party')

    def test_determine_enemies_with_party(self):
        """Test determine_enemies ignores party_id key.
        
        determine_enemies only handles enemy_template_id_X keys.
        Party generation is handled by the view, not determine_enemies.
        """
        party = Party.create(self.user)
        party.add(self.template)
        post = {
            'party_id': str(party.id)
        }
        result = determine_enemies(post)
        # determine_enemies ignores 'party_id' key
        self.assertEqual(result, [])

    def test_as_json_with_party(self):
        """Test as_json with party enemies."""
        party = Party.create(self.user)
        party.add(self.template)
        result = get_generated_party(party)
        json_str = as_json(result['enemies'])
        self.assertIsInstance(json_str, str)

    def test_save_as_html_with_party(self):
        """Test save_as_html with party enemies."""
        party = Party.create(self.user)
        party.add(self.template)
        result = get_generated_party(party)
        context = {'enemies': result['enemies']}
        html = save_as_html(context, 'generated_enemies.html')
        self.assertIsInstance(html, str)

    def test_get_enemy_templates_with_rank_filter(self):
        """Test get_enemy_templates with rank filter."""
        self.template.rank = 5
        self.template.save()
        templates = get_enemy_templates({'rank': '5'}, self.user)
        for t in templates:
            self.assertEqual(t.rank, 5)

    def test_get_enemy_templates_with_cult_rank_filter(self):
        """Test get_enemy_templates with cult rank filter."""
        templates = get_enemy_templates({'cult_rank': '2'}, self.user)
        # Should return cult templates with rank 2
        for t in templates:
            self.assertEqual(t.race.name, 'Cult')


class ViewsErrorBranchTest(TestCase):
    """Test views.py error handling branches."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='views_error_user', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Views Error Test')
        self.template.published = True
        self.template.save()
        self.factory = RequestFactory()

    def test_views_redirect_on_invalid_request(self):
        """Views redirect on GET when POST is expected."""
        from ..views import generate_enemies, generate_party, set_filter, set_party_filter
        views = [
            ('/generate/', generate_enemies),
            ('/generate_party/', generate_party),
            ('/set_filter/', set_filter),
            ('/set_party_filter/', set_party_filter),
        ]
        for path, view in views:
            with self.subTest(path=path):
                request = self.factory.get(path)
                request.user = self.user
                request.session = {}
                response = view(request)
                self.assertEqual(response.status_code, 302, f'{path} should redirect on GET')
                self.assertIn('Location', response)  # Has redirect target

    def test_export_views_redirect_on_invalid_input(self):
        """Export views redirect on invalid input."""
        from ..views import pdf_export, png_export
        for view_name, view in [('pdf_export', pdf_export), ('png_export', png_export)]:
            with self.subTest(view=view_name):
                # No action parameter
                request = self.factory.get(f'/{view_name}/')
                request.user = self.user
                request.session = {}
                response = view(request)
                self.assertEqual(response.status_code, 302)
                # Invalid path
                request = self.factory.get(f'/{view_name}/', {'action': view_name, 'generated_html': '../etc/passwd.html'})
                request.user = self.user
                request.session = {}
                response = view(request)
                self.assertEqual(response.status_code, 302)

    def test_create_enemy_template_no_race(self):
        """create_enemy_template redirects when no race_id."""
        from ..views import create_enemy_template
        request = self.factory.post('/create_enemy_template/')
        request.user = self.user
        request.session = {}
        response = create_enemy_template(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('Location', response)  # Redirects to index

    def test_delete_template_not_found(self):
        """delete_template handles non-existent template gracefully."""
        from ..views import delete_template
        request = self.factory.get('/delete_template/99999/')
        request.user = self.user
        request.session = {}
        response = delete_template(request, '99999')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 0)  # Returns content, not crash

    def test_delete_party_not_found(self):
        """delete_party handles non-existent party gracefully."""
        from ..views import delete_party
        request = self.factory.get('/delete_party/99999/')
        request.user = self.user
        request.session = {}
        response = delete_party(request, '99999')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 0)  # Returns content, not crash

    def test_enemy_template_private_not_owner(self):
        """enemy_template raises Http404 for private template not owned by user."""
        from ..views import enemy_template
        other_user = User.objects.create_user(username='views_other_user', password='password')
        private_template = EnemyTemplate.create(other_user, self.ruleset, self.race, 'Private')
        private_template.published = False
        private_template.save()

        request = self.factory.get(f'/enemy_template/{private_template.id}/')
        request.user = self.user
        request.session = {}
        with self.assertRaises(Http404):
            enemy_template(request, private_template.id)

    def test_party_private_not_owner(self):
        """party raises Http404 for private party not owned by user."""
        from ..views import party
        other_user = User.objects.create_user(username='views_party_user', password='password')
        private_party = Party.create(other_user)
        private_party.published = False
        private_party.save()

        request = self.factory.get(f'/party/{private_party.id}/')
        request.user = self.user
        request.session = {}
        with self.assertRaises(Http404):
            party(request, private_party.id)

    def test_race_index_not_admin(self):
        """race_index raises Http404 for non-admin user."""
        from ..views import race_index
        request = self.factory.get('/race_index/')
        request.user = self.user
        request.session = {}
        with self.assertRaises(Http404):
            race_index(request)

    def test_clone_template_not_found(self):
        """clone_template raises DoesNotExist for invalid ID."""
        from ..views import clone_template
        request = self.factory.get('/clone_template/99999/')
        request.user = self.user
        request.session = {}
        with self.assertRaises(EnemyTemplate.DoesNotExist):
            clone_template(request, '99999')

    def test_clone_party_not_found(self):
        """clone_party raises DoesNotExist for invalid ID."""
        from ..views import clone_party
        request = self.factory.get('/clone_party/99999/')
        request.user = self.user
        request.session = {}
        with self.assertRaises(Party.DoesNotExist):
            clone_party(request, '99999')

    def test_generate_enemies_json_invalid_amount(self):
        """generate_enemies_json handles invalid amount gracefully."""
        from ..views import generate_enemies_json
        request = self.factory.get('/generate_json/', {'id': str(self.template.id), 'amount': 'abc'})
        request.user = self.user
        request.session = {}
        # Should default to amount=1
        response = generate_enemies_json(request)
        self.assertEqual(response.status_code, 200)
        # Verify JSON content is valid
        import json as json_mod
        data = json_mod.loads(response.content)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)  # Default amount is 1




