"""GitHub URL validation tests."""

from __future__ import annotations

import pytest

from app.services.errors import InvalidGitHubUrlError
from app.services.github_service import canonicalize_github_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://github.com/OctoCat/Hello-World", "https://github.com/octocat/hello-world"),
        ("https://github.com/octocat/Hello-World.git", "https://github.com/octocat/hello-world"),
        ("https://www.github.com/octocat/Hello-World/", "https://github.com/octocat/hello-world"),
        ("https://GitHub.com/octocat/Hello-World.GIT", "https://github.com/octocat/hello-world"),
    ],
)
def test_valid_github_urls_are_canonicalized(raw: str, expected: str) -> None:
    parsed = canonicalize_github_url(raw)

    assert parsed.canonical_url == expected
    assert parsed.display_name == expected.removeprefix("https://github.com/")
    assert parsed.owner == "octocat"
    assert parsed.name == "hello-world"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "http://github.com/octocat/hello-world",
        "git@github.com:octocat/hello-world.git",
        "ssh://github.com/octocat/hello-world",
        "https://gitlab.com/octocat/hello-world",
        "https://github.com",
        "https://github.com/octocat",
        "https://github.com/octocat/hello-world/issues",
        "https://github.com/octocat/hello-world/tree/main",
        "https://github.com/octocat/hello-world?tab=readme",
        "https://github.com/octocat/hello-world#readme",
        "https://user:pass@github.com/octocat/hello-world",
        "https://github.com:443/octocat/hello-world",
        "https://github.com/-octocat/hello-world",
        "https://github.com/octocat-/hello-world",
        "https://github.com/own_er/hello-world",
        "https://github.com/octocat/../hello-world",
        "https://github.com/octocat/%2e%2e",
        "https://github.com/octocat/hello world",
        "https://github.com.evil.test/octocat/hello-world",
    ],
)
def test_invalid_github_urls_are_rejected(raw: str) -> None:
    with pytest.raises(InvalidGitHubUrlError):
        canonicalize_github_url(raw)


def test_url_longer_than_configured_limit_is_rejected() -> None:
    raw = "https://github.com/octocat/" + ("a" * 3000)
    with pytest.raises(InvalidGitHubUrlError):
        canonicalize_github_url(raw)
