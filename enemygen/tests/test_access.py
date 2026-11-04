"""
Consolidated access control tests.

This file combines all access control tests from:
- test_access_control.py (TemplateAccessControlTest, PartyAccessControlTest,
  SearchAccessControlTest, AjaxSearchAccessControlTest, IndexJsonAccessControlTest,
  PartyIndexJsonAccessControlTest, SearchSyntaxTest)
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
import json

from ..models import (
    EnemyTemplate, Party, Race, Ruleset, TemplateToParty,
)
from ..views_lib import get_enemy_templates, get_party_templates


class TemplateAccessControlTest(TestCase):
    """Test EnemyTemplate visibility based on published status and user auth."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user2 = User.objects.create_user(username='user2', password='pass')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)

        # User1's templates
        self.u1_public = EnemyTemplate.create(self.user1, self.ruleset, self.race, 'U1 Public')
        self.u1_public.published = True
        self.u1_public.save()

        self.u1_private = EnemyTemplate.create(self.user1, self.ruleset, self.race, 'U1 Private')
        self.u1_private.published = False
        self.u1_private.save()

        # User2's templates
        self.u2_public = EnemyTemplate.create(self.user2, self.ruleset, self.race, 'U2 Public')
        self.u2_public.published = True
        self.u2_public.save()

        self.u2_private = EnemyTemplate.create(self.user2, self.ruleset, self.race, 'U2 Private')
        self.u2_private.published = False
        self.u2_private.save()

    def test_owner_sees_own_public(self):
        """User1 can see their own public template."""
        templates = get_enemy_templates(None, self.user1)
        names = [t.name for t in templates]
        self.assertIn('U1 Public', names)

    def test_owner_sees_own_private(self):
        """User1 can see their own private template."""
        templates = get_enemy_templates(None, self.user1)
        names = [t.name for t in templates]
        self.assertIn('U1 Private', names)

    def test_owner_sees_other_public(self):
        """User1 can see User2's public template."""
        templates = get_enemy_templates(None, self.user1)
        names = [t.name for t in templates]
        self.assertIn('U2 Public', names)

    def test_owner_cannot_see_other_private(self):
        """User1 CANNOT see User2's private template."""
        templates = get_enemy_templates(None, self.user1)
        names = [t.name for t in templates]
        self.assertNotIn('U2 Private', names)

    def test_anonymous_sees_public_only(self):
        """Anonymous user only sees public templates."""
        templates = get_enemy_templates(None, AnonymousUser())
        names = [t.name for t in templates]
        self.assertIn('U1 Public', names)
        self.assertIn('U2 Public', names)
        self.assertNotIn('U1 Private', names)
        self.assertNotIn('U2 Private', names)

    def test_anonymous_cannot_see_any_private(self):
        """Anonymous user cannot see any private templates."""
        templates = get_enemy_templates(None, AnonymousUser())
        for t in templates:
            self.assertTrue(t.published, f"Anonymous user saw unpublished template: {t.name}")




class PartyAccessControlTest(TestCase):
    """Test Party visibility based on published status and user auth."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user2 = User.objects.create_user(username='user2', password='pass')

        # User1's parties
        self.u1_public = Party.create(self.user1)
        self.u1_public.name = 'U1 Public Party'
        self.u1_public.published = True
        self.u1_public.save()

        self.u1_private = Party.create(self.user1)
        self.u1_private.name = 'U1 Private Party'
        self.u1_private.published = False
        self.u1_private.save()

        # User2's parties
        self.u2_public = Party.create(self.user2)
        self.u2_public.name = 'U2 Public Party'
        self.u2_public.published = True
        self.u2_public.save()

        self.u2_private = Party.create(self.user2)
        self.u2_private.name = 'U2 Private Party'
        self.u2_private.published = False
        self.u2_private.save()

    def test_owner_sees_own_public_party(self):
        """User1 can see their own public party."""
        parties = get_party_templates(None, self.user1)
        names = [p.name for p in parties]
        self.assertIn('U1 Public Party', names)

    def test_owner_sees_own_private_party(self):
        """User1 can see their own private party."""
        parties = get_party_templates(None, self.user1)
        names = [p.name for p in parties]
        self.assertIn('U1 Private Party', names)

    def test_owner_sees_other_public_party(self):
        """User1 can see User2's public party."""
        parties = get_party_templates(None, self.user1)
        names = [p.name for p in parties]
        self.assertIn('U2 Public Party', names)

    def test_owner_cannot_see_other_private_party(self):
        """User1 CANNOT see User2's private party."""
        parties = get_party_templates(None, self.user1)
        names = [p.name for p in parties]
        self.assertNotIn('U2 Private Party', names)

    def test_anonymous_sees_public_parties_only(self):
        """Anonymous user only sees public parties."""
        parties = get_party_templates(None, AnonymousUser())
        names = [p.name for p in parties]
        self.assertIn('U1 Public Party', names)
        self.assertIn('U2 Public Party', names)
        self.assertNotIn('U1 Private Party', names)
        self.assertNotIn('U2 Private Party', names)




