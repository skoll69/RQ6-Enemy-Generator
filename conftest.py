import pathlib
from typing import List
import pytest

# Ensure test_web_basic.py runs last across the whole test session.
# We implement pytest_collection_modifyitems to move any tests collected from
# enemygen/tests/test_web_basic.py to the end of the item list, preserving
# relative order of all other tests.
# This is a minimal, plugin-free approach.

TARGET_SUFFIX = str(pathlib.Path('enemygen/tests/test_web_basic.py'))


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: List[pytest.Item]):
    tail: List[pytest.Item] = []
    head: List[pytest.Item] = []
    for it in items:
        # nodeid typically looks like 'enemygen/tests/test_web_basic.py::TestName::test_func'
        node_path = it.nodeid.split('::', 1)[0]
        # Normalize to forward slashes for safety
        norm = node_path.replace('\\', '/')
        if norm.endswith('enemygen/tests/test_web_basic.py'):
            tail.append(it)
        else:
            head.append(it)
    if tail:
        items[:] = head + tail
