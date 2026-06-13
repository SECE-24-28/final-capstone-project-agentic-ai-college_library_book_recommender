from __future__ import annotations

import json
import socket
import urllib.parse
import urllib.request
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from src import recommender as backend


PROJECT_DIR = Path(__file__).resolve().parent
DATASET_PATH = PROJECT_DIR / "data" / "books_enhanced.csv"
LIBRARY_NAME = "Aster Hall Library"


def borrow_or_return(isbn: str, action: str):
    if action == "borrow":
        return backend.borrow_book(isbn)
    else:
        return backend.return_book(isbn)


def api_search(query: str):
    query = query.strip()
    if not query:
        return {"mode": "empty", "books": []}
    if query.replace("-", "").replace(" ", "").isdigit() and len(query.replace("-", "").replace(" ", "")) >= 8:
        book = backend.search_by_isbn(query)
        return {"mode": "isbn", "books": [book] if book else []}
    return {"mode": "recommend", "books": backend.recommend_books(query)}


def api_chat(message: str, history: list[dict[str, str]]):
    query = (message or "").strip()
    if not query:
        return {
            "answer": "Type a book topic, author, title, or ISBN and I’ll help you find the best matches.",
            "books": []
        }

    if query.replace("-", "").replace(" ", "").isdigit() and len(query.replace("-", "").replace(" ", "")) >= 8:
        book = backend.search_by_isbn(query)
        if book:
            return {
                "answer": f"I found the book **{book.get('title')}** by {book.get('author')}. The details are shown in the card below.",
                "books": [book]
            }
        else:
            return {
                "answer": "I couldn't find any book matching that ISBN in the library database or external APIs.",
                "books": []
            }

    results = backend.recommend_books(query, top_n=5)

    if backend.client is not None:
        context = "\n".join(
            f"{i}. '{item.get('title')}' by {item.get('author')} (Category: {item.get('category')}) "
            f"— Match: {item.get('match_score', 0):.1f}%, Shelf: {item.get('shelf', 'Not assigned')}, "
            f"Available Copies: {item.get('copies', 0)} of {item.get('total_copies', 0)}, "
            f"Description: {item.get('description', '')[:150]}..."
            for i, item in enumerate(results, start=1)
        )
        prompt = f"""
You are a friendly college library assistant. Respond to the student query in a natural, helpful conversational tone.
Explain the reasoning for choosing each of the top 5 recommended books below.

Student Query: {query}

Recommended Books (Top 5):
{context}

Response guidelines:
- For each book, provide a very brief, friendly sentence explaining why it was chosen / how it matches the query.
- Make sure to explicitly include its library location (Shelf number) and the number of available copies.
- Keep the reasoning for each book very concise and clear.
- Maintain a warm, encouraging tone.
"""
        try:
            response = backend.client.chat.completions.create(
                model=backend.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=500,
            )
            answer = response.choices[0].message.content.strip()
            return {"answer": answer, "books": results}
        except Exception:
            pass

    if not results:
        return {
            "answer": f"I couldn't find any books covering '{query}'. Try search terms like 'AI', 'Algorithms', 'Java', or 'MBA'.",
            "books": []
        }

    return {
        "answer": f"I found {len(results)} relevant books for '{query}' in our library. The recommendation cards have been updated below!",
        "books": results
    }


