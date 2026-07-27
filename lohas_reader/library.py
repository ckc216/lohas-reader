"""Registry of novels available in the reader.

To add a novel, append an entry here with its novel543 ``book_id`` (the number
in the URL, e.g. ``https://www.novel543.com/0125682908/`` -> ``0125682908``).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LibraryEntry:
    book_id: str
    title: str
    author: str


LIBRARY: list[LibraryEntry] = [
    LibraryEntry(
        book_id="0125682908",
        title="男主都是戀愛腦，只有我是真修仙",
        author="晨光熹微",
    ),
]


def get_entry(book_id: str) -> LibraryEntry | None:
    return next((e for e in LIBRARY if e.book_id == book_id), None)
