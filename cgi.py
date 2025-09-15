"""
Minimal compatibility shim for the deprecated stdlib module 'cgi' removed in Python 3.13.

This module provides a subset of the old 'cgi' API that Django 3.2 expects,
primarily cgi.parse_header, and a simple escape function mapped to html.escape.

By placing this file in the project root (which is on sys.path before the
stdlib), imports like `import cgi` in third-party packages will resolve here
on Python 3.13+, avoiding ModuleNotFoundError.

Note: This is intentionally minimal and should only be expanded if additional
symbols are required by dependencies in this project.
"""
from __future__ import annotations
from typing import Tuple, Dict
import html
import re


def parse_header(line: str) -> Tuple[str, Dict[str, str]]:
    """Parse a Content-Type like header into a main value and parameter dict.

    This mimics the behavior of cgi.parse_header for common cases used by Django:
    - Returns a tuple (value, params)
    - Value is lowercased and stripped
    - Params keys are lowercased; values are stripped and unquoted if quoted
    """
    if line is None:
        return "", {}
    if not isinstance(line, str):
        try:
            line = line.decode("utf-8", errors="ignore")
        except Exception:
            line = str(line)
    parts = [p.strip() for p in line.split(";")]
    if not parts:
        return "", {}
    value = parts[0].strip().lower()
    params: Dict[str, str] = {}
    for p in parts[1:]:
        if not p:
            continue
        if "=" in p:
            k, v = p.split("=", 1)
            k = k.strip().lower()
            v = v.strip()
            if (v.startswith("\"") and v.endswith("\"")) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            params[k] = v
        else:
            # parameter without value
            params[p.strip().lower()] = ""
    return value, params


def escape(s: str, quote: bool = True) -> str:
    """Compatibility shim for cgi.escape using html.escape.
    cgi.escape(s, quote=True) -> html.escape(s, quote=quote)
    """
    return html.escape(s, quote=quote)


# Django <4.1 (and other libs) may call cgi.valid_boundary during multipart parsing.
# The original implementation validated that a MIME boundary consists of allowed
# characters. Provide a conservative port that matches common Django expectations.
_VALID_BOUNDARY_RE = re.compile(r"^[ -~]{0,200}$")  # visible ASCII, up to 200 chars


def valid_boundary(s: str) -> bool:
    """Return True if 's' is a syntactically valid multipart boundary.

    Compatible with legacy cgi.valid_boundary behavior used by Django 3.2,
    allowing visible ASCII without control characters and reasonable length.
    """
    if not isinstance(s, str):
        try:
            s = s.decode("utf-8", errors="ignore")
        except Exception:
            return False
    if not s:
        return False
    # Disallow CR/LF and other control chars; allow visible ASCII only
    if not _VALID_BOUNDARY_RE.match(s):
        return False
    # Must not contain spaces at ends
    if s[0].isspace() or s[-1].isspace():
        return False
    return True
