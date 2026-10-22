"""
Tests for Enemy list view optimizations, focusing on visibility, ordering, and performance.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from enemygen.models import EnemyTemplate, Ruleset, Race, Star
from enemygen.views_lib import get_enemy_templates

class EnemyViewsOptimizationTest(TestCase):
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        
        # Create some templates
        # Public rank 1
        self.public1 = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Public 1')
        self.public1.published = True
        self.public1.rank = 1
        self.public1.save()
        self.public1.tags.add('tag_a')
        
        # Public rank 2
        self.public2 = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Public 2')
        self.public2.published = True
        self.public2.rank = 2
        self.public2.save()
        self.public2.tags.add('tag_b')
        
        # Private rank 1
        self.private1 = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Private 1')
        self.private1.published = False
        self.private1.rank = 1
        self.private1.save()
        
        # Private rank 2
        self.private2 = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Private 2')
        self.private2.published = False
        self.private2.rank = 2
        self.private2.save()
        
        # Another user's private template (should NOT be visible)
        self.other_user = User.objects.create_user(username='other', password='password')
        self.other_private = EnemyTemplate.create(self.other_user, self.ruleset, self.race, 'Other Private')
        self.other_private.published = False
        self.other_private.save()

    def test_get_enemy_templates_visibility_anonymous(self):
        """
        Purpose: Verifies that anonymous users only see published templates.
        """
        from django.contrib.auth.models import AnonymousUser
        templates = get_enemy_templates(None, AnonymousUser())
        
        # Should only see public1 and public2
        template_ids = [t.id for t in templates]
        self.assertIn(self.public1.id, template_ids)
        self.assertIn(self.public2.id, template_ids)
        self.assertNotIn(self.private1.id, template_ids)
        self.assertNotIn(self.other_private.id, template_ids)

    def test_get_enemy_templates_visibility_authenticated(self):
        """
        Purpose: Verifies that authenticated users see published templates AND their own private ones.
        """
        templates = get_enemy_templates(None, self.user)
        
        template_ids = [t.id for t in templates]
        self.assertIn(self.public1.id, template_ids)
        self.assertIn(self.public2.id, template_ids)
        self.assertIn(self.private1.id, template_ids)
        self.assertIn(self.private2.id, template_ids)
        self.assertNotIn(self.other_private.id, template_ids)

    def test_get_enemy_templates_ordering(self):
        """
        Purpose: Verifies that templates are ordered by published status (True first) and then by rank.
        """
        templates = list(get_enemy_templates(None, self.user))
        
        # Expected order: Public rank 1, Public rank 2, Private rank 1, Private rank 2
        # (Assuming no other templates from fixture interfere, but fixture templates are rank 5 or 10 usually)
        
        # Filter only our test templates to be sure
        test_ids = [self.public1.id, self.public2.id, self.private1.id, self.private2.id]
        ordered_test_templates = [t for t in templates if t.id in test_ids]
        
        self.assertEqual(ordered_test_templates[0].id, self.public1.id)
        self.assertEqual(ordered_test_templates[1].id, self.public2.id)
        self.assertEqual(ordered_test_templates[2].id, self.private1.id)
        self.assertEqual(ordered_test_templates[3].id, self.private2.id)

    def test_get_enemy_templates_filtering(self):
        """
        Purpose: Verifies that tag filtering still works correctly with the consolidated query.
        """
        templates = get_enemy_templates('tag_a', self.user)
        template_ids = [t.id for t in templates]
        self.assertIn(self.public1.id, template_ids)
        self.assertNotIn(self.public2.id, template_ids)

    def test_get_enemy_templates_related_data(self):
        """
        Purpose: Verifies that accessing related data (tags, race, owner) works and doesn't crash.
        Requirement: The consolidated query uses select_related and prefetch_related.
        """
        templates = get_enemy_templates(None, self.user)
        for et in templates:
            self.assertIsNotNone(et.race.name)
            self.assertIsNotNone(et.owner.username)
            self.assertIsInstance(et.get_tags(), list)
            # Verify starred attribute is set
            self.assertTrue(hasattr(et, 'starred'))
