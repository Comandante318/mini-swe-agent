"""Regression tests for version management.

The .github/bump_version.py script was removed in this PR.
That script relied on a specific regex to locate and update __version__ in __init__.py.
These tests verify that:
  - __version__ still exists and is correctly formatted so any future tooling can find it
  - The regex that bump_version.py used still matches the current __init__.py content
  - The version follows semantic versioning conventions
"""

import re
from pathlib import Path

import pytest

INIT_FILE = Path("src/minisweagent/__init__.py")

# Regex taken directly from the deleted .github/bump_version.py
VERSION_RE = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.MULTILINE)

# Semantic version pattern: MAJOR.MINOR.PATCH with optional pre-release / build suffixes
SEMVER_RE = re.compile(
    r"^\d+\.\d+\.\d+"          # core MAJOR.MINOR.PATCH
    r"(?:[-.]?[a-zA-Z0-9]+)*$"  # optional pre-release labels (e.g. .dev1, -rc2)
)


class TestVersionFormat:
    """Verify that __version__ in __init__.py is well-formed."""

    def test_init_file_exists(self):
        """The package __init__.py must exist."""
        assert INIT_FILE.exists(), f"{INIT_FILE} does not exist"

    def test_version_present_in_init(self):
        """__version__ assignment must be present in src/minisweagent/__init__.py."""
        content = INIT_FILE.read_text()
        assert "__version__" in content

    def test_version_regex_matches(self):
        """The regex used by the deleted bump_version.py must match __version__ in __init__.py."""
        content = INIT_FILE.read_text()
        match = VERSION_RE.search(content)
        assert match is not None, (
            f"VERSION_RE did not match __version__ in {INIT_FILE}. "
            "Check that __version__ is assigned on a single line with double-quoted value."
        )

    def test_version_is_non_empty(self):
        """The extracted version string must not be empty."""
        content = INIT_FILE.read_text()
        match = VERSION_RE.search(content)
        assert match is not None
        version = match.group(1)
        assert version.strip(), "Extracted __version__ must not be empty or whitespace"

    def test_version_follows_semver(self):
        """Extracted __version__ must follow MAJOR.MINOR.PATCH semantic versioning."""
        content = INIT_FILE.read_text()
        match = VERSION_RE.search(content)
        assert match is not None
        version = match.group(1)
        assert SEMVER_RE.match(version), (
            f"__version__ '{version}' does not look like a semantic version (e.g. '2.0.0')"
        )

    def test_version_importable(self):
        """__version__ must be importable from the package."""
        from minisweagent import __version__

        assert isinstance(__version__, str)
        assert __version__  # non-empty

    def test_imported_version_matches_init_file(self):
        """The __version__ imported from the package must match what is written in __init__.py."""
        from minisweagent import __version__

        content = INIT_FILE.read_text()
        match = VERSION_RE.search(content)
        assert match is not None
        file_version = match.group(1)
        assert __version__ == file_version, (
            f"Imported __version__ ({__version__!r}) != version in {INIT_FILE} ({file_version!r})"
        )

    def test_version_regex_does_not_match_commented_version(self, tmp_path):
        """VERSION_RE should NOT match a commented-out __version__ line."""
        fake_init = tmp_path / "__init__.py"
        fake_init.write_text('# __version__ = "0.0.0"\n__version__ = "1.2.3"\n')
        content = fake_init.read_text()
        match = VERSION_RE.search(content)
        assert match is not None
        # The regex uses ^ in MULTILINE mode, so it anchors to start of line.
        # A comment line starts with '#', not '__version__', so the regex must match
        # only the uncommented line.
        assert match.group(1) == "1.2.3"

    def test_version_string_can_be_replaced(self):
        """Simulate the bump_version.py replacement logic: inserting a new version works correctly."""
        content = INIT_FILE.read_text()
        match = VERSION_RE.search(content)
        assert match is not None
        current = match.group(1)

        # Simulate replacement with a fake next version
        new_version = "99.0.0"
        updated = content[: match.start(1)] + new_version + content[match.end(1) :]

        # Verify the replacement worked
        new_match = VERSION_RE.search(updated)
        assert new_match is not None
        assert new_match.group(1) == new_version

        # Original version is no longer present as __version__ value
        # (but may still appear in comments or elsewhere - we check the regex match)
        assert new_match.group(1) != current


@pytest.mark.parametrize(
    ("version_string", "should_match"),
    [
        ("1.0.0", True),
        ("2.0.0", True),
        ("0.1.0", True),
        ("10.20.30", True),
        ("1.0.0.dev1", True),
        ("2.0.0-rc1", True),
        ("1.0", False),          # missing PATCH
        ("1", False),            # only MAJOR
        ("1.0.0.0.0", True),     # extra segments - lenient regex still matches
        ("", False),
    ],
)
def test_semver_regex_parametrized(version_string: str, should_match: bool):
    """Verify SEMVER_RE accepts valid version strings and rejects invalid ones."""
    result = SEMVER_RE.match(version_string) is not None
    assert result == should_match, f"SEMVER_RE match({version_string!r}) expected {should_match}, got {result}"
