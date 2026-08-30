"""
Regression tests for the 'Star Bug' where favorites were not displaying correctly.
Covers model methods and AJAX search results.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from ..models import EnemyTemplate, Ruleset, Race, Star
from ..ajax import search
import json

class StarBugRegressionTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Test Template')
        
    def test_is_starred_robustness(self):
        # Case 1: Not starred, no annotation
        self.assertFalse(self.template.is_starred(self.user))
        
        # Case 2: Starred, no annotation
        Star.objects.create(user=self.user, template=self.template)
        # We need to refresh from DB or just ensure no attr exists
        if hasattr(self.template, 'starred'):
            delattr(self.template, 'starred')
        self.assertTrue(self.template.is_starred(self.user))
        
        # Case 3: Annotated as True
        self.template.starred = True
        self.assertTrue(self.template.is_starred(self.user))
        
        # Case 4: Annotated as False
        self.template.starred = False
        self.assertTrue(Star.objects.filter(user=self.user, template=self.template).exists())
        self.assertFalse(self.template.is_starred(self.user))
        
        # Case 5: Anonymous User
        self.assertFalse(self.template.is_starred(AnonymousUser()))

    def test_summary_dict_starred(self):
        # Case 1: Anonymous user
        summary = self.template.summary_dict(AnonymousUser())
        self.assertIn('starred', summary)
        self.assertFalse(summary['starred'])
        
        # Case 2: Authenticated user, not starred
        summary = self.template.summary_dict(self.user)
        self.assertFalse(summary['starred'])
        
        # Case 3: Authenticated user, starred
        Star.objects.create(user=self.user, template=self.template)
        summary = self.template.summary_dict(self.user)
        self.assertTrue(summary['starred'])
        
        # Case 4: No user passed
        summary = self.template.summary_dict()
        self.assertIn('starred', summary)
        self.assertFalse(summary['starred'])

    def test_ajax_search_starred_status(self):
        # Star the template
        Star.objects.create(user=self.user, template=self.template)
        self.template.published = True
        self.template.save()
        
        request = self.factory.get('/rest/search/', {'string': 'Test Template'})
        request.user = self.user
        
        response = search(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        found = False
        for result in data['results']:
            if result['id'] == self.template.id:
                self.assertTrue(result['starred'], "Starred status missing or False in AJAX search results")
                found = True
        self.assertTrue(found, "Template not found in search results")

    def test_star_persistence(self):
        from ..ajax import toggle_star
        # Initial state: Not starred
        self.assertFalse(Star.objects.filter(user=self.user, template=self.template).exists())
        
        # Toggle star via AJAX
        request = self.factory.post(f'/rest/toggle_star/{self.template.id}/')
        request.user = self.user
        response = toggle_star(request, self.template.id)
        self.assertEqual(response.status_code, 200)
        
        # Verify persistence in DB
        self.assertTrue(Star.objects.filter(user=self.user, template=self.template).exists())
        
        # Verify it shows up as starred in a fresh retrieval
        fresh_template = EnemyTemplate.objects.get(id=self.template.id)
        self.assertTrue(fresh_template.is_starred(self.user))
        
        # Toggle again to unstar
        response = toggle_star(request, self.template.id)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Star.objects.filter(user=self.user, template=self.template).exists())

    def test_get_enemy_templates_starred_annotation(self):
        from ..views_lib import get_enemy_templates
        # Star the template
        Star.objects.create(user=self.user, template=self.template)
        
        # Fetch starred templates
        templates = get_enemy_templates('Starred', self.user)
        self.assertEqual(templates.count(), 1)
        
        # Verify annotation
        starred_template = templates[0]
        self.assertTrue(hasattr(starred_template, 'starred'), "Template should have 'starred' attribute when fetched via 'Starred' filter")
        self.assertTrue(starred_template.starred, "Starred attribute should be True for starred templates")
