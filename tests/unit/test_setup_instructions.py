"""Every dependency list this repository states twice states the same thing.

The Setup block in the README is the first command anybody runs here, and it
was installing `.[dev]` while the suite could not so much as collect without
`.[stand]`: `tests/stand/conftest.py` serves the stand with uvicorn,
`tests/stand/test_pages_contract.py` imports `selectolax`, and the
`local_stand` fixture in `tests/conftest.py` imports uvicorn and
`stand.app.main`. A first run that ends in a collection error is a first
impression nobody recovers from, so the extras a reader is told to install are
pinned against the extras `make install` uses -- the one install line in this
repository that is executed rather than read.

Superset rather than equality on purpose. The Makefile is what CI and the
maintainer run, so it is the floor; a README that told a reader to install
*more* than that (a future `docs` extra, say) is generous, not wrong. Less is
the failure this pin exists for.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: An editable install with extras, however it is spelled: `pip install`,
#: `python3 -m pip install`, quoted or not. The extras themselves are the
#: capture -- everything between the brackets.
INSTALL = re.compile(r"pip install\s+-e\s+[\"']?\.\[(?P<extras>[^\]]+)\][\"']?")


def _section(markdown: str, heading: str) -> str:
    """One `## ` section of a Markdown document, heading excluded."""
    start = markdown.find(heading)
    assert start != -1, f"the README no longer has a {heading!r} section"
    body = markdown[start + len(heading):]
    end = body.find("\n## ")
    return body if end == -1 else body[:end]


def _extras(command: str, source: str) -> tuple[str, set[str]]:
    """The extras one install command asks for, and the command as written."""
    match = INSTALL.search(command)
    assert match is not None, (
        f"{source} no longer contains an editable install with extras "
        f"(`pip install -e \".[...]\"`), which is what this pin compares. Either "
        f"the instructions changed shape -- fix INSTALL here -- or one of the two "
        f"stopped installing this project at all."
    )
    return match.group(0), {extra.strip() for extra in match["extras"].split(",")}


def test_the_readme_installs_at_least_what_make_install_does() -> None:
    """A reader who follows Setup can collect the suite; `make install` is the floor."""
    readme_line, readme_extras = _extras(
        _section((ROOT / "README.md").read_text(encoding="utf-8"), "## Setup"),
        "the README's Setup block",
    )
    make_line, make_extras = _extras(
        (ROOT / "Makefile").read_text(encoding="utf-8"),
        "the Makefile's install target",
    )
    assert make_extras <= readme_extras, (
        "the README's Setup block installs less than `make install` does, so a "
        "reader who follows it cannot even collect the suite:\n"
        f"  README:   {readme_line}\n"
        f"  Makefile: {make_line}\n"
        f"missing from the README: {sorted(make_extras - readme_extras)}"
    )


#: The one package in the `stand` extra that the stand itself does not need.
#: It parses HTML, and the thing that parses HTML is `tests/stand`, which
#: checks the shop's markup without a browser. The shop's own image has no
#: tests in it.
CONTRACT_ONLY = {"selectolax"}

#: One requirement line, with the version specifier left on: pinning the names
#: alone would let `uvicorn>=0.32` on one side and `uvicorn>=0.20` on the other
#: pass for the same list.
REQUIREMENT = re.compile(r"^\s*([^#\s].*?)\s*$")


def _requirements(path: Path) -> set[str]:
    """The requirement lines of a pip requirements file, comments and blanks out."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return {m.group(1) for m in map(REQUIREMENT.match, lines) if m}


def _distribution(requirement: str) -> str:
    """The package a requirement names, with the version specifier left off."""
    return re.split(r"[<>=!~\[;\s]", requirement, maxsplit=1)[0].strip().lower()


def test_the_stand_image_installs_the_stand_extra() -> None:
    """The stand's dependencies are written down twice, and must not drift apart.

    `pyproject.toml` has them because the suite starts the stand in its own
    process, and `stand/requirements.txt` has them because the stand's image is
    built without this project installed in it -- `stand/Dockerfile` copies the
    file, installs it and copies `stand/`, so the image stays small and stops
    depending on the framework it is under test for. Two lists mean two places
    to add a package and one place to forget it, and forgetting this one fails
    in a container at start-up rather than here.
    """
    extra = set(tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
                ["project"]["optional-dependencies"]["stand"])
    stated = _requirements(ROOT / "stand" / "requirements.txt")

    expected = {line for line in extra if _distribution(line) not in CONTRACT_ONLY}

    assert stated == expected, (
        "stand/requirements.txt and the `stand` extra in pyproject.toml disagree:\n"
        f"  in the extra, not in the file: {sorted(expected - stated)}\n"
        f"  in the file, not in the extra: {sorted(stated - extra)}\n"
        f"({', '.join(sorted(CONTRACT_ONLY))} is deliberately not in the file: it "
        "parses HTML for tests/stand, and the stand's image holds no tests.)"
    )