class SearchAccessControlTest(TestCase):
    """Test that EnemyTemplate.search() respects access control."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user2 = User.objects.create_user(username='user2', password='pass')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)

        # User1's templates
        self.u1_public = EnemyTemplate.create(self.user1, self.ruleset, self.race, 'Orc Warrior')
        self.u1_public.published = True
        self.u1_public.save()

        self.u1_private = EnemyTemplate.create(self.user1, self.ruleset, self.race, 'Orc Private')
        self.u1_private.published = False
        self.u1_private.save()

        # User2's templates
        self.u2_public = EnemyTemplate.create(self.user2, self.ruleset, self.race, 'Elf Warrior')
        self.u2_public.published = True
        self.u2_public.save()

        self.u2_private = EnemyTemplate.create(self.user2, self.ruleset, self.race, 'Elf Private')
        self.u2_private.published = False
        self.u2_private.save()

    def test_search_owner_finds_own_private(self):
        """User1 search finds their own private template."""
        results = EnemyTemplate.search('Orc Private', self.user1)
        names = [r.name for r in results]
        self.assertIn('Orc Private', names)

    def test_search_owner_cannot_find_other_private(self):
        """User1 search CANNOT find User2's private template."""
        results = EnemyTemplate.search('Elf Private', self.user1)
        names = [r.name for r in results]
        self.assertNotIn('Elf Private', names)

    def test_search_anonymous_finds_public_only(self):
        """Anonymous search only finds public templates."""
        results = EnemyTemplate.search('Warrior', AnonymousUser())
        names = [r.name for r in results]
        self.assertIn('Orc Warrior', names)
        self.assertIn('Elf Warrior', names)
        self.assertNotIn('Orc Private', names)
        self.assertNotIn('Elf Private', names)

    def test_search_anonymous_cannot_find_private(self):
        """Anonymous search cannot find private templates."""
        results = EnemyTemplate.search('Private', AnonymousUser())
        self.assertEqual(len(results), 0, "Anonymous user found private templates via search")
        self.assertTrue(hasattr(results, 'all'))  # Is iterable (QuerySet)

    def test_search_multi_word_and_filter(self):
        """Multi-word search acts as AND filter."""
        results = EnemyTemplate.search('Orc Warrior', self.user1)
        names = [r.name for r in results]
        self.assertIn('Orc Warrior', names)
        # Should not match "Orc Private" because it doesn't contain "Warrior"
        self.assertNotIn('Orc Private', names)

    def test_search_exclusion(self):
        """Search with - prefix excludes matching templates."""
        results = EnemyTemplate.search('Warrior -Orc', self.user1)
        names = [r.name for r in results]
        self.assertNotIn('Orc Warrior', names)
        self.assertIn('Elf Warrior', names)

    def test_search_by_race_name(self):
        """Search matches against race name."""
        results = EnemyTemplate.search('Human', self.user1)
        # All templates use Human race, so all public ones should match
        for r in results:
            self.assertEqual(r.race.name, 'Human')

    def test_search_by_tag(self):
        """Search matches against tags."""
        self.u1_public.tags.add('Bandit')
        self.u1_public.save()
        results = EnemyTemplate.search('Bandit', self.user1)
        names = [r.name for r in results]
        self.assertIn('Orc Warrior', names)

    def test_search_combined_exclusion_inclusion(self):
        """Search with both inclusion and exclusion words."""
        self.u1_public.tags.add('Cave')
        self.u1_public.save()
        self.u2_public.tags.add('Cave')
        self.u2_public.save()
        
        # Search for "Cave" but exclude "Orc"
        results = EnemyTemplate.search('Cave -Orc', self.user1)
        names = [r.name for r in results]
        self.assertNotIn('Orc Warrior', names)
        self.assertIn('Elf Warrior', names)

    def test_search_rank_filter(self):
        """Search respects rank filter."""
        self.u1_public.rank = 1
        self.u1_public.save()
        self.u2_public.rank = 5
        self.u2_public.save()
        
        results = EnemyTemplate.search('', self.user1, rank_filter=['1'])
        names = [r.name for r in results]
        self.assertIn('Orc Warrior', names)
        self.assertNotIn('Elf Warrior', names)

    def test_search_cult_rank_filter(self):
        """Search respects cult rank filter."""
        self.u1_public.cult_rank = 1
        self.u1_public.save()
        
        results = EnemyTemplate.search('', self.user1, cult_rank_filter=['1'])
        names = [r.name for r in results]
        self.assertIn('Orc Warrior', names)




