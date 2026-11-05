"""
Tests for pagination and server-side search in the index view.

Covers the changes from PR3: pagination (100/page), server-side search via
the `q` query parameter, and their combination.

Note: View-level tests use the view logic directly instead of full HTML rendering
due to Python 3.14 Django template rendering bugs with RequestFactory.
"""
from django.test import TestCase, RequestFactory, Client
from django.contrib.auth.models import User
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from ..models import EnemyTemplate, Race, Ruleset
from ..views_lib import get_enemy_templates, get_filter


def _get_index_templates(user, get_params=None):
    """Simulate the index() view logic and return the paginated templates.

    Mirrors the logic in views.py index() without triggering template rendering.
    """
    get_params = get_params or {}
    q = get_params.get('q', '').strip()
    templates = get_enemy_templates(None, user, search_string=q if q else None)
    paginator = Paginator(templates, 100)
    page = get_params.get('page')
    try:
        return paginator.page(page)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages)


class IndexPaginationTest(TestCase):
    """Test pagination logic in the index() view."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='pagination_test_user', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        # Create enough templates to span multiple pages (page size is 100)
        for i in range(150):
            et = EnemyTemplate.create(self.user, self.ruleset, self.race, f'Pagination Template {i:04d}')
            et.published = True
            et.save()

    def test_index_page_1_loads(self):
        """Index view page 1 returns a paginated template list."""
        templates = _get_index_templates(self.user, {'page': '1'})
        self.assertTrue(hasattr(templates, 'paginator'))
        self.assertEqual(templates.number, 1)

    def test_index_page_2_loads(self):
        """Index view page 2 loads successfully."""
        templates = _get_index_templates(self.user, {'page': '2'})
        self.assertEqual(templates.number, 2)

    def test_index_invalid_page_defaults_to_1(self):
        """Requesting page=abc defaults to page 1."""
        templates = _get_index_templates(self.user, {'page': 'abc'})
        self.assertEqual(templates.number, 1)

    def test_index_empty_page_shows_last(self):
        """Requesting page=9999 shows the last page."""
        templates = _get_index_templates(self.user, {'page': '9999'})
        self.assertEqual(templates.number, templates.paginator.num_pages)

    def test_index_page_size_is_100(self):
        """Each page contains at most 100 templates."""
        templates = _get_index_templates(self.user, {'page': '1'})
        self.assertLessEqual(len(templates), 100)

    def test_index_no_page_param_defaults_to_1(self):
        """No page parameter defaults to page 1."""
        templates = _get_index_templates(self.user, {})
        self.assertEqual(templates.number, 1)

    def test_index_pagination_has_previous_next(self):
        """Page 1 has no previous, has next (with enough templates)."""
        templates = _get_index_templates(self.user, {'page': '1'})
        self.assertFalse(templates.has_previous())
        self.assertTrue(templates.has_next())

    def test_index_last_page_has_previous_no_next(self):
        """Last page has previous, no next."""
        templates = _get_index_templates(self.user, {'page': '9999'})
        self.assertTrue(templates.has_previous())
        self.assertFalse(templates.has_next())

    def test_page_1_and_2_have_different_results(self):
        """Page 1 and page 2 contain different templates."""
        page1 = _get_index_templates(self.user, {'page': '1'})
        page2 = _get_index_templates(self.user, {'page': '2'})
        ids1 = set(t.id for t in page1)
        ids2 = set(t.id for t in page2)
        self.assertEqual(len(ids1 & ids2), 0)


class IndexSearchTest(TestCase):
    """Test server-side search in the index() view via the `q` parameter."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='search_test_user', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.unique_template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'Broo Warrior Test')
        self.unique_template.published = True
        self.unique_template.save()

    def test_search_filters_by_name(self):
        """Search for unique name returns matching template."""
        templates = _get_index_templates(self.user, {'q': 'Broo Warrior Test'})
        names = [t.name for t in templates]
        self.assertIn('Broo Warrior Test', names)

    def test_search_single_word(self):
        """Search for a single word matches templates containing that word."""
        templates = _get_index_templates(self.user, {'q': 'Broo'})
        names = [t.name for t in templates]
        self.assertTrue(any('Broo' in name for name in names))

    def test_search_no_results(self):
        """Search for a non-existent term returns empty results."""
        templates = _get_index_templates(self.user, {'q': 'XYZNonExistent12345'})
        self.assertEqual(len(templates), 0)

    def test_search_empty_string_returns_all(self):
        """Empty search string returns all templates (no filtering)."""
        templates = _get_index_templates(self.user, {'q': ''})
        self.assertGreater(len(templates), 0)

    def test_search_exclusion_prefix(self):
        """Search with - prefix excludes matching templates."""
        templates = _get_index_templates(self.user, {'q': 'Broo -Berserker'})
        names = [t.name for t in templates]
        # Should contain Broo Warrior Test but not Broo Berserker
        self.assertIn('Broo Warrior Test', names)
        self.assertNotIn('Broo Berserker', names)


