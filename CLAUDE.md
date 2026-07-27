# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

A Streamlit web-novel reader. Chapters are scraped **on demand** from novel543.com — nothing is stored locally.

- `streamlit_app.py` — UI + routing. Three views selected by `st.session_state` (`book_id`, `chapter`): library → chapter list → reading. Navigation goes through the `_go()` helper, which sets state and calls `st.rerun()`. Scraper calls are wrapped in `@st.cache_data` so back/forward navigation doesn't refetch.
- `lohas_reader/scraper.py` — the novel543 scraper, exposing `fetch_novel_info`, `fetch_chapters`, and `fetch_chapter_content`. A new source site would be a new module offering these same three functions.
- `lohas_reader/library.py` — `LIBRARY`, the hardcoded list of available novels. Add a book by appending a `LibraryEntry` with its `book_id` (the number in the novel543 URL).

### novel543 scraping notes (non-obvious)

- Chapter files are named `/{book_id}/{seq}_{n}.html`; a single chapter can span multiple pages (`..._n_2.html`, etc.), detected via the `(cur/total)` marker in the `<h1>`. `fetch_chapter_content` walks all pages.
- The directory page (`/{book_id}/dir`) mixes a "latest chapters" preview into the full catalog and lists newest-first, so `fetch_chapters` dedupes by URL and sorts by the numeric `_{n}` suffix rather than trusting DOM order.
- The page encoding is auto-detected (`resp.apparent_encoding`); content has ad blocks (`.gadBlock`) and footer boilerplate (`溫馨提示` etc.) that are stripped.

## Commands

Dependencies are managed with **uv** (`uv.lock` is committed). Python 3.14+ is required (`.python-version`, `requires-python = ">=3.14"`).

```sh
uv sync                                # install/sync dependencies into the venv
uv run streamlit run streamlit_app.py  # run the app locally (serves on port 8501)
uv add <package>                       # add a dependency (updates pyproject.toml + uv.lock)
```

There is no test suite, linter, or formatter configured yet.

## Environment notes

- The primary working directory is on Windows; the default shell is PowerShell (a Bash tool is also available). The `.devcontainer` / Codespaces setup and README use Linux (`sh`) commands — translate as needed.
- The devcontainer runs the app with `--server.enableCORS false --server.enableXsrfProtection false`; do not carry those flags into a real deployment.
