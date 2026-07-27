# 📖 lohas-reader

A small [Streamlit](https://streamlit.io) web-novel reader. Pick a book from the
library, browse its chapters, and the chapter text is scraped on demand from
[novel543.com](https://www.novel543.com) and shown right in the page.

### How to run it

Prerequisite: install [`uv`](https://docs.astral.sh/uv/).

```sh
uv sync                                # install dependencies
uv run streamlit run streamlit_app.py  # start the reader on http://localhost:8501
```

### Adding a novel

Edit `lohas_reader/library.py` and add a `LibraryEntry` with the book's
`book_id` — the number in its novel543 URL (e.g.
`https://www.novel543.com/0125682908/` → `0125682908`).

### Layout

- `streamlit_app.py` — UI and view routing (library → chapters → reading).
- `lohas_reader/scraper.py` — novel543 scraper (info, chapter list, content).
- `lohas_reader/library.py` — the list of available novels.