class AjaxSearchAccessControlTest(TestCase):
    """Test the AJAX search endpoint respects access control."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user2 = User.objects.create_user(username='user2', password='pass')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)

        self.u1_public = EnemyTemplate.create(self.user1, self.ruleset, self.race, 'Ajax Public')
        self.u1_public.published = True
        self.u1_public.save()

        self.u1_private = EnemyTemplate.create(self.user1, self.ruleset, self.race, 'Ajax Private')
        self.u1_private.published = False
        self.u1_private.save()

        self.u2_private = EnemyTemplate.create(self.user2, self.ruleset, self.race, 'Ajax Other Private')
        self.u2_private.published = False
        self.u2_private.save()

        self.client = Client()

    def test_ajax_search_logged_in_sees_own_private(self):
        """Logged-in user1 AJAX search finds their own private template."""
        self.client.login(username='user1', password='pass')
        response = self.client.get(reverse('search'), {'string': 'Ajax Private'})
        data = json.loads(response.content)
        names = [r['name'] for r in data['results']]
        self.assertIn('Ajax Private', names)

    def test_ajax_search_logged_in_cannot_see_other_private(self):
        """Logged-in user1 AJAX search CANNOT find user2's private template."""
        self.client.login(username='user1', password='pass')
        response = self.client.get(reverse('search'), {'string': 'Ajax Other Private'})
        data = json.loads(response.content)
        names = [r['name'] for r in data['results']]
        self.assertNotIn('Ajax Other Private', names)

    def test_ajax_search_anonymous_sees_public_only(self):
        """Anonymous AJAX search only sees public templates."""
        response = self.client.get(reverse('search'), {'string': 'Ajax'})
        data = json.loads(response.content)
        names = [r['name'] for r in data['results']]
        self.assertIn('Ajax Public', names)
        self.assertNotIn('Ajax Private', names)
        self.assertNotIn('Ajax Other Private', names)




