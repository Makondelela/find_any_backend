import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from search_config import slugify_term


def test_slugify_term_replaces_spaces_with_hyphen():
    assert slugify_term("Data Engineer") == "data-engineer"
    assert slugify_term("AI Engineer") == "ai-engineer"
    assert slugify_term("  Data   Engineer  ") == "data-engineer"


def test_slugify_term_removes_non_alphanumeric_characters():
    assert slugify_term("Cyber Security") == "cyber-security"
    assert slugify_term("AWS") == "aws"