class SearchPaginationCombinedTest(TestCase):
    """Test search and pagination working together."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='combined_test_user', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        # Create enough search-matching templates for multi-page tests
        for i in range(150):
            et = EnemyTemplate.create(self.user, self.ruleset, self.race, f'Searchable Template {i:04d}')
            et.published = True
            et.save()

    def test_search_with_page_1(self):
        """Search results on page 1 are filtered correctly."""
        templates = _get_index_templates(self.user, {'q': 'Searchable', 'page': '1'})
        self.assertEqual(templates.number, 1)
        for t in templates:
            self.assertTrue('Searchable' in t.name)

    def test_search_results_are_paginated(self):
        """Search results are paginated at 100 per page."""
        templates = _get_index_templates(self.user, {'q': 'Searchable', 'page': '1'})
        self.assertLessEqual(len(templates), 100)

    def test_search_invalid_page_defaults_to_1(self):
        """Search with invalid page defaults to page 1."""
        templates = _get_index_templates(self.user, {'q': 'Searchable', 'page': 'abc'})
        self.assertEqual(templates.number, 1)

    def test_different_pages_have_different_results(self):
        """Page 1 and page 2 of search results contain different templates."""
        page1 = _get_index_templates(self.user, {'q': 'Searchable', 'page': '1'})
        page2 = _get_index_templates(self.user, {'q': 'Searchable', 'page': '2'})
        ids1 = set(t.id for t in page1)
        ids2 = set(t.id for t in page2)
        self.assertEqual(len(ids1 & ids2), 0)


class GetEnemyTemplatesSearchTest(TestCase):
    """Test get_enemy_templates() with the search_string parameter."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='lib_test_user', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)
        self.unique_template = EnemyTemplate.create(self.user, self.ruleset, self.race, 'UniqueSearchTemplate')
        self.unique_template.published = True
        self.unique_template.save()

    def test_search_string_filters_results(self):
        """search_string parameter filters templates by name."""
        templates = get_enemy_templates(None, self.user, search_string='UniqueSearch')
        names = [t.name for t in templates]
        self.assertIn('UniqueSearchTemplate', names)

    def test_search_string_none_returns_all(self):
        """search_string=None returns all templates (no filtering)."""
        templates = get_enemy_templates(None, self.user, search_string=None)
        self.assertGreater(len(templates), 10)

    def test_search_string_empty_returns_all(self):
        """search_string='' is treated as None (returns all)."""
        templates = get_enemy_templates(None, self.user, search_string='')
        self.assertGreater(len(templates), 10)

    def test_search_string_with_filter(self):
        """search_string works with tag filter."""
        self.unique_template.tags.add('TestTag')
        templates = get_enemy_templates('TestTag', self.user, search_string='UniqueSearch')
        names = [t.name for t in templates]
        self.assertIn('UniqueSearchTemplate', names)

    def test_search_string_exclusion(self):
        """search_string with - prefix excludes templates."""
        templates = get_enemy_templates(None, self.user, search_string='-UniqueSearch')
        names = [t.name for t in templates]
        self.assertNotIn('UniqueSearchTemplate', names)

    def test_search_string_starred_annotation(self):
        """Search results have starred annotation for authenticated users."""
        templates = get_enemy_templates(None, self.user, search_string='UniqueSearch')
        for t in templates:
            self.assertTrue(hasattr(t, 'starred'))

    def test_search_string_anonymous_user(self):
        """Search works for anonymous users, only returning published templates."""
        from django.contrib.auth.models import AnonymousUser
        templates = get_enemy_templates(None, AnonymousUser(), search_string='UniqueSearch')
        for t in templates:
            self.assertTrue(t.published)

    def test_search_string_ordering(self):
        """Search results are ordered by published status then rank."""
        templates = get_enemy_templates(None, self.user, search_string='Warrior')
        prev_published = True
        prev_rank = -1
        for t in templates:
            if not t.published:
                prev_published = False
            else:
                self.assertTrue(prev_published)
            if not prev_published:
                self.assertGreaterEqual(t.rank, prev_rank)
            prev_rank = t.rank