class IndexJsonAccessControlTest(TestCase):
    """Test index_json API respects access control."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user2 = User.objects.create_user(username='user2', password='pass')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)

        self.u1_public = EnemyTemplate.create(self.user1, self.ruleset, self.race, 'Json Public')
        self.u1_public.published = True
        self.u1_public.save()

        self.u1_private = EnemyTemplate.create(self.user1, self.ruleset, self.race, 'Json Private')
        self.u1_private.published = False
        self.u1_private.save()

        self.u2_private = EnemyTemplate.create(self.user2, self.ruleset, self.race, 'Json Other Private')
        self.u2_private.published = False
        self.u2_private.save()

        self.client = Client()

    def test_index_json_logged_in_sees_own_private(self):
        """Logged-in user1 index_json includes their own private template."""
        self.client.login(username='user1', password='pass')
        response = self.client.get(reverse('index_json'))
        data = json.loads(response.content)
        names = [item['name'] for item in data]
        self.assertIn('Json Public', names)
        self.assertIn('Json Private', names)
        self.assertNotIn('Json Other Private', names)

    def test_index_json_anonymous_sees_public_only(self):
        """Anonymous index_json only includes public templates."""
        response = self.client.get(reverse('index_json'))
        data = json.loads(response.content)
        names = [item['name'] for item in data]
        self.assertIn('Json Public', names)
        self.assertNotIn('Json Private', names)
        self.assertNotIn('Json Other Private', names)




class PartyIndexJsonAccessControlTest(TestCase):
    """Test party_index_json API respects access control."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user2 = User.objects.create_user(username='user2', password='pass')

        self.u1_public = Party.create(self.user1)
        self.u1_public.name = 'Party Json Public'
        self.u1_public.published = True
        self.u1_public.save()

        self.u1_private = Party.create(self.user1)
        self.u1_private.name = 'Party Json Private'
        self.u1_private.published = False
        self.u1_private.save()

        self.u2_private = Party.create(self.user2)
        self.u2_private.name = 'Party Json Other Private'
        self.u2_private.published = False
        self.u2_private.save()

        self.client = Client()

    def test_party_index_json_logged_in_sees_own_private(self):
        """Logged-in user1 party_index_json includes their own private party."""
        self.client.login(username='user1', password='pass')
        response = self.client.get(reverse('party_index_json'))
        data = json.loads(response.content)
        names = [item['name'] for item in data]
        self.assertIn('Party Json Public', names)
        self.assertIn('Party Json Private', names)
        self.assertNotIn('Party Json Other Private', names)

    def test_party_index_json_anonymous_sees_public_only(self):
        """Anonymous party_index_json only includes public parties."""
        response = self.client.get(reverse('party_index_json'))
        data = json.loads(response.content)
        names = [item['name'] for item in data]
        self.assertIn('Party Json Public', names)
        self.assertNotIn('Party Json Private', names)
        self.assertNotIn('Party Json Other Private', names)




