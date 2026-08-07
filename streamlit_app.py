"""lohas-reader — read web novels scraped on demand from novel543.com."""

import streamlit as st
import streamlit.components.v1 as components

from lohas_reader import scraper
from lohas_reader.library import LIBRARY, get_entry

st.set_page_config(page_title="lohas-reader", page_icon="📖", layout="centered")

# Hide Streamlit's top chrome — the sticky header, its toolbar and the
# Community Cloud "Fork"/GitHub badge — so the full screen goes to the text.
# ``config.toml`` alone isn't enough: the badge is injected by the host, not by
# Streamlit's own toolbar. The header is what the default top padding leaves
# room for, so reclaim that too. A style-only ``st.html`` renders into the
# event container and takes up no space of its own.
st.html(
    """
    <style>
      header[data-testid="stHeader"],
      [data-testid="stToolbar"],
      [data-testid="stDecoration"] { display: none !important; }
      [data-testid="stMainBlockContainer"], .block-container {
        padding-top: 1.5rem !important;
      }
    </style>
    """
)

# Chapter list: how many buttons per row.
CHAPTER_COLS = 3


# --- Cached scraping wrappers -------------------------------------------------
# Cache network calls so navigating back and forth doesn't re-scrape.
@st.cache_data(show_spinner=False, ttl=3600)
def load_info(book_id: str):
    return scraper.fetch_novel_info(book_id)


@st.cache_data(show_spinner=False, ttl=3600)
def load_chapters(book_id: str):
    return scraper.fetch_chapters(book_id)


@st.cache_data(show_spinner=False, ttl=3600)
def load_content(path: str):
    return scraper.fetch_chapter_content(path)


# --- Navigation helpers -------------------------------------------------------
def _go(book_id: str | None, chapter: int | None):
    st.session_state.book_id = book_id
    st.session_state.chapter = chapter
    st.rerun()


def _scroll_to_top(anchor: str):
    """Scroll the reader back to the top (used when the chapter changes).

    Runs inside a zero-height component iframe rather than ``st.html``: the
    iframe's srcdoc carries *anchor*, so it reloads — and the script really
    re-executes — on every chapter, whereas an ``st.html`` block is updated in
    place and its script only runs on mount.

    A single ``scrollTo`` isn't enough either, because Streamlit restores the
    previous scroll offset after a rerun and element heights keep settling
    afterwards. So we pin the top for a short window, releasing as soon as the
    reader scrolls or clicks.
    """
    components.html(
        f"""
        <script>
          /* anchor:{anchor} */
          (function () {{
            const doc = window.parent.document;
            const scrollers = [
              doc.querySelector('[data-testid="stMain"]'),
              doc.querySelector('section.main'),
              doc.scrollingElement,
            ].filter(Boolean);
            const events = ['wheel', 'touchstart', 'keydown', 'mousedown'];
            let stop = false;
            function release() {{
              stop = true;
              events.forEach(e => doc.removeEventListener(e, release));
            }}
            events.forEach(
              e => doc.addEventListener(e, release, {{passive: true}}));
            const until = Date.now() + 1500;
            (function pin() {{
              if (stop) return;
              scrollers.forEach(el => {{ el.scrollTop = 0; }});
              window.parent.scrollTo(0, 0);
              if (Date.now() < until) requestAnimationFrame(pin);
              else release();
            }})();
          }})();
        </script>
        """,
        height=0,
    )


st.session_state.setdefault("book_id", None)
st.session_state.setdefault("chapter", None)


# --- Views --------------------------------------------------------------------
def view_library():
    st.title("📖 lohas-reader")
    st.caption("點選書籍開始閱讀")
    for entry in LIBRARY:
        with st.container(border=True):
            st.subheader(entry.title)
            st.write(f"作者：{entry.author}")
            if st.button("閱讀", key=f"open_{entry.book_id}", use_container_width=True):
                _go(entry.book_id, None)


def view_chapters(book_id: str):
    entry = get_entry(book_id)
    if st.button("← 返回書庫"):
        _go(None, None)

    with st.spinner("載入書籍資訊…"):
        info = load_info(book_id)
        chapters = load_chapters(book_id)

    st.title(info.title or (entry.title if entry else book_id))
    if info.author:
        st.caption(f"作者：{info.author}　·　共 {len(chapters)} 章")
    if info.synopsis:
        with st.expander("簡介"):
            st.write(info.synopsis)

    st.subheader("章節")

    # Jump straight to a chapter number.
    jump = st.columns([3, 1])
    target = jump[0].number_input(
        "跳到章節", min_value=1, max_value=len(chapters), value=1,
        label_visibility="collapsed",
    )
    if jump[1].button("前往", use_container_width=True):
        _go(book_id, int(target))

    # Sort order. ``chapters`` comes back in reading order; 反序 shows the
    # newest first. A deselected segmented control returns None, which falls
    # back to 正序.
    order = st.segmented_control(
        "排序", ["正序", "反序"], default="正序", key="ch_order",
        label_visibility="collapsed",
    )
    listing = list(reversed(chapters)) if order == "反序" else chapters

    # Render every chapter as rows of CHAPTER_COLS buttons. Titles already
    # carry their own number (e.g. "007：…"), so show them as-is.
    for i in range(0, len(listing), CHAPTER_COLS):
        row = st.columns(CHAPTER_COLS)
        for col, c in zip(row, listing[i:i + CHAPTER_COLS]):
            if col.button(c.title, key=f"ch_{c.index}", use_container_width=True):
                _go(book_id, c.index)

    st.caption(f"已顯示全部 {len(chapters)} 章")


def _nav_buttons(book_id: str, chapter_no: int, total: int, suffix: str):
    cols = st.columns([1, 1, 1])
    if cols[0].button("← 章節列表", key=f"list_{suffix}", use_container_width=True):
        _go(book_id, None)
    if cols[1].button(
        "上一章", key=f"prev_{suffix}",
        disabled=chapter_no <= 1, use_container_width=True,
    ):
        _go(book_id, chapter_no - 1)
    if cols[2].button(
        "下一章", key=f"next_{suffix}",
        disabled=chapter_no >= total, use_container_width=True,
    ):
        _go(book_id, chapter_no + 1)


def view_reading(book_id: str, chapter_no: int):
    chapters = load_chapters(book_id)
    if not (1 <= chapter_no <= len(chapters)):
        _go(book_id, None)
        return
    chapter = chapters[chapter_no - 1]

    _nav_buttons(book_id, chapter_no, len(chapters), suffix="top")

    st.header(chapter.title)
    with st.spinner("載入內文…"):
        paragraphs = load_content(chapter.path)
    for para in paragraphs:
        st.write(para)

    st.divider()
    _nav_buttons(book_id, chapter_no, len(chapters), suffix="bottom")

    # Jump to the top whenever we land on a chapter (e.g. after 下一章). Done
    # last, so the chapter is fully laid out before we reset the offset.
    _scroll_to_top(f"{book_id}:{chapter_no}")


# --- Router -------------------------------------------------------------------
book_id = st.session_state.book_id
chapter = st.session_state.chapter

if book_id is None:
    view_library()
elif chapter is None:
    view_chapters(book_id)
else:
    view_reading(book_id, chapter)
