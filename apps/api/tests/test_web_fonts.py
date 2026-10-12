"""The web app's fonts ship with the build.

`next/font/google` downloads the font files from Google while `next build` runs. On 2026-10-12
that download failed twice in CI on commits that did not touch the layout — once on `main` itself
— and a production image that cannot be built without a third party's server is a deploy risk.
The fonts are now packages pinned by the lockfile (apps/web/src/app/layout.tsx); this scan keeps
a build-time or page-time fetch from a font host from coming back.
"""

from __future__ import annotations

import re
from pathlib import Path

_WEB = Path(__file__).resolve().parents[2] / "web"

# A loader that fetches at build time, or a font host named in source, styles or the CSP.
_FETCHED = re.compile(r"next/font/google|fonts\.googleapis\.com|fonts\.gstatic\.com")

_SCANNED = {".ts", ".tsx", ".css", ".mjs", ".js"}


def _sources() -> list[Path]:
    files = [p for p in (_WEB / "src").rglob("*") if p.suffix in _SCANNED]
    files.append(_WEB / "next.config.mjs")
    return files


def test_no_font_is_fetched_from_a_font_host() -> None:
    sources = _sources()
    assert len(sources) > 20, "the scan found too few files to mean anything"
    offenders = [
        f"{path.relative_to(_WEB)}: {match.group(0)}"
        for path in sources
        if (match := _FETCHED.search(path.read_text(encoding="utf-8")))
    ]
    assert not offenders, "a font is fetched from a third party: " + "; ".join(offenders)


def test_every_font_family_the_styles_name_first_is_imported_by_the_layout() -> None:
    """A family named in the tokens without its package falls back to a system font, silently."""
    layout = (_WEB / "src" / "app" / "layout.tsx").read_text(encoding="utf-8")
    tokens = (_WEB / "src" / "styles" / "tokens.css").read_text(encoding="utf-8")
    package_of = {
        "Inter Variable": "@fontsource-variable/inter/",
        "Archivo Variable": "@fontsource-variable/archivo/",
        "Hanken Grotesk Variable": "@fontsource-variable/hanken-grotesk/",
        "IBM Plex Mono": "@fontsource/ibm-plex-mono/",
    }
    # The first family of each font token that names a web font (a token whose first family is a
    # system font — the workspace's own monospace stack — names no package).
    first_families = re.findall(r'--font-[a-z]+:\s*"([^"]+)"', tokens)
    named = [family for family in first_families if family in package_of]
    assert sorted(set(named)) == sorted(package_of), first_families
    for family in named:
        assert f'import "{package_of[family]}' in layout, family