class SearchSyntaxTest(TestCase):
    """Test all search syntax possibilities in EnemyTemplate.search()."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='searchuser', password='pass')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)

        # Create templates with various names for testing
        self.t1 = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Orc Warrior')
        self.t1.published = True
        self.t1.save()
        self.t1.tags.add('Melee', 'Cave')

        self.t2 = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Elf Archer')
        self.t2.published = True
        self.t2.save()
        self.t2.tags.add('Ranged', 'Forest')

        self.t3 = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Dwarf Warrior')
        self.t3.published = True
        self.t3.save()
        self.t3.tags.add('Melee', 'Mountain')

        self.t4 = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Goblin Scout')
        self.t4.published = True
        self.t4.save()
        self.t4.tags.add('Ranged', 'Cave')

    def test_search_empty_string(self):
        """Empty search returns all published templates."""
        results = EnemyTemplate.search('', self.user)
        names = [r.name for r in results]
        self.assertIn('Orc Warrior', names)
        self.assertIn('Elf Archer', names)
        self.assertIn('Dwarf Warrior', names)
        self.assertIn('Goblin Scout', names)

    def test_search_single_word(self):
        """Single word search matches name, race, or tags."""
        results = EnemyTemplate.search('Warrior', self.user)
        names = [r.name for r in results]
        self.assertIn('Orc Warrior', names)
        self.assertIn('Dwarf Warrior', names)
        self.assertNotIn('Elf Archer', names)
        self.assertNotIn('Goblin Scout', names)

    def test_search_multi_word_and(self):
        """Multi-word search acts as AND - all words must match."""
        results = EnemyTemplate.search('Orc Warrior', self.user)
        names = [r.name for r in results]
        self.assertIn('Orc Warrior', names)
        self.assertNotIn('Dwarf Warrior', names)  # Has "Warrior" but not "Orc"

    def test_search_syntax_by_tag(self):
        """Search matches against tags."""
        results = EnemyTemplate.search('Melee', self.user)
        names = [r.name for r in results]
        self.assertIn('Orc Warrior', names)
        self.assertIn('Dwarf Warrior', names)
        self.assertNotIn('Elf Archer', names)
        self.assertNotIn('Goblin Scout', names)

    def test_search_exclusion_single(self):
        """Exclusion with - prefix excludes matching templates."""
        results = EnemyTemplate.search('Warrior -Orc', self.user)
        names = [r.name for r in results]
        self.assertNotIn('Orc Warrior', names)
        self.assertIn('Dwarf Warrior', names)

    def test_search_exclusion_multiple(self):
        """Multiple exclusion words."""
        results = EnemyTemplate.search('Melee -Orc -Dwarf', self.user)
        # No templates match "Melee" without "Orc" or "Dwarf"
        names = [r.name for r in results]
        self.assertNotIn('Orc Warrior', names)
        self.assertNotIn('Dwarf Warrior', names)

    def test_search_case_insensitive(self):
        """Search is case-insensitive."""
        results_upper = EnemyTemplate.search('WARRIOR', self.user)
        results_lower = EnemyTemplate.search('warrior', self.user)
        names_upper = [r.name for r in results_upper]
        names_lower = [r.name for r in results_lower]
        self.assertEqual(set(names_upper), set(names_lower))

    def test_search_exclusion_case_insensitive(self):
        """Exclusion is case-insensitive."""
        results = EnemyTemplate.search('Warrior -orc', self.user)
        names = [r.name for r in results]
        self.assertNotIn('Orc Warrior', names)
        self.assertIn('Dwarf Warrior', names)

    def test_search_combined_inclusion_exclusion(self):
        """Search with both inclusion and exclusion words."""
        results = EnemyTemplate.search('Melee Cave -Dwarf', self.user)
        names = [r.name for r in results]
        self.assertIn('Orc Warrior', names)  # Has Melee and Cave tags
        self.assertNotIn('Dwarf Warrior', names)  # Has Melee but excluded by -Dwarf

    def test_search_syntax_by_race_name(self):
        """Search matches against race name."""
        results = EnemyTemplate.search('Human', self.user)
        # All templates use Human race
        for r in results:
            self.assertEqual(r.race.name, 'Human')

    def test_search_syntax_rank_filter(self):
        """Search with rank filter."""
        self.t1.rank = 1
        self.t1.save()
        self.t2.rank = 5
        self.t2.save()
        
        results = EnemyTemplate.search('', self.user, rank_filter=['1'])
        names = [r.name for r in results]
        self.assertIn('Orc Warrior', names)
        self.assertNotIn('Elf Archer', names)

    def test_search_syntax_cult_rank_filter(self):
        """Search with cult rank filter."""
        self.t1.cult_rank = 1
        self.t1.save()
        
        results = EnemyTemplate.search('', self.user, cult_rank_filter=['1'])
        names = [r.name for r in results]
        self.assertIn('Orc Warrior', names)

    def test_search_combined_filters(self):
        """Search with both rank and cult rank filters."""
        self.t1.rank = 1
        self.t1.cult_rank = 1
        self.t1.save()
        self.t2.rank = 1
        self.t2.cult_rank = 0
        self.t2.save()
        
        results = EnemyTemplate.search('', self.user, rank_filter=['1'], cult_rank_filter=['1'])
        names = [r.name for r in results]
        self.assertIn('Orc Warrior', names)
        self.assertNotIn('Elf Archer', names)

    def test_search_whitespace_handling(self):
        """Search trims whitespace from query."""
        results = EnemyTemplate.search('  Warrior  ', self.user)
        names = [r.name for r in results]
        self.assertIn('Orc Warrior', names)
        self.assertIn('Dwarf Warrior', names)

    def test_search_no_results(self):
        """Search with no matches returns empty."""
        results = EnemyTemplate.search('NonexistentTemplate', self.user)
        self.assertEqual(len(results), 0)
        self.assertTrue(hasattr(results, 'all'))  # Is iterable (QuerySet)


