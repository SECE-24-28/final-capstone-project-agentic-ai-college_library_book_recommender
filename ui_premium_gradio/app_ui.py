from __future__ import annotations

import html
import socket
import sys
from pathlib import Path
from typing import Any

import gradio as gr

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

if load_dotenv is not None:
    load_dotenv(PROJECT_DIR / ".env")

from src import recommender as backend


DATASET_PATH = PROJECT_DIR / "data" / "books_enhanced.csv"


def _find_free_port(start: int = 7861, limit: int = 20) -> int:
    for port in range(start, start + limit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def _book_value(book: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = book.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def _escape(value: Any) -> str:
    return html.escape(str(value or ""))


def _is_isbn(query: str) -> bool:
    cleaned = query.replace("-", "").replace(" ", "")
    return cleaned.isdigit() and len(cleaned) >= 8


def _split_terms(value: str, limit: int = 5) -> list[str]:
    terms = []
    for raw in str(value or "").replace("|", ";").replace(",", ";").split(";"):
        term = raw.strip()
        if term and term not in terms:
            terms.append(term)
    return terms[:limit]


def _availability_text(book: dict[str, Any]) -> str:
    copies = int(float(book.get("copies", 0) or 0))
    shelf = _book_value(book, "shelf", default="Not assigned")
    if copies > 0:
        return (
            f"Available Copies: {copies}\n"
            f"Shelf: {shelf}\n"
            "Can Borrow Today: YES"
        )
    borrowed = _book_value(book, "borrowed_count", default="0")
    expected = _book_value(book, "expected_return", default="Not scheduled")
    return (
        f"Available Copies: {copies}\n"
        f"Shelf: {shelf}\n"
        "Can Borrow Today: NO\n"
        f"Borrowed by: {borrowed} Students\n"
        f"Expected Return: {expected}"
    )


def _recommendation_markdown(query: str, books: list[dict[str, Any]]) -> str:
    if not books:
        return "No matching books found. Try a broader college topic."

    lines = [f"Recommended Books for: {query}", ""]
    for index, book in enumerate(books, start=1):
        lines.extend(
            [
                f"{index}. {_book_value(book, 'title', default='Untitled')}",
                f"Author: {_book_value(book, 'author', 'authors', default='Unknown author')}",
                f"Category: {_book_value(book, 'category', 'categories', default='General')}",
                f"Publisher: {_book_value(book, 'publisher', default='Unknown publisher')}",
                f"Year: {_book_value(book, 'year', default='')}",
                f"ISBN: {_book_value(book, 'isbn', 'isbn13', default='N/A')}",
                "",
                "Reason:",
                backend.explain_book(book, query),
                "",
                f"Match Score: {float(book.get('match_score', 0)):.0f}%",
                "",
                "Availability:",
                _availability_text(book),
                "",
            ]
        )
    return "\n".join(lines)


def _isbn_markdown(book: dict[str, Any]) -> str:
    title = _book_value(book, "title", default="Untitled")
    author = _book_value(book, "author", "authors", default="Unknown author")
    summary = backend.summarize_book(book)
    return "\n".join(
        [
            "Book Found:",
            title,
            "",
            "Authors:",
            author,
            "",
            summary,
            "",
            "Availability:",
            _availability_text(book),
        ]
    )


def _reason_html(book: dict[str, Any], query: str) -> str:
    reasons = backend.explain_book(book, query).splitlines()
    items = []
    for reason in reasons:
        clean = reason.replace("✓", "").replace("âœ“", "").strip()
        items.append(f"<li><span>&#10003;</span>{_escape(clean)}</li>")
    return "".join(items)


def _availability_html(book: dict[str, Any]) -> str:
    copies = int(float(book.get("copies", 0) or 0))
    shelf = _book_value(book, "shelf", default="Not assigned")
    if copies > 0:
        return (
            f"<p><b>Available Copies:</b> {_escape(copies)}</p>"
            f"<p><b>Shelf:</b> {_escape(shelf)}</p>"
            "<p><b>Can Borrow Today:</b> YES</p>"
        )
    return (
        f"<p><b>Available Copies:</b> {_escape(copies)}</p>"
        f"<p><b>Shelf:</b> {_escape(shelf)}</p>"
        "<p><b>Can Borrow Today:</b> NO</p>"
        f"<p><b>Borrowed by:</b> {_escape(_book_value(book, 'borrowed_count', default='0'))} Students</p>"
        f"<p><b>Expected Return:</b> {_escape(_book_value(book, 'expected_return', default='Not scheduled'))}</p>"
    )


def _book_card(book: dict[str, Any], index: int, query: str | None = None) -> str:
    score = float(book.get("match_score", 100) or 100)
    title = _book_value(book, "title", default="Untitled")
    author = _book_value(book, "author", "authors", default="Unknown author")
    category = _book_value(book, "category", "categories", default="General")
    topics = _split_terms(_book_value(book, "keywords", "table_of_contents"), 5)
    topic_html = "".join(f"<span>{_escape(topic)}</span>" for topic in topics)
    reason_html = _reason_html(book, query or title) if query else ""
    cover_url = book.get("image_url") or "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?auto=format&fit=crop&w=300&q=80"
    isbn = _book_value(book, 'isbn', 'isbn13', default='N/A')
    copies = int(float(book.get("copies", 0) or 0))
    disabled_attr = 'disabled="disabled"' if copies <= 0 else ''
    
    return f"""
    <article class="book-card" data-isbn="{_escape(isbn)}" data-index="{index}" data-query="{_escape(query or '')}" data-isbnmode="false">
        <div class="book-card-content">
            <div class="book-cover-wrapper">
                <img class="book-cover-img" src="{_escape(cover_url)}" alt="Cover of {_escape(title)}" loading="lazy" />
            </div>
            <div class="book-details">
                <div class="card-top">
                    <span class="rank">#{index}</span>
                    <span class="score">{score:.0f}% match</span>
                </div>
                <h3>{_escape(title)}</h3>
                <div class="meta">
                    <p><b>Author:</b> {_escape(author)}</p>
                    <p><b>Category:</b> {_escape(category)}</p>
                    <p><b>Publisher:</b> {_escape(_book_value(book, 'publisher', default='Unknown publisher'))}</p>
                    <p><b>Year:</b> {_escape(_book_value(book, 'year', default=''))}</p>
                    <p><b>ISBN:</b> {_escape(isbn)}</p>
                </div>
                <div class="tags">{topic_html}</div>
                <div class="reason"><h4>Reason</h4><ul>{reason_html}</ul></div>
                <div class="availability"><h4>Availability</h4>{_availability_html(book)}</div>
                <div class="card-actions">
                    <button class="card-action-btn borrow-btn" onclick="gradioCardAction('{_escape(isbn)}', 'borrow')" {disabled_attr}>Borrow</button>
                    <button class="card-action-btn return-btn" onclick="gradioCardAction('{_escape(isbn)}', 'return')">Return</button>
                </div>
            </div>
        </div>
    </article>
    """


def _isbn_card(book: dict[str, Any]) -> str:
    topics = _split_terms(_book_value(book, "keywords", "table_of_contents"), 6)
    audience = _split_terms(_book_value(book, "target_audience", default="College students"), 4)
    topic_html = "".join(f"<li>{_escape(topic)}</li>" for topic in topics)
    audience_html = "".join(f"<li>{_escape(person)}</li>" for person in audience)
    cover_url = book.get("image_url") or "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?auto=format&fit=crop&w=300&q=80"
    isbn = _book_value(book, 'isbn', 'isbn13', default='N/A')
    copies = int(float(book.get("copies", 0) or 0))
    disabled_attr = 'disabled="disabled"' if copies <= 0 else ''
    
    return f"""
    <article class="book-card isbn-card" data-isbn="{_escape(isbn)}" data-index="1" data-query="{_escape(isbn)}" data-isbnmode="true">
        <div class="book-card-content">
            <div class="book-cover-wrapper">
                <img class="book-cover-img" src="{_escape(cover_url)}" alt="Cover of {_escape(_book_value(book, 'title'))}" loading="lazy" />
            </div>
            <div class="book-details">
                <div class="card-top">
                    <span class="rank">ISBN</span>
                    <span class="score">{_escape(_book_value(book, 'difficulty_level', default='Intermediate'))}</span>
                </div>
                <h3>{_escape(_book_value(book, 'title', default='Untitled'))}</h3>
                <div class="meta">
                    <p><b>Authors:</b> {_escape(_book_value(book, 'author', 'authors', default='Unknown author'))}</p>
                    <p><b>Category:</b> {_escape(_book_value(book, 'category', 'categories', default='General'))}</p>
                    <p><b>Publisher:</b> {_escape(_book_value(book, 'publisher', default='Unknown publisher'))}</p>
                    <p><b>ISBN:</b> {_escape(isbn)}</p>
                </div>
                <p class="summary">{_escape(_book_value(book, 'description', default='No description available.'))}</p>
                <div class="two-col">
                    <div><h4>This book covers</h4><ul>{topic_html}</ul></div>
                    <div><h4>Recommended for</h4><ul>{audience_html}</ul></div>
                </div>
                <div class="availability"><h4>Availability</h4>{_availability_html(book)}</div>
                <div class="card-actions">
                    <button class="card-action-btn borrow-btn" onclick="gradioCardAction('{_escape(isbn)}', 'borrow')" {disabled_attr}>Borrow</button>
                    <button class="card-action-btn return-btn" onclick="gradioCardAction('{_escape(isbn)}', 'return')">Return</button>
                </div>
            </div>
        </div>
    </article>
    """


def _cards_html(books: list[dict[str, Any]], query: str | None = None, isbn_mode: bool = False) -> str:
    if not books:
        return "<div class='empty'>No books found. Try AI, data structures, civil engineering, MBA, or an ISBN.</div>"
    cards = [
        _isbn_card(book) if isbn_mode else _book_card(book, index, query)
        for index, book in enumerate(books, start=1)
    ]
    return "<div class='cards'>" + "".join(cards) + "</div>"


def _popular_rail_html() -> str:
    books = backend.recommend_books("", top_n=10)
    double_books = books + books
    items = []
    for b in double_books:
        cover_url = b.get("image_url") or "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?auto=format&fit=crop&w=300&q=80"
        items.append(f"""
        <div class="rail-item" style="background-image: url('{_escape(cover_url)}');" onclick="browseSubjectGradio('{_escape(b.get('title'))}')">
            <div class="rail-item-info">{_escape(b.get('title'))}</div>
        </div>
        """)
    return f"""
    <div class="panel-transparent">
        <h3>Trending Books</h3>
        <div class="image-rail-container">
            <div class="image-rail">
                {"".join(items)}
            </div>
        </div>
    </div>
    """


def answer_question(message: str, history: list[dict[str, str]]) -> tuple[list[dict[str, str]], str, str, list[dict[str, Any]]]:
    query = (message or "").strip()
    current_history = history or []

    if not query:
        return current_history, _cards_html([]), "Type a topic, title, author, or ISBN.", []

    try:
        if _is_isbn(query):
            book = backend.search_by_isbn(query)
            if not book:
                answer = "No book found for this ISBN in the local dataset or free ISBN APIs."
                books: list[dict[str, Any]] = []
                cards = _cards_html([])
            else:
                books = [book]
                answer = _isbn_markdown(book)
                cards = _cards_html(books, isbn_mode=True)
        else:
            from web_app import api_chat
            chat_result = api_chat(query, current_history)
            answer = chat_result.get("answer")
            books = chat_result.get("books", [])
            cards = _cards_html(books, query=query)
    except Exception as exc:
        answer = f"Something went wrong while connecting the UI to the backend: {exc}"
        books = []
        cards = _cards_html([])

    updated_history = current_history + [
        {"role": "user", "content": query},
        {"role": "assistant", "content": answer},
    ]
    return updated_history, cards, "", books


def update_borrow_return(isbn: str, action: str) -> tuple[str, str]:
    cleaned = (isbn or "").strip()
    if not cleaned:
        return "Enter an ISBN to borrow or return.", _cards_html([])

    if action == "borrow":
        ok, message, book = backend.borrow_book(cleaned)
    else:
        ok, message, book = backend.return_book(cleaned)

    status = ("Success: " if ok else "Notice: ") + message
    return status, _cards_html([book], isbn_mode=True) if book else _cards_html([])


def handle_card_action_gradio(isbn: str, action: str, current_books: list[dict[str, Any]] | None) -> tuple[str, str, list[dict[str, Any]]]:
    isbn = (isbn or "").strip()
    action = (action or "").strip()
    current_books_list = current_books or []
    if not isbn or isbn == "N/A":
        return "Invalid ISBN.", _cards_html(current_books_list), current_books_list

    if action == "borrow":
        ok, message, updated_book = backend.borrow_book(isbn)
    else:
        ok, message, updated_book = backend.return_book(isbn)

    status = ("Success: " if ok else "Notice: ") + message

    # Update the book in the current list
    updated_books = []
    if updated_book:
        for b in current_books_list:
            b_isbn = _book_value(b, "isbn", "isbn13", default="")
            target_isbn = _book_value(updated_book, "isbn", "isbn13", default="")
            if b_isbn and target_isbn and b_isbn == target_isbn:
                updated_book["match_score"] = b.get("match_score", 100)
                updated_books.append(updated_book)
            else:
                updated_books.append(b)
    else:
        updated_books = current_books_list

    is_isbn_mode = len(current_books_list) == 1 and _is_isbn(_book_value(current_books_list[0], 'isbn', 'isbn13', default=''))
    return status, _cards_html(updated_books, isbn_mode=is_isbn_mode), updated_books


def _status_html() -> str:
    dataset_ok = DATASET_PATH.exists()
    llm_ok = backend.client is not None
    book_count = len(getattr(backend, "df", []))

    def badge(label: str, ok: bool, detail: str) -> str:
        cls = "ok" if ok else "warn"
        state = "Connected" if ok else "Missing"
        return f"<span class='badge {cls}'><b>{label}</b>: {state} <small>{detail}</small></span>"

    return "".join(
        [
            badge("Enhanced CSV", dataset_ok, f"{book_count} books"),
            badge("Semantic Search", True, "TF-IDF scoring ready"),
            badge("Groq LLM", llm_ok, "key loaded" if llm_ok else "fallback summaries active"),
        ]
    )


def create_app() -> gr.Blocks:
    css = """
    :root { color-scheme: dark; }
    body {
        background: radial-gradient(1000px 500px at 20% -10%, rgba(124, 92, 255, 0.15), transparent 50%),
                    radial-gradient(900px 450px at 90% 10%, rgba(34, 211, 238, 0.1), transparent 50%),
                    #090d16;
        color: #e2e8f0;
    }
    .gradio-container {
        max-width: 1180px !important;
        min-height: 100vh;
        margin: auto !important;
        padding: 18px !important;
    }
    .app-shell {
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        background: rgba(15, 23, 42, 0.45);
        box-shadow: 0 18px 45px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        overflow: hidden;
    }
    .app-header {
        padding: 20px 24px 14px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        position: relative;
    }
    .app-header::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: linear-gradient(135deg, #7c5cff, #22d3ee);
    }
    .app-title { margin: 0; font-size: 26px; line-height: 1.2; font-weight: 800; color: #ffffff; }
    .app-subtitle { margin: 6px 0 0; color: #94a3b8; font-size: 14px; line-height: 1.5; }
    .status-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding: 12px 20px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .badge {
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 999px;
        padding: 7px 10px;
        background: rgba(255, 255, 255, 0.04);
        font-size: 12px;
        line-height: 1;
        white-space: nowrap;
        color: #cbd5e1;
    }
    .badge small { color: #94a3b8; margin-left: 4px; }
    .badge.ok { border-color: rgba(34, 197, 94, 0.3); background: rgba(34, 197, 94, 0.1); color: #4ade80; }
    .badge.warn { border-color: rgba(245, 158, 11, 0.3); background: rgba(245, 158, 11, 0.1); color: #fbbf24; }
    .workspace { padding: 16px 20px 20px; }
    .chatbot {
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        background: rgba(15, 23, 42, 0.3) !important;
        color: #f1f5f9 !important;
    }
    .input-row { align-items: stretch; gap: 8px; margin-top: 10px; }
    .input-row textarea {
        min-height: 48px !important;
        border-radius: 8px !important;
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        color: #fff !important;
    }
    .input-row textarea:focus {
        border-color: rgba(124, 92, 255, 0.6) !important;
    }
    .input-row button, button { border-radius: 8px !important; }
    .cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(285px, 1fr));
        gap: 12px;
        margin-top: 4px;
    }
    .book-card {
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.03);
        padding: 14px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        min-width: 0;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .book-card:hover {
        transform: translateY(-2px);
        border-color: rgba(124, 92, 255, 0.45);
        background: rgba(255, 255, 255, 0.06);
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(124, 92, 255, 0.15);
    }
    .card-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
    }
    .rank, .score {
        border-radius: 999px;
        padding: 5px 8px;
        font-size: 11px;
        font-weight: 700;
        background: rgba(124, 92, 255, 0.15);
        color: #c7d2fe;
        border: 1px solid rgba(124, 92, 255, 0.3);
        white-space: nowrap;
    }
    .score {
        background: rgba(34, 211, 238, 0.15);
        color: #22d3ee;
        border: 1px solid rgba(34, 211, 238, 0.3);
    }
    .book-card h3 {
        margin: 0 0 8px;
        font-size: 17px;
        line-height: 1.3;
        color: #ffffff;
    }
    .book-card h4 {
        margin: 12px 0 6px;
        font-size: 13px;
        line-height: 1.2;
        color: #cbd5e1;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding-bottom: 4px;
    }
    .meta p, .availability p, .summary {
        margin: 4px 0;
        color: #94a3b8;
        font-size: 13px;
        line-height: 1.45;
    }
    .meta p b { color: #cbd5e1; }
    .tags {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin: 10px 0 4px;
    }
    .tags span {
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 999px;
        padding: 4px 7px;
        background: rgba(255, 255, 255, 0.04);
        font-size: 12px;
        color: #cbd5e1;
    }
    .reason ul, .two-col ul {
        margin: 0;
        padding-left: 0;
        list-style: none;
    }
    .reason li, .two-col li {
        margin: 5px 0;
        font-size: 13px;
        line-height: 1.4;
        color: #cbd5e1;
        display: flex;
        align-items: flex-start;
        gap: 6px;
    }
    .reason li span {
        color: #22c55e;
        font-weight: 800;
        margin-right: 4px;
        flex-shrink: 0;
    }
    .availability {
        margin-top: 10px;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        padding-top: 8px;
    }
    .two-col {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
    }
    .empty {
        border: 1px dashed rgba(255, 255, 255, 0.15);
        border-radius: 8px;
        padding: 18px;
        color: #94a3b8;
        background: rgba(255, 255, 255, 0.02);
    }
    @media (max-width: 760px) {
        .gradio-container { padding: 10px !important; }
        .app-title { font-size: 20px; }
        .app-header, .workspace, .status-row { padding-left: 12px; padding-right: 12px; }
        .badge { width: 100%; white-space: normal; }
        .two-col { grid-template-columns: 1fr; }
    }
    footer { display: none !important; }

    /* Moving Image Rail */
    .panel-transparent {
        margin-bottom: 24px;
    }
    .panel-transparent h3 {
        font-size: 20px;
        margin-bottom: 12px;
        color: #fff;
    }
    .image-rail-container {
        overflow: hidden;
        white-space: nowrap;
        padding: 12px 0;
        background: rgba(15, 23, 42, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        position: relative;
    }
    .image-rail {
        display: inline-flex;
        animation: marquee 45s linear infinite;
        gap: 16px;
    }
    .image-rail:hover {
        animation-play-state: paused;
    }
    .rail-item {
        width: 140px;
        height: 200px;
        flex-shrink: 0;
        border-radius: 10px;
        background-size: cover;
        background-position: center;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }
    .rail-item:hover {
        transform: translateY(-4px) scale(1.03);
        border-color: rgba(124, 92, 255, 0.6);
        box-shadow: 0 12px 24px rgba(0,0,0,0.5), 0 0 15px rgba(124,92,255,0.2);
    }
    .rail-item-info {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(180deg, transparent, rgba(0,0,0,0.95));
        padding: 10px 8px;
        font-size: 11px;
        color: #fff;
        white-space: normal;
        font-weight: 500;
        text-align: center;
        text-shadow: 0 1px 2px rgba(0,0,0,0.8);
        opacity: 0.85;
        transition: opacity 0.2s ease;
    }
    .rail-item:hover .rail-item-info {
        opacity: 1;
    }
    @keyframes marquee {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }
    /* Subject Browse Grid */
    .subject-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        margin-top: 16px;
    }
    .subject-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 20px;
        cursor: pointer;
        transition: all 0.25s ease;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
    }
    .subject-card:hover {
        background: rgba(255, 255, 255, 0.05);
        border-color: rgba(124, 92, 255, 0.4);
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    }
    .subject-icon {
        font-size: 28px;
        margin-bottom: 12px;
        background: rgba(124, 92, 255, 0.1);
        width: 48px;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 10px;
        border: 1px solid rgba(124, 92, 255, 0.2);
    }
    .subject-card h4 {
        margin: 0 0 6px !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #fff !important;
        border-bottom: none !important;
        padding-bottom: 0 !important;
    }
    .subject-card p {
        margin: 0 !important;
        color: var(--text-muted) !important;
        font-size: 12.5px !important;
        line-height: 1.4 !important;
    }
    /* Premium Cards Styling with Covers */
    .book-card-content {
        display: flex;
        gap: 18px;
    }
    .book-cover-wrapper {
        width: 105px;
        height: 155px;
        flex-shrink: 0;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.5);
        background: #111422;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .book-cover-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.3s ease;
    }
    .book-card:hover .book-cover-img {
        transform: scale(1.05);
    }
    .book-details {
        flex: 1;
        min-width: 0;
    }
    .card-actions {
        margin-top: 16px;
        display: flex;
        gap: 10px;
    }
    .book-card .card-actions .card-action-btn {
        flex: 1;
        min-height: 38px;
        border-radius: 8px !important;
        font-size: 13.5px;
        font-weight: 600;
        cursor: pointer;
        border: 1px solid transparent !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        font-family: inherit;
    }
    .book-card .card-actions .card-action-btn.borrow-btn {
        background: linear-gradient(135deg, #7c5cff, #4f46e5) !important;
        border: 1px solid rgba(124, 92, 255, 0.3) !important;
        color: #fff !important;
    }
    .book-card .card-actions .card-action-btn.borrow-btn:hover:not(:disabled) {
        background: linear-gradient(135deg, #906ffa, #6366f1) !important;
        box-shadow: 0 0 15px rgba(124, 92, 255, 0.35) !important;
        transform: translateY(-1px) !important;
    }
    .book-card .card-actions .card-action-btn.borrow-btn:disabled {
        background: rgba(255, 255, 255, 0.05) !important;
        border-color: rgba(255, 255, 255, 0.05) !important;
        color: rgba(255, 255, 255, 0.2) !important;
        cursor: not-allowed;
        transform: none !important;
        box-shadow: none !important;
    }
    .book-card .card-actions .card-action-btn.return-btn {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #cbd5e1 !important;
    }
    .book-card .card-actions .card-action-btn.return-btn:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        color: #fff !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
    }
    @keyframes card-pulse {
        0% {
            box-shadow: 0 0 0 0px rgba(124, 92, 255, 0.6);
            border-color: rgba(124, 92, 255, 0.8);
            transform: translateY(-2px) scale(1.01);
        }
        50% {
            transform: translateY(-2px) scale(1.01);
        }
        100% {
            box-shadow: 0 0 0 12px rgba(124, 92, 255, 0);
            border-color: rgba(255, 255, 255, 0.08);
            transform: translateY(0) scale(1);
        }
    }
    .book-card.card-updated {
        animation: card-pulse 1s cubic-bezier(0.25, 0.8, 0.25, 1) forwards !important;
    }
    """

    with gr.Blocks(title="College Library Recommender", analytics_enabled=False) as demo:
        search_results_state = gr.State([])

        gr.HTML(f"<style>{css}</style><script>function browseSubjectGradio(subjectName) {{ const inputEl = document.querySelector('#agent_message_input textarea, #agent_message_input input'); if (inputEl) {{ inputEl.value = subjectName; inputEl.dispatchEvent(new Event('input', {{ bubbles: true }})); }} const tabButtons = Array.from(document.querySelectorAll('button')); const agentTabButton = tabButtons.find(btn => btn.textContent && btn.textContent.trim().includes('Library AI Agent')); if (agentTabButton) {{ agentTabButton.click(); }} setTimeout(() => {{ const searchBtn = document.querySelector('#agent_search_btn'); if (searchBtn) {{ searchBtn.click(); }} }}, 150); }} function gradioCardAction(isbn, action) {{ const isbnInput = document.querySelector('#gradio_card_action_isbn input, #gradio_card_action_isbn textarea'); const actionInput = document.querySelector('#gradio_card_action_type input, #gradio_card_action_type textarea'); const btn = document.querySelector('#gradio_card_action_btn'); if (isbnInput && actionInput && btn) {{ isbnInput.value = isbn; isbnInput.dispatchEvent(new Event('input', {{ bubbles: true }})); actionInput.value = action; actionInput.dispatchEvent(new Event('input', {{ bubbles: true }})); setTimeout(() => {{ btn.click(); setTimeout(() => {{ const card = document.querySelector('article.book-card[data-isbn=\"' + isbn + '\"]'); if (card) {{ card.classList.add('card-updated'); }} }}, 800); }}, 100); }} }}</script>")
        with gr.Group(elem_classes=["app-shell"]):
            gr.HTML(
                """
                <div class="app-header">
                    <h1 class="app-title">College Library Book Recommender</h1>
                    <p class="app-subtitle">
                        Enter a topic, book name, author, or ISBN to get explainable recommendations,
                        ISBN knowledge retrieval, and live library availability.
                    </p>
                </div>
                """
            )
            gr.HTML(f"<div class='status-row'>{_status_html()}</div>")
            with gr.Tabs():
                with gr.Tab("Home Dashboard"):
                    gr.HTML(_popular_rail_html())
                    gr.HTML(
                        """
                        <div class="panel" style="margin-top: 16px;">
                            <h3>Browse by Subject</h3>
                            <div class="subject-grid">
                                <div class="subject-card" onclick="browseSubjectGradio('Artificial Intelligence')">
                                    <div class="subject-icon">🤖</div>
                                    <h4>Artificial Intelligence</h4>
                                    <p>Neural networks, machine learning, NLP, and intelligent agents.</p>
                                </div>
                                <div class="subject-card" onclick="browseSubjectGradio('Programming')">
                                    <div class="subject-icon">💻</div>
                                    <h4>Programming</h4>
                                    <p>Python, Java, C++, OOP, and data structures.</p>
                                </div>
                                <div class="subject-card" onclick="browseSubjectGradio('Database Systems')">
                                    <div class="subject-icon">🗄️</div>
                                    <h4>Database Systems</h4>
                                    <p>SQL, NoSQL, query optimization, and transaction management.</p>
                                </div>
                                <div class="subject-card" onclick="browseSubjectGradio('Business & MBA')">
                                    <div class="subject-icon">📊</div>
                                    <h4>Business & MBA</h4>
                                    <p>Management, finance, operations, and strategic marketing.</p>
                                </div>
                                <div class="subject-card" onclick="browseSubjectGradio('Cybersecurity')">
                                    <div class="subject-icon">🛡️</div>
                                    <h4>Cybersecurity</h4>
                                    <p>Cryptography, ethical hacking, and network security protocols.</p>
                                </div>
                                <div class="subject-card" onclick="browseSubjectGradio('Mathematics')">
                                    <div class="subject-icon">📐</div>
                                    <h4>Mathematics</h4>
                                    <p>Linear algebra, calculus, discrete math, and probability.</p>
                                </div>
                            </div>
                        </div>
                        """
                    )
                with gr.Tab("Library AI Agent"):
                    with gr.Column(elem_classes=["workspace"]):
                        chatbot = gr.Chatbot(
                            value=[
                                {
                                    "role": "assistant",
                                    "content": "Enter a book name, topic, author, or ISBN. Example: AI, data structures, MBA finance, or 9781484284803.",
                                }
                            ],
                            height=390,
                            label="Response Output",
                            elem_classes=["chatbot"],
                        )
                        with gr.Row(elem_classes=["input-row"]):
                            message = gr.Textbox(
                                placeholder="Enter a book name or ISBN...",
                                show_label=False,
                                scale=8,
                                elem_id="agent_message_input",
                            )
                            send = gr.Button("Search", variant="primary", scale=1, elem_id="agent_search_btn")

                        status = gr.Markdown("")
                        cards = gr.HTML(_cards_html([]), label="Recommendation Cards")

                        # Hidden fields for programmatic card actions
                        card_action_isbn = gr.Textbox(visible=False, elem_id="gradio_card_action_isbn")
                        card_action_type = gr.Textbox(visible=False, elem_id="gradio_card_action_type")
                        card_action_btn = gr.Button(visible=False, elem_id="gradio_card_action_btn")

                        with gr.Accordion("Borrow / Return by ISBN", open=True):
                            with gr.Row(elem_classes=["input-row"]):
                                library_isbn = gr.Textbox(
                                    placeholder="ISBN for borrow or return...",
                                    show_label=False,
                                    scale=6,
                                )
                                borrow = gr.Button("Borrow", variant="primary", scale=1)
                                return_btn = gr.Button("Return", scale=1)
                            library_status = gr.Markdown("")

                        clear = gr.Button("Clear")

        send.click(answer_question, inputs=[message, chatbot], outputs=[chatbot, cards, status, search_results_state]).then(
            lambda: "", outputs=message
        )
        message.submit(answer_question, inputs=[message, chatbot], outputs=[chatbot, cards, status, search_results_state]).then(
            lambda: "", outputs=message
        )
        borrow.click(
            lambda isbn: update_borrow_return(isbn, "borrow"),
            inputs=library_isbn,
            outputs=[library_status, cards],
        )
        return_btn.click(
            lambda isbn: update_borrow_return(isbn, "return"),
            inputs=library_isbn,
            outputs=[library_status, cards],
        )
        card_action_btn.click(
            handle_card_action_gradio,
            inputs=[card_action_isbn, card_action_type, search_results_state],
            outputs=[library_status, cards, search_results_state],
        )
        clear.click(
            lambda: (
                [
                    {
                        "role": "assistant",
                        "content": "Cleared. Enter a topic, title, author, or ISBN to search again.",
                    }
                ],
                _cards_html([]),
                "",
                "",
                [],
            ),
            outputs=[chatbot, cards, status, library_status, search_results_state],
        )

    return demo


if __name__ == "__main__":
    app = create_app()
    app.queue()
    app.launch(server_name="127.0.0.1", server_port=_find_free_port(), show_error=True, js="() => { document.body.classList.add('dark'); }")
