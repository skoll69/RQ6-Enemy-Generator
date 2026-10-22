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
