import re
from pathlib import Path
import pytest

from .conftest import MAKEFILE_PATH


@pytest.mark.infra
def test_makefile_has_no_duplicate_targets():
    """
    Verify root Makefile does not contain duplicate target headers.
    """
    makefile_path = MAKEFILE_PATH if MAKEFILE_PATH.exists() else Path('Makefile')
    assert makefile_path.exists(), 'Root Makefile not found.'

    content = makefile_path.read_text(encoding='utf-8', errors='ignore').splitlines()

    header_re = re.compile(r"^(?P<names>[A-Za-z0-9_\-\.\s]+?)\s*::?\s*(?:#.*)?$")
    # Collect occurrences: name -> list of line numbers
    seen: dict[str, list[int]] = {}

    for idx, line in enumerate(content, start=1):
        if not line or line.lstrip() != line:
            # Skip indented lines and blank lines
            continue
        if line.startswith('#'):
            continue
        # Skip variable/assignment lines (contain '=' before any ':')
        if '=' in line and (':' not in line or line.index('=') < line.index(':')):
            continue
        m = header_re.match(line)
        if not m:
            continue
        names_part = m.group('names').strip()
        # Split by whitespace to allow multi-target header like: "a b: deps"
        names = [n.strip() for n in names_part.split() if n.strip()]
        for name in names:
            # Ignore pattern rules and most special dot-prefixed meta-targets except .PHONY
            if '%' in name:
                continue
            if name.startswith('.') and name != '.PHONY':
                continue
            # Record
            seen.setdefault(name, []).append(idx)

    duplicates = {name: lines for name, lines in seen.items() if len(lines) > 1}
    if duplicates:
        details = "\n".join(f"- {name}: lines {lines}" for name, lines in sorted(duplicates.items()))
        pytest.fail(f"Duplicate Makefile targets detected in infra-docker/Makefile:\n{details}")
