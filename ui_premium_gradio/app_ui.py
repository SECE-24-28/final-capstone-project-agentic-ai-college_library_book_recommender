import os
import socket
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import gradio as gr
from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

load_dotenv(PROJECT_DIR / ".env")

from src import recommender as backend


MODEL_NAME = "llama-3.3-70b-versatile"
DATASET_PATH = PROJECT_DIR / "data" / "books.csv"
EMBEDDINGS_PATH = PROJECT_DIR / "models" / "book_embeddings.pkl"


def _find_free_port(start: int = 7861, limit: int = 20) -> int:
    for port in range(start, start + limit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def _book_value(book: Dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = book.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def _is_isbn(query: str) -> bool:
    cleaned = query.replace("-", "").replace(" ", "")
    return cleaned.isdigit() and len(cleaned) >= 8


def _format_book_lines(books: List[Dict[str, Any]]) -> str:
    lines = []
    for idx, book in enumerate(books[:5], start=1):
        title = _book_value(book, "title", default="Untitled")
        author = _book_value(book, "author", "authors", default="Unknown author")
        category = _book_value(book, "category", "categories", default="General")
        isbn = _book_value(book, "isbn", "isbn13", default="N/A")
        score = book.get("match_score", "")
        score_text = f" | match {float(score):.1f}%" if isinstance(score, (int, float)) else ""
        lines.append(f"{idx}. {title} by {author} ({category}) | ISBN {isbn}{score_text}")
    return "\n".join(lines)


def _results_table(books: List[Dict[str, Any]]) -> List[List[Any]]:
    rows = []
    for book in books:
        rows.append(
            [
                _book_value(book, "title", default="Untitled"),
                _book_value(book, "author", "authors", default="Unknown author"),
                _book_value(book, "category", "categories", default="General"),
                _book_value(book, "isbn", "isbn13", default=""),
                book.get("match_score", "100"),
            ]
        )
    return rows


def _fallback_recommendation_answer(query: str, books: List[Dict[str, Any]]) -> str:
    if not books:
        return (
            "I could not find a strong match in the books.csv dataset. "
            "Try a broader topic such as artificial intelligence, programming, history, or psychology."
        )

    answer = [f"I found {len(books)} matches from the local books.csv dataset for '{query}'."]
    answer.append("")
    for book in books[:3]:
        title = _book_value(book, "title", default="Untitled")
        author = _book_value(book, "author", "authors", default="Unknown author")
        category = _book_value(book, "category", "categories", default="General")
        score = book.get("match_score", 0)
        answer.append(f"- {title} by {author} ({category}) - match {score}%")
    answer.append("")
    answer.append("The Groq LLM is not connected right now, so I used the recommender's local fallback response.")
    return "\n".join(answer)


def _llm_chat_answer(query: str, books: List[Dict[str, Any]]) -> str:
    if backend.client is None:
        return _fallback_recommendation_answer(query, books)

    context = _format_book_lines(books)
    prompt = f"""
User request:
{query}

Books retrieved from books.csv:
{context}

Write a helpful chatbot reply for a college library user.
Use only the retrieved books.
Recommend the top 3 books, explain briefly why they fit, and mention ISBNs.
Keep the answer concise and natural.
"""
    try:
        response = backend.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a friendly college library chatbot connected to a book recommendation backend.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=350,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        fallback = _fallback_recommendation_answer(query, books)
        return f"{fallback}\n\nLLM note: Groq was configured, but the request failed: {exc}"


def _isbn_answer(query: str) -> Tuple[str, List[Dict[str, Any]]]:
    isbn = query.replace("-", "").replace(" ", "")
    book = backend.search_by_isbn(isbn)
    if not book:
        books = backend.recommend_books(query, top_n=5)
        return _llm_chat_answer(query, books), books

    title = _book_value(book, "title", default="this book")
    author = _book_value(book, "authors", "author", default="Unknown author")
    category = _book_value(book, "categories", "category", default="General")
    description = _book_value(book, "description", default="No description available.")
    summary = backend.summarize_book(book)
    answer = (
        f"I found this ISBN in books.csv.\n\n"
        f"**{title}** by {author}\n\n"
        f"Category: {category}\n\n"
        f"Description: {description[:650]}\n\n"
        f"{summary}"
    )
    return answer, [book]


def answer_question(message: str, history: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[List[Any]], str]:
    query = (message or "").strip()
    current_history = history or []

    if not query:
        return current_history, [], "Type a topic, title, author, or ISBN to search the connected dataset."

    try:
        if _is_isbn(query):
            answer, books = _isbn_answer(query)
        else:
            books = backend.recommend_books(query, top_n=5)
            answer = _llm_chat_answer(query, books)
    except Exception as exc:
        answer = f"Something went wrong while connecting the UI to the backend: {exc}"
        books = []

    updated_history = current_history + [
        {"role": "user", "content": query},
        {"role": "assistant", "content": answer},
    ]
    return updated_history, _results_table(books), ""


def _status_html() -> str:
    dataset_ok = DATASET_PATH.exists()
    embeddings_ok = EMBEDDINGS_PATH.exists()
    llm_ok = backend.client is not None
    book_count = len(getattr(backend, "df", []))

    def badge(label: str, ok: bool, detail: str) -> str:
        cls = "ok" if ok else "warn"
        state = "Connected" if ok else "Missing"
        return f"<span class='badge {cls}'><b>{label}</b>: {state} <small>{detail}</small></span>"

    return "".join(
        [
            badge("Dataset books.csv", dataset_ok, f"{book_count} books"),
            badge("Embeddings", embeddings_ok, "semantic search ready"),
            badge("Groq LLM", llm_ok, "key loaded from .env" if llm_ok else "set GROQ_API_KEY in .env"),
        ]
    )


def create_app() -> gr.Blocks:
    css = """
    :root { color-scheme: light; }
    body { background: #f5f7fb; color: #111827; }
    .gradio-container {
        max-width: 1040px !important;
        min-height: 100vh;
        margin: auto !important;
        padding: 18px 18px 24px !important;
    }
    .app-shell {
        max-width: 920px;
        margin: 0 auto;
        border: 1px solid #dbe3ef;
        border-radius: 8px;
        background: #ffffff;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
        overflow: hidden;
    }
    .app-header {
        padding: 16px 18px 10px;
        border-bottom: 1px solid #e5eaf2;
    }
    .app-title {
        margin: 0;
        font-size: 24px;
        line-height: 1.2;
        font-weight: 800;
    }
    .app-subtitle {
        margin: 6px 0 0;
        color: #5b6472;
        font-size: 14px;
        line-height: 1.45;
    }
    .status-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding: 0 18px 14px;
        border-bottom: 1px solid #e5eaf2;
        background: #ffffff;
    }
    .badge {
        border: 1px solid #d6dce7;
        border-radius: 999px;
        padding: 7px 10px;
        background: #f9fafb;
        font-size: 12px;
        line-height: 1;
        white-space: nowrap;
    }
    .badge small {
        color: #667085;
        margin-left: 4px;
    }
    .badge.ok {
        border-color: #b7dec4;
        background: #f0fff4;
    }
    .badge.warn {
        border-color: #f7cd8f;
        background: #fff8e8;
    }
    .chat-wrap {
        padding: 14px 18px 18px;
    }
    .chatbot {
        border: 1px solid #e1e7f0 !important;
        border-radius: 8px !important;
        background: #fbfcfe !important;
    }
    .input-row {
        align-items: stretch;
        gap: 8px;
        margin-top: 10px;
    }
    .input-row textarea {
        min-height: 48px !important;
        border-radius: 8px !important;
    }
    .input-row button {
        min-width: 92px;
        border-radius: 8px !important;
    }
    .results-box {
        margin-top: 10px;
    }
    @media (max-width: 760px) {
        .gradio-container { padding: 10px !important; }
        .app-title { font-size: 20px; }
        .app-header, .chat-wrap { padding-left: 12px; padding-right: 12px; }
        .status-row { padding-left: 12px; padding-right: 12px; }
        .badge { width: 100%; white-space: normal; }
    }
    footer { display: none !important; }
    """

    with gr.Blocks(title="College Library Chatbot", analytics_enabled=False) as demo:
        gr.HTML(f"<style>{css}</style>")
        with gr.Group(elem_classes=["app-shell"]):
            gr.HTML(
                """
                <div class="app-header">
                    <h1 class="app-title">College Library Chatbot</h1>
                    <p class="app-subtitle">
                        Ask for a topic, title, author, or ISBN. Replies are generated from your backend,
                        Groq API key, LLM, and local books.csv dataset.
                    </p>
                </div>
                """
            )
            gr.HTML(f"<div class='status-row'>{_status_html()}</div>")

            with gr.Column(elem_classes=["chat-wrap"]):
                chatbot = gr.Chatbot(
                    value=[
                        {
                            "role": "assistant",
                            "content": "Hi! Ask me for books, for example: AI for beginners, data structures, history, or an ISBN.",
                        }
                    ],
                    height=470,
                    label="Chat",
                    elem_classes=["chatbot"],
                )

                with gr.Row(elem_classes=["input-row"]):
                    message = gr.Textbox(
                        placeholder="Ask for recommendations or paste an ISBN...",
                        show_label=False,
                        scale=9,
                    )
                    send = gr.Button("Send", variant="primary", scale=1)

                status = gr.Markdown("")

                with gr.Accordion("Top books used from books.csv", open=False, elem_classes=["results-box"]):
                    results = gr.Dataframe(
                        headers=["Title", "Author", "Category", "ISBN", "Match"],
                        datatype=["str", "str", "str", "str", "str"],
                        row_count=5,
                        column_count=(5, "fixed"),
                        label=None,
                        interactive=False,
                    )

                clear = gr.Button("Clear chat")

        send.click(answer_question, inputs=[message, chatbot], outputs=[chatbot, results, status]).then(
            lambda: "", outputs=message
        )
        message.submit(answer_question, inputs=[message, chatbot], outputs=[chatbot, results, status]).then(
            lambda: "", outputs=message
        )
        clear.click(
            lambda: (
                [
                    {
                        "role": "assistant",
                        "content": "Chat cleared. What kind of book should we look for next?",
                    }
                ],
                [],
                "",
            ),
            outputs=[chatbot, results, status],
        )

    return demo


if __name__ == "__main__":
    app = create_app()
    app.queue()
    app.launch(server_name="127.0.0.1", server_port=_find_free_port(), show_error=True)
