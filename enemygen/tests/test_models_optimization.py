"""
Tests for EnemyTemplate model optimizations, focusing on tag fetching and star status caching.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from enemygen.models import EnemyTemplate, Ruleset, Race, Star

class EnemyTemplateOptimizationTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Test Template')
        self.template.tags.add('tag1', 'tag2')

    def test_get_tags(self):
        """
        Purpose: Verifies that EnemyTemplate.get_tags() returns a sorted list of strings.
        Requirement: The optimization uses self.tags.all() (which returns tag objects) 
        internally if prefetched, but must still return names as strings to maintain 
        compatibility with existing templates and logic.
        """
        tags = self.template.get_tags()
        self.assertEqual(tags, ['tag1', 'tag2'])
        self.assertIsInstance(tags[0], str)

    def test_is_starred(self):
        """
        Purpose: Verifies the standard behavior of is_starred when no cache is present.
        Requirement: Must check the database if the 'starred' attribute is missing.
        """
        # Verify initial state
        self.assertFalse(self.template.is_starred(self.user))
        
        # Star it
        Star.objects.create(user=self.user, template=self.template)
        self.assertTrue(self.template.is_starred(self.user))
        
        # Anonymous user
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(self.template.is_starred(AnonymousUser()))

    def test_get_starred(self):
        """
        Purpose: Verifies that EnemyTemplate.get_starred class method returns the correct data.
        Requirement: Resulting templates should have their tags, race, and owner prefetched.
        """
        # Star the template
        Star.objects.create(user=self.user, template=self.template)
        
        starred = EnemyTemplate.get_starred(self.user)
        self.assertEqual(len(starred), 1)
        self.assertEqual(starred[0].id, self.template.id)

    def test_starred_attribute_override(self):
        """
        Purpose: Verifies that the is_starred method respects a manually set 'starred' attribute.
        Requirement: This is the core of the optimization. If the 'starred' attribute exists 
        (populated by annotation), the database query must be skipped.
        """
        # When .starred attribute is True, it should return True regardless of DB
        self.template.starred = True
        self.assertTrue(self.template.is_starred(self.user))
        
        # When .starred attribute is False, it should return False even if it IS starred in DB
        self.template.starred = False
        Star.objects.create(user=self.user, template=self.template)
        self.assertFalse(self.template.is_starred(self.user))

    def test_increment_used(self):
        """
        Purpose: Verifies that increment_used() exists and increments the 'used' counter.
        Requirement: This method is called by views_lib.py during generation but was missing
        from the model, causing a runtime crash (AttributeError).
        """
        initial_used = self.template.used
        self.template.increment_used()
        self.assertEqual(self.template.used, initial_used + 1)
        
        # Verify persistence — reload from DB
        self.template.refresh_from_db()
        self.assertEqual(self.template.used, initial_used + 1)

    def test_get_enemies_calls_increment_used(self):
        """
        Purpose: Verifies that get_enemies() in views_lib.py calls increment_used() when increment=True.
        Requirement: This is the actual call path used by generate_enemies and generate_enemies_json views.
        """
        from ..views_lib import get_enemies, determine_enemies
        
        initial_used = self.template.used
        enemy_index = [(self.template, 2)]  # Generate 2 enemies from this template
        enemies = get_enemies(enemy_index, increment=True)
        
        self.assertEqual(len(enemies), 2)
        self.template.refresh_from_db()
        self.assertEqual(self.template.used, initial_used + 1)

    def test_get_enemies_no_increment(self):
        """
        Purpose: Verifies that get_enemies() does NOT call increment_used() when increment=False.
        Requirement: The 'dont_increment' POST parameter should skip incrementing.
        """
        from ..views_lib import get_enemies
        
        initial_used = self.template.used
        enemy_index = [(self.template, 1)]
        enemies = get_enemies(enemy_index, increment=False)
        
        self.assertEqual(len(enemies), 1)
        self.template.refresh_from_db()
        self.assertEqual(self.template.used, initial_used)

    def test_get_generated_party_calls_increment_used(self):
        """
        Purpose: Verifies that get_generated_party() calls increment_used() for each template in the party.
        Requirement: This is the call path used by generate_party and generate_party_json views.
        """
        from ..views_lib import get_generated_party
        from enemygen.models import Party, TemplateToParty
        
        initial_used = self.template.used
        
        # Create a party with the template
        party = Party.objects.create(name='Test Party', owner=self.user, published=True)
        TemplateToParty.objects.create(party=party, template=self.template, amount=2)
        
        context = get_generated_party(party)
        
        self.assertEqual(len(context['enemies']), 2)
        self.template.refresh_from_db()
        self.assertEqual(self.template.used, initial_used + 1)

    def test_increment_used_does_not_save_other_fields(self):
        """
        Purpose: Verifies that increment_used() only saves the 'used' field, not other modified fields.
        Requirement: Uses save(update_fields=['used']) to prevent accidental persistence of unrelated changes.
        """
        # Modify an unrelated field in memory
        original_name = self.template.name
        self.template.name = 'Temp Modified Name'
        
        # Increment used — should NOT persist the name change
        self.template.increment_used()
        
        # Reload from DB — name should be unchanged
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, original_name)
        # But used should be incremented
        self.assertEqual(self.template.used, 1)

    def test_get_enemies_increments_both_used_and_generated(self):
        """
        Purpose: Verifies that a single generation call increments both 'used' and 'generated' counters.
        Requirement: get_enemies() calls increment_used() and generate(increment=True), so both counters should increase.
        """
        from ..views_lib import get_enemies
        
        initial_used = self.template.used
        initial_generated = self.template.generated
        enemy_index = [(self.template, 1)]
        enemies = get_enemies(enemy_index, increment=True)
        
        self.assertEqual(len(enemies), 1)
        self.template.refresh_from_db()
        self.assertEqual(self.template.used, initial_used + 1)
        self.assertEqual(self.template.generated, initial_generated + 1)

    def test_get_enemies_multiple_templates_increment_independently(self):
        """
        Purpose: Verifies that when generating from multiple templates, each template's 'used' counter increments independently.
        Requirement: Each template gets used += 1 regardless of amount or other templates.
        """
        from ..views_lib import get_enemies
        
        # Create a second template
        template2 = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Test Template 2')
        
        initial_used_1 = self.template.used
        initial_used_2 = template2.used
        
        # Generate from both templates
        enemy_index = [(self.template, 2), (template2, 3)]
        enemies = get_enemies(enemy_index, increment=True)
        
        self.assertEqual(len(enemies), 5)  # 2 + 3 enemies total
        self.template.refresh_from_db()
        template2.refresh_from_db()
        
        # Each template's used counter incremented by 1, not by amount
        self.assertEqual(self.template.used, initial_used_1 + 1)
        self.assertEqual(template2.used, initial_used_2 + 1)

    def test_generate_enemies_json_api_increments_used(self):
        """
        Purpose: Verifies that the generate_enemies_json API endpoint increments the 'used' counter.
        Requirement: This JSON API always calls get_enemies with increment=True, so the used counter
        must increment. Before PR 2, this endpoint would crash with AttributeError.
        """
        import json
        from django.test import Client
        
        initial_used = self.template.used
        client = Client()
        response = client.get(f'/generate_enemies_json/?id={self.template.id}&amount=2')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 2)
        
        self.template.refresh_from_db()
        self.assertEqual(self.template.used, initial_used + 1)

    def test_generate_party_json_api_increments_used(self):
        """
        Purpose: Verifies that the generate_party_json API endpoint increments the 'used' counter.
        Requirement: This JSON API calls get_generated_party which always increments used.
        Before PR 2, this endpoint would crash with AttributeError.
        """
        import json
        from django.test import Client
        from enemygen.models import Party, TemplateToParty
        
        initial_used = self.template.used
        
        # Create a party with the template
        party = Party.objects.create(name='JSON Test Party', owner=self.user, published=True)
        TemplateToParty.objects.create(party=party, template=self.template, amount=2)
        
        client = Client()
        response = client.get(f'/generate_party_json/?id={party.id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['enemies']), 2)
        self.assertEqual(data['party_name'], 'JSON Test Party')
        
        self.template.refresh_from_db()
        self.assertEqual(self.template.used, initial_used + 1)
