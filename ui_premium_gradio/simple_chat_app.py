import os
import socket
import sys

import gradio as gr
from dotenv import load_dotenv
from groq import Groq

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from src.recommender import recommend_books, search_by_isbn

load_dotenv(os.path.join(PROJECT_DIR, ".env"))

MODEL_NAME = "llama-3.3-70b-versatile"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def _find_free_port(start: int = 7863, limit: int = 20) -> int:
    for port in range(start, start + limit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def answer_question(message: str, history):
    query = (message or "").strip()
    if not query:
        return "Type a book topic, author, title, or ISBN and I’ll help you find the best matches."

    if query.isdigit() and len(query) >= 8:
        book = search_by_isbn(query)
        if book:
            return (
                f"I found {book.get('title', 'this book')} by {book.get('authors', 'the author')}. "
                f"Category: {book.get('categories', 'General')}. "
                f"Description: {book.get('description', 'No description available.')}"
            )

    results = recommend_books(query, top_n=5)
    if not results:
        return "I could not find a good match for that request. Try a broader topic like 'AI', 'history', or 'programming'."

    context = "\n".join(
        f"{i}. {item.get('title', 'Untitled')} by {item.get('author', item.get('authors', 'Unknown author'))} "
        f"({item.get('category', item.get('categories', 'General'))}) — match {item.get('match_score', 0):.1f}%"
        for i, item in enumerate(results, start=1)
    )

    if client:
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a friendly college library assistant. Answer in concise, natural language and recommend the best books from the provided list.",
                    },
                    {
                        "role": "user",
                        "content": f"User asked: {query}\n\nRecommended books:\n{context}\n\nWrite a short, helpful reply in a warm chat style. Mention the top 3 most relevant books and why they fit.",
                    },
                ],
                temperature=0.7,
                max_tokens=220,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            pass

    lines = [f"I found {len(results)} smart matches for '{query}'."]
    for item in results[:3]:
        lines.append(
            f"• {item.get('title', 'Untitled')} by {item.get('author', item.get('authors', 'Unknown author'))} "
            f"({item.get('category', item.get('categories', 'General'))}) — match {item.get('match_score', 0):.1f}%"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    custom_css = """
    :root { color-scheme: dark; }
    body { background: radial-gradient(1000px 500px at 20% -10%, rgba(124, 92, 255, 0.15), transparent 50%), radial-gradient(900px 450px at 90% 10%, rgba(34, 211, 238, 0.1), transparent 50%), #090d16; font-family: Inter, Arial, sans-serif; }
    .gradio-container { max-width: 1200px; }
    .main { padding-top: 6px; }
    .panel { border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 24px; background: rgba(15, 23, 42, 0.45); box-shadow: 0 18px 40px rgba(0, 0, 0, 0.5); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); }
    .chatbot { border-radius: 20px !important; background: rgba(15, 23, 42, 0.3) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; }
    .message.user { background: linear-gradient(135deg, #7c5cff, #22d3ee) !important; border-radius: 18px 18px 4px 18px !important; color: #ffffff !important; }
    .message.bot { background: rgba(255, 255, 255, 0.05) !important; color: #f1f5f9 !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 18px 18px 18px 4px !important; box-shadow: 0 8px 18px rgba(0, 0, 0, 0.3) !important; }
    textarea, input { border-radius: 14px !important; background: rgba(255, 255, 255, 0.05) !important; color: #eff6ff !important; border: 1px solid rgba(255, 255, 255, 0.12) !important; }
    button.primary { background: linear-gradient(135deg, #7c5cff, #22d3ee) !important; border: none !important; color: white !important; }
    """

    with gr.Blocks(title="Library AI Assistant") as demo:
        gr.Markdown("""
        <div class='panel' style='padding:18px; margin-bottom:12px;'>
          <div style='font-size:28px; font-weight:900; color:#eff6ff;'>Library AI Assistant</div>
          <div style='color:#cbd5e1; margin-top:6px;'>Ask for book recommendations, topics, or ISBN lookup using the Groq model already configured in this project.</div>
        </div>
        """)
        chatbot = gr.Chatbot(
            value=[],
            height=430,
            elem_classes=["chatbot"]
        )
        msg = gr.Textbox(placeholder="Ask me for books, topics, or ISBN numbers...")
        with gr.Row():
            submit_btn = gr.Button("Send", variant="primary")
            clear_btn = gr.Button("Clear")

        def respond(message, history):
            if not message.strip():
                return history, ""
            answer = answer_question(message, history)
            updated = (history or []) + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": answer},
            ]
            return updated, ""

        submit_btn.click(respond, inputs=[msg, chatbot], outputs=[chatbot, msg]).then(lambda: None, None, None)
        msg.submit(respond, inputs=[msg, chatbot], outputs=[chatbot, msg])
        clear_btn.click(lambda: [], None, chatbot)

    demo.queue()
    demo.launch(server_name="127.0.0.1", server_port=_find_free_port(), show_error=True, css=custom_css, js="() => { document.body.classList.add('dark'); }")