INDEX_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>College Library Book Recommender</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    * { box-sizing: border-box; }
    
    :root {
      color-scheme: dark;
      --bg-gradient: radial-gradient(1000px 500px at 20% -10%, rgba(124, 92, 255, 0.15), transparent 50%),
                     radial-gradient(900px 450px at 90% 10%, rgba(34, 211, 238, 0.1), transparent 50%),
                     #090d16;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --text-accent: #38bdf8;
      --card-bg: rgba(255, 255, 255, 0.03);
      --card-border: rgba(255, 255, 255, 0.07);
      --card-border-hover: rgba(124, 92, 255, 0.4);
      --shadow-primary: 0 10px 40px rgba(0, 0, 0, 0.5);
      --shadow-glow: 0 0 20px rgba(124, 92, 255, 0.15);
      --primary-gradient: linear-gradient(135deg, #7c5cff, #22d3ee);
      --secondary-gradient: linear-gradient(135deg, #334155, #1e293b);
      --accent-gradient: linear-gradient(135deg, #22c55e, #10b981);
    }

    body {
      margin: 0;
      font-family: 'Outfit', sans-serif;
      background: var(--bg-gradient);
      color: var(--text-main);
      min-height: 100vh;
      -webkit-font-smoothing: antialiased;
      display: flex;
      flex-direction: column;
    }

    /* Navigation Bar */
    .nav-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 40px;
      background: rgba(15, 23, 42, 0.6);
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .nav-bar .logo {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .nav-bar .logo .icon {
      font-size: 24px;
    }

    .nav-bar .logo .title {
      font-size: 20px;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: var(--primary-gradient);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .nav-links {
      display: flex;
      gap: 12px;
    }

    .nav-btn {
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 14.5px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: none;
      transition: all 0.2s ease;
    }

    .nav-btn:hover {
      color: #fff;
      background: rgba(255,255,255,0.05);
      border-color: rgba(255,255,255,0.08);
      transform: none;
      box-shadow: none;
    }

    .nav-btn.active {
      color: #fff;
      background: rgba(124, 92, 255, 0.15);
      border: 1px solid rgba(124, 92, 255, 0.3);
    }

    .shell {
      max-width: 1200px;
      width: 100%;
      margin: 0 auto;
      padding: 24px;
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    .page-content {
      animation: fadeIn 0.3s ease-in-out;
      width: 100%;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }

    header, .panel {
      background: rgba(15, 23, 42, 0.45);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      box-shadow: var(--shadow-primary);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      padding: 24px;
      margin-bottom: 24px;
    }

    header {
      padding: 30px 40px;
      position: relative;
      overflow: hidden;
    }

    header::before {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 3px;
      background: var(--primary-gradient);
    }

    h1 {
      margin: 0;
      font-size: 36px;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #ffffff, #94a3b8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .sub {
      margin: 10px 0 0;
      color: var(--text-muted);
      line-height: 1.6;
      font-size: 15px;
    }

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
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
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
      margin: 0 0 6px;
      font-size: 16px;
      font-weight: 700;
      color: #fff;
      border-bottom: none;
      padding-bottom: 0;
    }

    .subject-card p {
      margin: 0;
      color: var(--text-muted);
      font-size: 12.5px;
      line-height: 1.4;
    }

    /* Agent Horizontal Layout with Sidebar */
    .agent-layout {
      display: flex;
      gap: 24px;
      min-height: 600px;
      align-items: stretch;
    }

    .sidebar {
      width: 260px;
      flex-shrink: 0;
      background: rgba(15, 23, 42, 0.55);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
    }

    .btn-new-chat {
      background: linear-gradient(135deg, rgba(124, 92, 255, 0.25), rgba(34, 211, 238, 0.15));
      border: 1px dashed rgba(124, 92, 255, 0.5);
      color: #fff;
      padding: 12px;
      border-radius: 10px;
      cursor: pointer;
      font-weight: 600;
      font-size: 14.5px;
      text-align: center;
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .btn-new-chat:hover {
      background: rgba(124, 92, 255, 0.35);
      border-color: #22d3ee;
      transform: translateY(-1px);
    }

    .conversation-list {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding-right: 4px;
    }

    .conversation-item {
      padding: 12px 14px;
      border-radius: 10px;
      cursor: pointer;
      font-size: 14px;
      color: var(--text-muted);
      transition: all 0.2s ease;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border: 1px solid transparent;
      background: rgba(255, 255, 255, 0.01);
    }

    .conversation-item:hover {
      background: rgba(255, 255, 255, 0.05);
      color: #fff;
    }

    .conversation-item.active {
      background: rgba(124, 92, 255, 0.18);
      border-color: rgba(124, 92, 255, 0.35);
      color: #fff;
      font-weight: 600;
    }

    .conversation-item .delete-chat-btn {
      opacity: 0;
      background: transparent;
      border: none;
      color: #ef4444;
      cursor: pointer;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
      transition: opacity 0.2s ease;
    }

    .conversation-item:hover .delete-chat-btn {
      opacity: 0.8;
    }

    .conversation-item .delete-chat-btn:hover {
      opacity: 1;
      background: rgba(239, 68, 68, 0.15);
    }

    .main-chat-area {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 24px;
      min-width: 0;
    }

    .chat-panel {
      width: 100%;
      min-width: 0;
      display: flex;
      flex-direction: column;
      background: rgba(15, 23, 42, 0.45);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      box-shadow: var(--shadow-primary);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      overflow: hidden;
    }

    @media (max-width: 900px) {
      .agent-layout {
        flex-direction: column;
      }
      .sidebar {
        width: 100%;
      }
    }

    .chat-header {
      padding: 16px 20px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .chat-header h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
    }

    .btn-clear {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #ef4444;
      font-size: 12px;
      padding: 5px 10px;
      border-radius: 6px;
      min-height: auto;
      font-weight: 600;
      box-shadow: none;
      transition: all 0.2s ease;
    }

    .btn-clear:hover {
      background: rgba(239, 68, 68, 0.2);
      border-color: rgba(239, 68, 68, 0.4);
      transform: none;
      box-shadow: none;
    }

    .chat-messages {
      height: 320px;
      padding: 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .chat-bubble {
      max-width: 85%;
      padding: 12px 16px;
      border-radius: 12px;
      font-size: 13.5px;
      line-height: 1.5;
    }

    .chat-bubble p {
      margin: 4px 0;
    }

    .chat-bubble ul, .chat-bubble ol {
      padding-left: 18px;
      margin: 6px 0;
    }

    .chat-bubble li {
      margin: 4px 0;
      display: list-item;
    }

    .chat-bubble.user {
      align-self: flex-end;
      background: var(--primary-gradient);
      color: #fff;
      border-bottom-right-radius: 2px;
    }

    .chat-bubble.agent {
      align-self: flex-start;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: #cbd5e1;
      border-bottom-left-radius: 2px;
    }

    .chat-input-area {
      padding: 16px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      gap: 8px;
      background: rgba(15, 23, 42, 0.2);
    }

    .chat-input-area input {
      flex: 1;
      min-height: 40px;
      border-radius: 8px;
    }

    .chat-input-area button {
      min-height: 40px;
      padding: 0 16px;
      border-radius: 8px;
    }

    .results-panel {
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding-right: 0;
    }

    .panel-header-sticky {
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 16px 20px;
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      position: sticky;
      top: 0;
      z-index: 50;
    }

    .panel-header-sticky h3 {
      margin: 0 0 12px;
      font-size: 18px;
    }

    .search-row-mini {
      display: flex;
      gap: 8px;
    }

    .search-row-mini input {
      min-height: 38px;
      font-size: 14px;
      border-radius: 8px;
    }

    .search-row-mini button {
      min-height: 38px;
      font-size: 14px;
      padding: 0 16px;
      border-radius: 8px;
    }

    .panel-nested {
      background: rgba(255,255,255,0.02);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 12px;
      padding: 16px;
    }

    .panel-nested h3 {
      font-size: 16px;
      margin-bottom: 10px;
      color: #fff;
    }

    .library-status-msg {
      margin-top: 10px;
      color: var(--text-accent);
      font-size: 13px;
      font-weight: 500;
    }

    /* Premium Cards Styling with Covers */
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 20px;
      margin-bottom: 24px;
    }

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

    /* Beautiful Dynamic HTML Book Covers */
    .html-book-cover {
      width: 100%;
      height: 100%;
      padding: 12px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      color: #fff;
      position: relative;
      overflow: hidden;
      box-sizing: border-box;
      font-family: 'Outfit', sans-serif;
      text-align: left;
    }

    .html-book-cover-bg {
      position: absolute;
      inset: 0;
      z-index: 1;
      transition: transform 0.4s ease;
    }

    .book-card:hover .html-book-cover-bg,
    .rail-item:hover .html-book-cover-bg {
      transform: scale(1.08);
    }

    .cover-pattern {
      position: absolute;
      right: -10px;
      bottom: -15px;
      font-size: 78px;
      opacity: 0.12;
      pointer-events: none;
      z-index: 2;
    }

    .cover-header {
      font-size: 8px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      font-weight: 700;
      color: rgba(255, 255, 255, 0.7);
      z-index: 2;
      position: relative;
    }

    .cover-title {
      font-size: 13px;
      font-weight: 750;
      line-height: 1.3;
      margin: auto 0;
      display: -webkit-box;
      -webkit-line-clamp: 4;
      -webkit-box-orient: vertical;
      overflow: hidden;
      text-overflow: ellipsis;
      text-shadow: 0 2px 4px rgba(0,0,0,0.35);
      z-index: 2;
      position: relative;
    }

    .cover-footer {
      font-size: 9px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.85);
      border-top: 1px solid rgba(255, 255, 255, 0.15);
      padding-top: 6px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      z-index: 2;
      position: relative;
    }

    .book-details {
      flex: 1;
      min-width: 0;
    }

    .book-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 20px;
      box-shadow: var(--shadow-primary);
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      display: flex;
      flex-direction: column;
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
    }

    .book-card:hover {
      transform: translateY(-4px);
      border-color: var(--card-border-hover);
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.45), var(--shadow-glow);
      background: rgba(255, 255, 255, 0.05);
    }

    .top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      margin-bottom: 14px;
    }

    .pill {
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 11px;
      font-weight: 700;
      background: rgba(124, 92, 255, 0.15);
      color: #a78bfa;
      border: 1px solid rgba(124, 92, 255, 0.3);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .score {
      background: rgba(34, 211, 238, 0.15);
      color: #22d3ee;
      border: 1px solid rgba(34, 211, 238, 0.3);
    }

    .book-card h3 {
      margin: 0 0 10px;
      font-size: 18px;
      line-height: 1.4;
      font-weight: 700;
      color: #fff;
    }

    h4 {
      margin: 16px 0 8px;
      font-size: 14px;
      font-weight: 600;
      color: #e2e8f0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      padding-bottom: 4px;
    }

    p, li {
      color: var(--text-muted);
      font-size: 13px;
      line-height: 1.5;
    }

    p {
      margin: 6px 0;
    }

    p b {
      color: #cbd5e1;
      font-weight: 500;
    }

    ul {
      list-style: none;
      padding: 0;
      margin: 0;
    }

    li {
      margin: 6px 0;
      display: flex;
      align-items: flex-start;
      gap: 6px;
    }

    .ok {
      color: #22c55e;
      font-weight: 800;
      margin-right: 4px;
      flex-shrink: 0;
    }

    .tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 12px;
      margin-bottom: auto;
    }

    .tags span {
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 999px;
      padding: 3px 8px;
      background: rgba(255, 255, 255, 0.04);
      font-size: 11px;
      color: #cbd5e1;
      transition: all 0.2s ease;
    }

    .tags span:hover {
      background: rgba(124, 92, 255, 0.1);
      border-color: rgba(124, 92, 255, 0.3);
    }

    .availability {
      margin-top: 16px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      padding-top: 12px;
    }

    .availability p {
      font-size: 12.5px;
    }

    pre {
      white-space: pre-wrap;
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      padding: 16px;
      color: #cbd5e1;
      font-family: 'Courier New', Courier, monospace;
      font-size: 13px;
    }

    /* Responsive adjustments */
    @media (max-width: 900px) {
      .agent-layout {
        flex-direction: column;
      }
      .chat-panel {
        width: 100%;
        min-width: 0;
      }
      .results-panel {
        max-height: none;
      }
    }

    @media (max-width: 600px) {
      .nav-bar {
        padding: 12px 16px;
        flex-direction: column;
        gap: 10px;
      }
      .book-card-content {
        flex-direction: column;
        align-items: center;
      }
      .book-cover-wrapper {
        width: 120px;
        height: 175px;
        margin-bottom: 12px;
      }
      .book-details {
        width: 100%;
      }
    }

    /* Card actions styling */
    .card-actions {
      margin-top: 16px;
      display: flex;
      gap: 10px;
    }

    .card-action-btn {
      flex: 1;
      min-height: 38px;
      border-radius: 8px;
      font-size: 13.5px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      font-family: inherit;
    }

    .card-action-btn.borrow-btn {
      background: linear-gradient(135deg, #7c5cff, #4f46e5);
      border: 1px solid rgba(124, 92, 255, 0.3);
      color: #fff;
    }

    .card-action-btn.borrow-btn:hover:not(:disabled) {
      background: linear-gradient(135deg, #906ffa, #6366f1);
      box-shadow: 0 0 15px rgba(124, 92, 255, 0.35);
      transform: translateY(-1px);
    }

    .card-action-btn.borrow-btn:disabled {
      background: rgba(255, 255, 255, 0.05);
      border-color: rgba(255, 255, 255, 0.05);
      color: rgba(255, 255, 255, 0.2);
      cursor: not-allowed;
      transform: none;
      box-shadow: none;
    }

    .card-action-btn.return-btn {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #cbd5e1;
    }

    .card-action-btn.return-btn:hover {
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(255, 255, 255, 0.2);
      color: #fff;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
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
        border-color: var(--card-border);
        transform: translateY(0) scale(1);
      }
    }

    .card-updated {
      animation: card-pulse 1s cubic-bezier(0.25, 0.8, 0.25, 1) forwards;
    }
  </style>
</head>
<body>
  <!-- Navigation Header -->
  <nav class="nav-bar">
    <div class="logo">
      <span class="icon">📚</span>
      <span class="title">Aster Hall Library</span>
    </div>
    <div class="nav-links">
      <button id="nav-home" class="nav-btn active" onclick="switchPage('home')">Home Dashboard</button>
      <button id="nav-agent" class="nav-btn" onclick="switchPage('agent')">AI Library Agent</button>
    </div>
  </nav>

  <div class="shell">
    
    <!-- HOME PAGE -->
    <div id="page-home" class="page-content">
      <header>
        <h1>Aster Hall Library Dashboard</h1>
        <p class="sub">Welcome to our digital campus library. Explore top books, browse subjects, or consult our AI research assistant.</p>
      </header>

      <!-- Moving Image Rail -->
      <section class="panel-transparent">
        <h3>Trending Books</h3>
        <div class="image-rail-container">
          <div id="moving-rail" class="image-rail">
            <!-- Populated dynamically -->
          </div>
        </div>
      </section>

      <!-- Featured Subjects -->
      <section class="panel">
        <h3>Browse by Subject</h3>
        <div class="subject-grid">
          <div class="subject-card" onclick="browseSubject('Artificial Intelligence')">
            <div class="subject-icon">🤖</div>
            <h4>Artificial Intelligence</h4>
            <p>Neural networks, machine learning, NLP, and intelligent agents.</p>
          </div>
          <div class="subject-card" onclick="browseSubject('Programming')">
            <div class="subject-icon">💻</div>
            <h4>Programming</h4>
            <p>Python, Java, C++, OOP, and data structures.</p>
          </div>
          <div class="subject-card" onclick="browseSubject('Database Systems')">
            <div class="subject-icon">🗄️</div>
            <h4>Database Systems</h4>
            <p>SQL, NoSQL, query optimization, and transaction management.</p>
          </div>
          <div class="subject-card" onclick="browseSubject('MBA')">
            <div class="subject-icon">📊</div>
            <h4>Business & MBA</h4>
            <p>Management, finance, operations, and strategic marketing.</p>
          </div>
          <div class="subject-card" onclick="browseSubject('Cybersecurity')">
            <div class="subject-icon">🛡️</div>
            <h4>Cybersecurity</h4>
            <p>Cryptography, ethical hacking, and network security protocols.</p>
          </div>
          <div class="subject-card" onclick="browseSubject('Mathematics')">
            <div class="subject-icon">📐</div>
            <h4>Mathematics</h4>
            <p>Linear algebra, calculus, discrete math, and probability.</p>
          </div>
        </div>
      </section>
    </div>

    <!-- AGENT PAGE -->
    <div id="page-agent" class="page-content" style="display: none;">
      <div class="agent-layout">
        <!-- ChatGPT-style Left Sidebar -->
        <aside class="sidebar">
          <button class="btn-new-chat" onclick="newChat()">+ New Chat</button>
          <div id="conversation-list" class="conversation-list">
            <!-- Populated dynamically -->
          </div>
        </aside>

        <!-- ChatGPT-style Main Chat & Results Area -->
        <div class="main-chat-area">
          <!-- Top: Chat Panel -->
          <div class="chat-panel">
            <div class="chat-header">
              <h3 id="active-chat-title">Library AI Agent</h3>
              <button class="btn-clear" onclick="clearActiveChat()">Clear Chat</button>
            </div>
            <div id="chat-messages" class="chat-messages">
              <!-- Messages populated dynamically -->
            </div>
            <div class="chat-input-area">
              <input id="chat-input" placeholder="Ask about books, e.g., 'What Python books do you have?'" onkeydown="if(event.key === 'Enter') sendChatMessage()" />
              <button onclick="sendChatMessage()">Send</button>
            </div>
          </div>

          <!-- Bottom: Results & Borrow Panel -->
          <div class="results-panel">
            <div class="panel-header-sticky">
              <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; flex-wrap: wrap; gap: 8px;">
                <h3 style="margin: 0; font-size: 18px;">Search & Chat Recommendations</h3>
                <div id="status" class="status" style="margin: 0; font-size: 13.5px;">Type a query or ask the AI agent.</div>
              </div>
            </div>
            
            <div id="cards" class="cards">
              <!-- Recommendation cards populated here -->
            </div>

            <section class="panel-nested">
              <h3>Borrow / Return Portal</h3>
              <div class="row">
                <input id="isbnAction" placeholder="Enter book ISBN..." />
                <button onclick="libraryAction('borrow')">Borrow</button>
                <button class="secondary" onclick="libraryAction('return')">Return</button>
              </div>
              <div id="libraryStatus" class="library-status-msg"></div>
            </section>
          </div>
        </div>
      </div>
    </div>

  </div>

  <script>
    const esc = (v) => String(v ?? "").replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    const terms = (v, n=5) => String(v || "").split(/[;,|]/).map(x => x.trim()).filter(Boolean).slice(0, n);
    
    function availabilityText(book) {
      const copies = Number(book.copies || 0);
      if (copies > 0) return `Available Copies: ${copies}\nShelf: ${book.shelf || "Not assigned"}\nCan Borrow Today: YES`;
      return `Available Copies: ${copies}\nShelf: ${book.shelf || "Not assigned"}\nCan Borrow Today: NO\nBorrowed by: ${book.borrowed_count || 0} Students\nExpected Return: ${book.expected_return || "Not scheduled"}`;
    }
    
    function reasonLines(book, query) {
      const topics = terms(book.keywords || book.table_of_contents, 3).join(", ") || book.category || "the requested topic";
      const audience = terms(book.target_audience, 1)[0] || "college students";
      return [`Similar to ${query}`, `Covers ${topics}`, `Popular among ${audience}`, `${book.difficulty_level || "Intermediate"}-level textbook`];
    }
    
    function getHtmlCover(book) {
      const category = String(book.category || book.categories || "General").toLowerCase();
      let gradient = "linear-gradient(135deg, #312e81, #4f46e5)";
      let icon = "📚";

      if (category.includes("artificial intelligence") || category.includes("machine learning") || category.includes("data science") || category.includes("ai")) {
        gradient = "linear-gradient(135deg, #4f46e5, #06b6d4)";
        icon = "🤖";
      } else if (category.includes("programming") || category.includes("software")) {
        gradient = "linear-gradient(135deg, #1e293b, #475569)";
        icon = "💻";
      } else if (category.includes("database") || category.includes("sql")) {
        gradient = "linear-gradient(135deg, #0f172a, #2563eb)";
        icon = "🗄️";
      } else if (category.includes("cybersecurity") || category.includes("security")) {
        gradient = "linear-gradient(135deg, #020617, #16a34a)";
        icon = "🛡️";
      } else if (category.includes("cloud")) {
        gradient = "linear-gradient(135deg, #0284c7, #06b6d4)";
        icon = "☁️";
      } else if (category.includes("math") || category.includes("calculus") || category.includes("algebra")) {
        gradient = "linear-gradient(135deg, #7c3aed, #d946ef)";
        icon = "📐";
      } else if (category.includes("physics") || category.includes("chemistry") || category.includes("science")) {
        gradient = "linear-gradient(135deg, #be123c, #f43f5e)";
        icon = "🔬";
      } else if (category.includes("engineering") || category.includes("electronics")) {
        gradient = "linear-gradient(135deg, #b45309, #d97706)";
        icon = "⚙️";
      } else if (category.includes("mba") || category.includes("business") || category.includes("management") || category.includes("economics")) {
        gradient = "linear-gradient(135deg, #111827, #0d9488)";
        icon = "📊";
      } else if (category.includes("communication") || category.includes("research") || category.includes("writing")) {
        gradient = "linear-gradient(135deg, #4d7c0f, #84cc16)";
        icon = "📝";
      }

      return `<div class="html-book-cover">
        <div class="html-book-cover-bg" style="background: ${gradient};"></div>
        <div class="cover-pattern">${icon}</div>
        <div class="cover-header">${esc(book.category || "General")}</div>
        <div class="cover-title">${esc(book.title)}</div>
        <div class="cover-footer">${esc(book.author || book.authors || "Aster Hall Press")}</div>
      </div>`;
    }

    function getHtmlCoverFallback(img) {
      const book = {
        title: img.dataset.title || "Untitled",
        category: img.dataset.category || "General",
        author: img.dataset.author || "Aster Hall Press"
      };
      return getHtmlCover(book);
    }

    function getCoverHtml(book) {
      const coverUrl = book.image_url;
      if (coverUrl) {
        return `<img class="book-cover-img" src="${coverUrl}" alt="Cover of ${esc(book.title)}" data-title="${esc(book.title)}" data-category="${esc(book.category || '')}" data-author="${esc(book.author || book.authors || '')}" onerror="this.outerHTML=getHtmlCoverFallback(this)" loading="lazy" />`;
      }
      return getHtmlCover(book);
    }

    function card(book, index, query, isbnMode=false) {
      const topics = terms(book.keywords || book.table_of_contents).map(t => `<span>${esc(t)}</span>`).join("");
      const reasons = reasonLines(book, query || book.title).map(r => `<li><span class="ok">&#10003;</span>${esc(r)}</li>`).join("");
      const isbn = esc(book.isbn || book.isbn13 || "N/A");
      const copies = Number(book.copies || 0);

      return `<article class="book-card" data-isbn="${isbn}" data-index="${index}" data-query="${esc(query || '')}" data-isbnmode="${isbnMode}">
        <div class="book-card-content">
          <div class="book-cover-wrapper">
            ${getCoverHtml(book)}
          </div>
          <div class="book-details">
            <div class="top">
              <span class="pill">${isbnMode ? "ISBN" : "#" + index}</span>
              <span class="pill score">${Math.round(Number(book.match_score || 100))}% match</span>
            </div>
            <h3>${esc(book.title || "Untitled")}</h3>
            <p><b>Author:</b> ${esc(book.author || book.authors || "Unknown author")}</p>
            <p><b>Category:</b> ${esc(book.category || "General")}</p>
            <p><b>Publisher:</b> ${esc(book.publisher || "Unknown publisher")}</p>
            <p><b>Year:</b> ${esc(book.year || "")}</p>
            <p><b>ISBN:</b> ${isbn}</p>
            <div class="tags">${topics}</div>
            <h4>Reason</h4><ul>${reasons}</ul>
            <div class="availability">
              <h4>Availability</h4>
              ${availabilityText(book).split("\n").map(line => `<p>${esc(line)}</p>`).join("")}
            </div>
            <div class="card-actions">
              <button class="card-action-btn borrow-btn" onclick="handleCardAction('${isbn}', 'borrow', this)" ${copies <= 0 ? 'disabled' : ''}>Borrow</button>
              <button class="card-action-btn return-btn" onclick="handleCardAction('${isbn}', 'return', this)">Return</button>
            </div>
          </div>
        </div>
      </article>`;
    }

    async function handleCardAction(isbn, action, button) {
      if (!isbn || isbn === "N/A") {
        alert("Invalid ISBN.");
        return;
      }
      button.disabled = true;
      try {
        const response = await fetch(`/api/${action}?isbn=${encodeURIComponent(isbn)}`, { method: "POST" });
        const data = await response.json();
        
        if (document.getElementById("libraryStatus")) {
          document.getElementById("libraryStatus").textContent = data.message;
        }
        
        if (data.ok && data.book) {
          // Find all cards with this ISBN and update them
          const cards = document.querySelectorAll(`article.book-card[data-isbn="${isbn}"]`);
          cards.forEach(cardEl => {
            const index = cardEl.getAttribute("data-index");
            const query = cardEl.getAttribute("data-query");
            const isbnMode = cardEl.getAttribute("data-isbnmode") === "true";
            
            const tempDiv = document.createElement("div");
            tempDiv.innerHTML = card(data.book, index, query, isbnMode);
            const newCard = tempDiv.firstElementChild;
            newCard.classList.add("card-updated");
            cardEl.replaceWith(newCard);
          });
          
          loadPopularRail();
        } else {
          alert(data.message);
        }
      } catch (err) {
        console.error("Action failed", err);
        alert("An error occurred. Please try again.");
      } finally {
        button.disabled = false;
      }
    }

    function switchPage(page) {
      document.querySelectorAll('.page-content').forEach(p => p.style.display = 'none');
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      if (page === 'home') {
        document.getElementById('page-home').style.display = 'block';
        document.getElementById('nav-home').classList.add('active');
      } else {
        document.getElementById('page-agent').style.display = 'block';
        document.getElementById('nav-agent').classList.add('active');
      }
    }

    function browseSubject(subjectName) {
      switchPage('agent');
      document.getElementById('chat-input').value = subjectName;
      sendChatMessage();
    }

    // ChatGPT-Style Conversations Management
    let conversations = JSON.parse(localStorage.getItem('library_conversations')) || [];
    let currentConversationId = localStorage.getItem('library_current_conversation_id') || "";

    const DEFAULT_GREETING = "Hii! I am your Library AI Agent. Ask me for book recommendations, topics, or lookup an ISBN (e.g. 'Show me books on Machine Learning' or '9789310000001').";

    function saveConversations() {
      localStorage.setItem('library_conversations', JSON.stringify(conversations));
      localStorage.setItem('library_current_conversation_id', currentConversationId);
    }

    function initConversations() {
      if (conversations.length === 0) {
        // Create initial default chat
        const newId = String(Date.now());
        conversations.push({
          id: newId,
          title: "New Library Chat",
          history: [{ role: 'assistant', content: DEFAULT_GREETING }],
          books: []
        });
        currentConversationId = newId;
        saveConversations();
      }
      
      // Ensure active ID is valid
      const activeExists = conversations.some(c => c.id === currentConversationId);
      if (!activeExists && conversations.length > 0) {
        currentConversationId = conversations[0].id;
        saveConversations();
      }

      renderSidebar();
      renderActiveChat();
    }

    function renderSidebar() {
      const container = document.getElementById('conversation-list');
      container.innerHTML = conversations.map(c => {
        const isActive = c.id === currentConversationId ? 'active' : '';
        return `<div class="conversation-item ${isActive}" onclick="selectConversation('${c.id}')">
          <span>💬 ${esc(c.title)}</span>
          <button class="delete-chat-btn" onclick="deleteConversation('${c.id}', event)">✕</button>
        </div>`;
      }).join('');
    }

    function selectConversation(id) {
      currentConversationId = id;
      saveConversations();
      renderSidebar();
      renderActiveChat();
    }

    function newChat() {
      const newId = String(Date.now());
      conversations.unshift({
        id: newId,
        title: "New Library Chat",
        history: [{ role: 'assistant', content: DEFAULT_GREETING }],
        books: []
      });
      currentConversationId = newId;
      saveConversations();
      renderSidebar();
      renderActiveChat();
      
      // Reset recommendations below chat
      document.getElementById("cards").innerHTML = "";
      document.getElementById("status").textContent = "Type a query or ask the AI agent.";
    }

    function deleteConversation(id, event) {
      if (event) event.stopPropagation(); // Avoid triggering selectConversation
      
      conversations = conversations.filter(c => c.id !== id);
      
      if (currentConversationId === id) {
        if (conversations.length > 0) {
          currentConversationId = conversations[0].id;
        } else {
          currentConversationId = "";
        }
      }
      
      saveConversations();
      initConversations();
    }

    function clearActiveChat() {
      const active = conversations.find(c => c.id === currentConversationId);
      if (active) {
        active.history = [{ role: 'assistant', content: "Chat cleared. Ask me for recommendations or book lookups." }];
        active.books = [];
        active.title = "New Library Chat";
        saveConversations();
        renderSidebar();
        renderActiveChat();
      }
    }

    function getActiveConversation() {
      return conversations.find(c => c.id === currentConversationId);
    }

    function renderActiveChat() {
      const active = getActiveConversation();
      if (!active) return;

      document.getElementById('active-chat-title').textContent = active.title;

      // Render Messages
      const chatContainer = document.getElementById('chat-messages');
      chatContainer.innerHTML = active.history.map(msg => {
        const bubbleClass = msg.role === 'user' ? 'user' : 'agent';
        const formatted = esc(msg.content)
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\*(.*?)\*/g, '<em>$1</em>')
          .replace(/`([^`]+)`/g, '<code>$1</code>')
          .replace(/\n/g, '<br/>');
        return `<div class="chat-bubble ${bubbleClass}">${formatted}</div>`;
      }).join('');
      chatContainer.scrollTop = chatContainer.scrollHeight;

      // Render Recommendations Below Chat
      const cardsContainer = document.getElementById("cards");
      if (active.books && active.books.length > 0) {
        cardsContainer.innerHTML = active.books.map((b, i) => card(b, i + 1, active.title, false)).join("");
        document.getElementById("status").textContent = `${active.books.length} result(s) found via AI chat`;
      } else {
        cardsContainer.innerHTML = "";
        document.getElementById("status").textContent = "Type a query or ask the AI agent.";
      }
    }

    async function sendChatMessage() {
      const input = document.getElementById('chat-input');
      const message = input.value.trim();
      if (!message) return;

      const active = getActiveConversation();
      if (!active) return;

      input.value = '';
      active.history.push({ role: 'user', content: message });
      
      // Update title on first real message
      if (active.title === "New Library Chat" || active.title === "New Library Chat...") {
        active.title = message.length > 20 ? message.substring(0, 18) + "..." : message;
      }

      renderSidebar();
      renderActiveChat();
      saveConversations();

      // Show typing indicator
      const chatContainer = document.getElementById('chat-messages');
      const typingBubble = document.createElement('div');
      typingBubble.className = 'chat-bubble agent';
      typingBubble.id = 'chat-typing-indicator';
      typingBubble.textContent = 'Thinking...';
      chatContainer.appendChild(typingBubble);
      chatContainer.scrollTop = chatContainer.scrollHeight;

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, history: active.history })
        });
        const data = await response.json();
        
        // Remove typing indicator
        const indicator = document.getElementById('chat-typing-indicator');
        if (indicator) indicator.remove();

        active.history.push({ role: 'assistant', content: data.answer });
        if (data.books && data.books.length > 0) {
          active.books = data.books;
        } else {
          active.books = [];
        }
        
        renderActiveChat();
        saveConversations();
      } catch (err) {
        const indicator = document.getElementById('chat-typing-indicator');
        if (indicator) indicator.remove();
        active.history.push({ role: 'assistant', content: "Sorry, I encountered an error. Please try again." });
        renderActiveChat();
      }
    }

    async function searchBooks(queryText) {
      const query = queryText || "";
      const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
      const data = await response.json();
      document.getElementById("cards").innerHTML = (data.books || []).map((b, i) => card(b, i + 1, query, data.mode === "isbn")).join("");
      document.getElementById("status").textContent = `${(data.books || []).length} result(s) found`;
    }

    async function libraryAction(action) {
      const isbn = document.getElementById("isbnAction").value.trim();
      const response = await fetch(`/api/${action}?isbn=${encodeURIComponent(isbn)}`, { method: "POST" });
      const data = await response.json();
      document.getElementById("libraryStatus").textContent = data.message;
      if (data.book) {
        document.getElementById("cards").innerHTML = card(data.book, 1, isbn, true);
        loadPopularRail();
      }
    }

    async function loadPopularRail() {
      try {
        const response = await fetch('/api/popular');
        const data = await response.json();
        const books = data.books || [];
        if (books.length > 0) {
          // Double the books for seamless infinite marquee scroll
          const doubleBooks = [...books, ...books];
          document.getElementById('moving-rail').innerHTML = doubleBooks.map(b => {
            return `<div class="rail-item" onclick="browseSubject('${b.title}')">
              ${getCoverHtml(b)}
              <div class="rail-item-info">${esc(b.title)}</div>
            </div>`;
          }).join('');
        }
      } catch (err) {
        console.error("Failed to load trending books", err);
      }
    }

    // Initialize
    window.addEventListener('DOMContentLoaded', () => {
      initConversations();
      loadPopularRail();
      searchBooks("");
    });
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type="application/json"):
        payload = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self._send(200, INDEX_HTML, "text/html; charset=utf-8")
            return
        if parsed.path == "/api/search":
            query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
            self._send(200, json.dumps(api_search(query)))
            return
        if parsed.path == "/api/popular":
            books = backend.recommend_books("", top_n=10)
            self._send(200, json.dumps({"books": books}))
            return
        self._send(404, json.dumps({"error": "Not found"}))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in {"/api/borrow", "/api/return"}:
            action = parsed.path.rsplit("/", 1)[-1]
            isbn = urllib.parse.parse_qs(parsed.query).get("isbn", [""])[0]
            ok, message, book = borrow_or_return(isbn, action)
            self._send(200, json.dumps({"ok": ok, "message": message, "book": book}))
            return
        if parsed.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}
            message = data.get("message", "").strip()
            history = data.get("history", [])
            chat_result = api_chat(message, history)
            self._send(200, json.dumps(chat_result))
            return
        self._send(404, json.dumps({"error": "Not found"}))


def find_free_port(start=7861):
    for port in range(start, start + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def main():
    port = find_free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"College Library Recommender running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