class IndexAnonymousUserTest(TestCase):
    """Test pagination and search for anonymous users."""
    fixtures = ('enemygen_testdata.json',)

    def test_anonymous_pagination_works(self):
        """Anonymous user can paginate."""
        from django.contrib.auth.models import AnonymousUser
        templates = _get_index_templates(AnonymousUser(), {'page': '1'})
        self.assertTrue(hasattr(templates, 'paginator'))

    def test_anonymous_search_works(self):
        """Anonymous user can search."""
        from django.contrib.auth.models import AnonymousUser
        # Search for "Centaur" which is in the fixture
        templates = _get_index_templates(AnonymousUser(), {'q': 'Centaur'})
        for t in templates:
            self.assertTrue(t.published)
        # Should find the Centaur Warrior from the fixture
        names = [t.name for t in templates]
        self.assertTrue(any('Centaur' in name for name in names))

    def test_anonymous_sees_only_published(self):
        """Anonymous user only sees published templates."""
        from django.contrib.auth.models import AnonymousUser
        templates = _get_index_templates(AnonymousUser(), {'q': ''})
        for t in templates:
            self.assertTrue(t.published)


class SearchInputTemplateTest(TestCase):
    """Test that the search input and pagination in templates are correct.

    Uses template source inspection instead of Client due to Python 3.14
    Django template rendering bugs.
    """
    def test_search_input_has_name_q(self):
        """Search input has name='q' for form submission."""
        with open('enemygen/templates/index.html') as f:
            content = f.read()
        self.assertIn('name="q"', content)

    def test_search_form_method_get(self):
        """Search form uses GET method."""
        with open('enemygen/templates/index.html') as f:
            content = f.read()
        self.assertIn('method="get"', content)

    def test_search_input_prepopulated(self):
        """Search input value is bound to request.GET.q."""
        with open('enemygen/templates/index.html') as f:
            content = f.read()
        self.assertIn('request.GET.q', content)

    def test_pagination_links_contain_previous(self):
        """Pagination template contains 'previous' link."""
        with open('enemygen/templates/enemy_template_list.html') as f:
            content = f.read()
        self.assertIn('previous', content)

    def test_pagination_links_contain_next(self):
        """Pagination template contains 'next' link."""
        with open('enemygen/templates/enemy_template_list.html') as f:
            content = f.read()
        self.assertIn('next', content)

    def test_pagination_shows_page_number(self):
        """Pagination template shows current page number."""
        with open('enemygen/templates/enemy_template_list.html') as f:
            content = f.read()
        self.assertIn('templates.number', content)
        self.assertIn('templates.paginator.num_pages', content)

    def test_pagination_preserves_search_term(self):
        """Pagination links preserve the search term in the URL."""
        with open('enemygen/templates/enemy_template_list.html') as f:
            content = f.read()
        self.assertIn('&q={{ request.GET.q }}', content)


class PerformanceBenchmarkTest(TestCase):
    """Measure performance improvements from pagination."""
    fixtures = ('enemygen_testdata.json',)

    def setUp(self):
        self.user = User.objects.create_user(username='perf_test_user', password='password')
        self.ruleset = Ruleset.objects.get(id=1)
        self.race = Race.objects.get(id=1)

    def test_paginated_render_time(self):
        """Paginated render (100 templates) is fast."""
        import time
        from django.template.loader import render_to_string

        templates = get_enemy_templates(None, self.user)
        paginator = Paginator(templates, 100)
        page = paginator.page(1)

        factory = RequestFactory()
        start = time.time()
        html = render_to_string('enemy_template_list.html', {
            'templates': page,
            'user': self.user,
            'request': factory.get('/'),
        })
        render_time = time.time() - start

        self.assertLess(render_time, 0.5, f'Paginated render took {render_time:.3f}s, expected < 0.5s')

    def test_paginated_html_size(self):
        """Paginated HTML is significantly smaller than full list."""
        from django.template.loader import render_to_string

        templates = get_enemy_templates(None, self.user)
        paginator = Paginator(templates, 100)
        page = paginator.page(1)

        factory = RequestFactory()
        html = render_to_string('enemy_template_list.html', {
            'templates': page,
            'user': self.user,
            'request': factory.get('/'),
        })
        html_size = len(html)

        self.assertLess(html_size, 500 * 1024, f'Paginated HTML is {html_size/1024:.1f}KB, expected < 500KB')

    def test_queryset_evaluation_time(self):
        """Queryset evaluation for paginated results is fast."""
        import time

        start = time.time()
        templates = get_enemy_templates(None, self.user)
        paginator = Paginator(templates, 100)
        page = paginator.page(1)
        list(page.object_list)
        eval_time = time.time() - start

        self.assertLess(eval_time, 1.0, f'Queryset eval took {eval_time:.3f}s, expected < 1s')

    def test_search_queryset_evaluation_time(self):
        """Search queryset evaluation is fast."""
        import time

        start = time.time()
        templates = get_enemy_templates(None, self.user, search_string='Warrior')
        count = len(templates)
        eval_time = time.time() - start

        self.assertLess(eval_time, 1.0, f'Search eval took {eval_time:.3f}s, expected < 1s')
        self.assertGreater(count, 0, 'Search for Warrior should return results')
