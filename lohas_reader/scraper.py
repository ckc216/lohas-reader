"""Scraper for novel543.com.

Page layout (as of 2026-07):

* Book index   ``/{book_id}/``            -> title, author, synopsis
* Directory    ``/{book_id}/dir``         -> chapter list (newest first)
* Chapter      ``/{book_id}/{seq}_{n}.html``
                 A single chapter may be split across several pages; the
                 ``<h1>`` shows ``(cur/total)`` and page ``k`` lives at
                 ``/{book_id}/{seq}_{n}_{k}.html`` (page 1 has no suffix).

Each site should live in its own module so adding another source later is a
matter of writing a new scraper with the same three functions.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.novel543.com"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Be polite: brief pause between requests when walking many pages.
_REQUEST_DELAY = 0.5
_TIMEOUT = 15


@dataclass
class NovelInfo:
    book_id: str
    title: str
    author: str
    synopsis: str


@dataclass
class Chapter:
    index: int  # 1-based position in reading order
    title: str
    path: str  # site-relative, e.g. "/0125682908/8096_1.html"


def _get_soup(path: str) -> BeautifulSoup:
    url = path if path.startswith("http") else f"{BASE_URL}{path}"
    resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return BeautifulSoup(resp.text, "lxml")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# Boilerplate footer lines the site injects into the chapter body.
_NOISE = re.compile(r"溫馨提示|站內信|手機閱讀|章節報錯|加入書[籤簽]|請記住本站")


def _is_noise(text: str) -> bool:
    return bool(_NOISE.search(text))


def fetch_novel_info(book_id: str) -> NovelInfo:
    """Fetch title/author/synopsis from a book's index page."""
    soup = _get_soup(f"/{book_id}/")

    title_el = soup.select_one("h1.title")
    author_el = soup.select_one(".author")
    intro_el = soup.select_one(".intro")

    return NovelInfo(
        book_id=book_id,
        title=_clean(title_el.get_text()) if title_el else "",
        author=_clean(author_el.get_text()) if author_el else "",
        synopsis=intro_el.get_text("\n").strip() if intro_el else "",
    )


def fetch_chapters(book_id: str) -> list[Chapter]:
    """Return chapters in reading order (oldest first).

    The directory page mixes a "latest chapters" preview in with the full
    catalog and lists things newest-first, so DOM order is unreliable. Each
    chapter file is named ``{seq}_{n}.html`` with a monotonically increasing
    ``n``, so we dedupe by URL and sort by that number instead.
    """
    soup = _get_soup(f"/{book_id}/dir")

    seen: dict[str, str] = {}  # path -> title (first occurrence wins)
    for a in soup.select(f'.chaplist a[href*="/{book_id}/"]'):
        href = a.get("href", "")
        if not href or not re.search(r"_\d+\.html$", href):
            continue
        seen.setdefault(href, _clean(a.get_text()))

    def seq(path: str) -> int:
        m = re.search(r"_(\d+)\.html$", path)
        return int(m.group(1)) if m else 0

    ordered = sorted(seen.items(), key=lambda kv: seq(kv[0]))
    return [
        Chapter(index=i, title=title, path=path)
        for i, (path, title) in enumerate(ordered, start=1)
    ]


def _page_url(path: str, page: int) -> str:
    """Build the URL for page ``page`` (1-based) of a chapter.

    ``/{book_id}/8096_1.html`` -> page 2 is ``/{book_id}/8096_1_2.html``.
    """
    if page <= 1:
        return path
    return re.sub(r"\.html$", f"_{page}.html", path)


def _extract_page(soup: BeautifulSoup) -> tuple[list[str], int, int]:
    """Return (paragraphs, current_page, total_pages) for one chapter page."""
    content = soup.select_one(".content") or soup.select_one(".chapter-content")
    paragraphs: list[str] = []
    if content:
        # Drop ad blocks / scripts injected into the content body.
        for junk in content.select(".gadBlock, script, ins, .ad, .gg"):
            junk.decompose()
        for p in content.find_all("p"):
            text = _clean(p.get_text())
            if text and not _is_noise(text):
                paragraphs.append(text)

    cur, total = 1, 1
    heading = soup.select_one("h1")
    if heading:
        m = re.search(r"\((\d+)\s*/\s*(\d+)\)", heading.get_text())
        if m:
            cur, total = int(m.group(1)), int(m.group(2))
    return paragraphs, cur, total


def fetch_chapter_content(path: str) -> list[str]:
    """Fetch a full chapter as a list of paragraphs, following pagination."""
    soup = _get_soup(path)
    paragraphs, _, total = _extract_page(soup)

    for page in range(2, total + 1):
        time.sleep(_REQUEST_DELAY)
        page_soup = _get_soup(_page_url(path, page))
        more, _, _ = _extract_page(page_soup)
        paragraphs.extend(more)

    return paragraphs
