from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from groq import Groq
except Exception:
    Groq = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:
    TfidfVectorizer = None
    cosine_similarity = None

from src.preprocess import load_books
import pickle


PROJECT_DIR = Path(__file__).resolve().parents[1]
ENHANCED_DATASET_PATH = PROJECT_DIR / "data" / "books_enhanced.csv"
MODEL_NAME = "llama-3.3-70b-versatile"

if load_dotenv is not None:
    load_dotenv(PROJECT_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY and Groq is not None else None

df = load_books()

# Load precalculated SentenceTransformer model and embeddings
try:
    from sentence_transformers import SentenceTransformer
    st_model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings_path = PROJECT_DIR / "models" / "book_embeddings.pkl"
    if embeddings_path.exists():
        with open(embeddings_path, "rb") as f:
            book_embeddings = pickle.load(f)
    else:
        book_embeddings = None
except Exception as e:
    st_model = None
    book_embeddings = None


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and np.isnan(value):
        return ""
    return " ".join(str(value).split())


def _first(book: dict[str, Any] | pd.Series, *keys: str, default: str = "") -> str:
    for key in keys:
        value = book.get(key, "")
        if _clean(value):
            return _clean(value)
    return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _split_terms(value: Any) -> list[str]:
    return [
        term.strip()
        for term in re.split(r"[;,|]", _clean(value))
        if term.strip()
    ]


def _isbn_digits(value: str) -> str:
    return re.sub(r"[^0-9Xx]", "", value or "")


def _semantic_text(row: pd.Series) -> str:
    return " ".join(
        _clean(row.get(key, ""))
        for key in [
            "title",
            "author",
            "authors",
            "category",
            "categories",
            "description",
            "keywords",
            "table_of_contents",
            "target_audience",
        ]
    )


def _tokens(text: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 1
    }
    if "ai" in tokens:
        tokens.update({"artificial", "intelligence", "machine", "learning"})
    if "ml" in tokens:
        tokens.update({"machine", "learning", "model"})
    return tokens


def _fallback_semantic_scores(query: str) -> list[float]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return [0.0 for _ in range(len(df))]

    scores = []
    for _, row in df.iterrows():
        row_tokens = _tokens(_semantic_text(row))
        if not row_tokens:
            scores.append(0.0)
            continue
        intersection = len(query_tokens & row_tokens)
        union = len(query_tokens | row_tokens)
        scores.append(intersection / union if union else 0.0)
    return scores


if TfidfVectorizer is not None:
    tfidf_vectorizer = TfidfVectorizer(stop_words="english", max_features=12000, ngram_range=(1, 2))
    tfidf_matrix = tfidf_vectorizer.fit_transform(df.apply(_semantic_text, axis=1).tolist())
else:
    tfidf_vectorizer = None
    tfidf_matrix = None


try:
    _ratings_col = pd.to_numeric(df.get("ratings_count", pd.Series([0])), errors="coerce").fillna(0)
    MAX_RATINGS_COUNT = float(max(_ratings_col.max(), 1.0))
except Exception:
    MAX_RATINGS_COUNT = 1.0


def popularity_score(row: pd.Series | dict[str, Any]) -> float:
    stored = _as_float(row.get("popularity_score", 0))
    if stored:
        return max(0.0, min(stored, 1.0))

    rating = _as_float(row.get("average_rating", 0)) / 5.0
    ratings_count = _as_float(row.get("ratings_count", 0))
    return max(0.0, min(0.4 * rating + 0.6 * (ratings_count / MAX_RATINGS_COUNT), 1.0))


def _is_word_substring(sub: str, full: str) -> bool:
    sub_clean = sub.strip().lower()
    full_clean = full.strip().lower()
    if not sub_clean or not full_clean:
        return False
    # Check for whole-word boundaries or prefix matches (if length is >= 4 to avoid short acronym bugs)
    pattern = r"\b" + re.escape(sub_clean) + r"\b"
    if re.search(pattern, full_clean):
        return True
    if len(sub_clean) >= 4 and sub_clean in full_clean:
        return True
    return False


def _category_match(row: pd.Series, query: str) -> float:
    query_lower = query.lower()
    category = _first(row, "category", "categories").lower()
    keywords = [term.lower() for term in _split_terms(row.get("keywords", ""))]
    if not category:
        return 0.0
    if _is_word_substring(query_lower, category) or _is_word_substring(category, query_lower):
        return 1.0
    if any(_is_word_substring(query_lower, term) or _is_word_substring(term, query_lower) for term in keywords):
        return 0.75
    return SequenceMatcher(None, query_lower, category).ratio() * 0.5


def _author_similarity(row: pd.Series, query: str) -> float:
    author = _first(row, "author", "authors").lower()
    query_lower = query.lower()
    if not author:
        return 0.0
    if _is_word_substring(query_lower, author) or _is_word_substring(author, query_lower):
        return 1.0
    return SequenceMatcher(None, query_lower, author).ratio()


def _availability_penalty(row: pd.Series) -> float:
    copies = int(_as_float(row.get("copies", row.get("copies_available", 0))))
    return 0.94 if copies <= 0 else 1.0


def get_book_cover(book: dict[str, Any]) -> str:
    thumbnail = book.get("thumbnail")
    if thumbnail and isinstance(thumbnail, str) and thumbnail.strip():
        if thumbnail.startswith("http://"):
            thumbnail = thumbnail.replace("http://", "https://", 1)
        return thumbnail

    isbn = str(book.get("isbn") or book.get("isbn13") or "").replace("-", "").replace(" ", "")
    if isbn and len(isbn) >= 10 and not isbn.startswith("97893"):
        return f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
    
    category = str(book.get("category") or book.get("categories") or "").lower()
    title = str(book.get("title") or "").strip()
    
    # Calculate a stable hash of the title to select a cover photo
    idx = sum(ord(c) for c in title) if title else 0
    
    ai_pool = [
        "photo-1507146426996-ef05306b995a", "photo-1526374965328-7f61d4dc18c5",
        "photo-1510511459019-5dda7724fd87", "photo-1550751827-4bd374c3f58b",
        "photo-1639322537228-f710d846310a", "photo-1451187580459-43490279c0fa",
        "photo-1518770660439-4636190af475", "photo-1531297484001-80022131f5a1",
        "photo-1527474305487-b87b222841cc", "photo-1558494949-ef010cbdcc31"
    ]
    prog_pool = [
        "photo-1555066931-4365d14bab8c", "photo-1614741118887-7a4ee193a5fa",
        "photo-1629654297299-c8506221ca97", "photo-1461749280684-dccba630e2f6",
        "photo-1517694712202-14dd9538aa97", "photo-1542831371-29b0f74f9713",
        "photo-1587620962725-abab7fe55159", "photo-1607799279861-4dd421887fb3",
        "photo-1531403009284-440f080d1e12", "photo-1515879218367-8466d910aaa4"
    ]
    science_pool = [
        "photo-1507413245164-6160d8298b31", "photo-1532187643603-ba119ca4109e",
        "photo-1617155093730-a8bf47be792d", "photo-1532094349884-543bc11b234d",
        "photo-1507668077129-56e32842fceb", "photo-1464822759023-fed622ff2c3b",
        "photo-1500485035595-cbe6f645feb1", "photo-1470071459604-3b5ec3a7fe05"
    ]
    eng_pool = [
        "photo-1581092160607-ee22621dd758", "photo-1504307651254-35680f356dfd",
        "photo-1635070041078-e363dbe005cb", "photo-1517646287270-a5a9ca602e5c",
        "photo-1581091226825-a6a2a5aee158", "photo-1508962914676-134849a727f0",
        "photo-1503387762-592deb58ef4e"
    ]
    business_pool = [
        "photo-1454165804606-c3d57bc86b40", "photo-1508385082359-f38ae991e8f2",
        "photo-1460925895917-afdab827c52f", "photo-1504868584819-f8e8b4b6d7e3",
        "photo-1590283603385-17ffb3a7f29f", "photo-1518186285589-2f7649de83e0"
    ]
    math_pool = [
        "photo-1509228468518-180dd4864904", "photo-1606326608606-aa0b62935f2b",
        "photo-1543002588-bfa74002ed7e", "photo-1516979187457-637abb4f9353"
    ]
    general_pool = [
        "photo-1543002588-bfa74002ed7e", "photo-1544947950-fa07a98d237f",
        "photo-1512820790803-83ca734da794", "photo-1497633762265-9d179a990aa6",
        "photo-1516979187457-637abb4f9353", "photo-1506880018603-83d5b814b5a6",
        "photo-1476275466078-4007374efbbe", "photo-1495446815901-a7297e633e8d",
        "photo-1513001900722-370f803f498d", "photo-1532012197267-da84d127e765"
    ]

    if any(k in category for k in ["artificial intelligence", "machine learning", "data science", "ai"]):
        pool = ai_pool
    elif any(k in category for k in ["programming", "python", "java", "c++", "clean code", "code", "software"]):
        pool = prog_pool
    elif any(k in category for k in ["database", "sql", "nosql", "distributed"]):
        pool = prog_pool
    elif any(k in category for k in ["math", "calculus", "algebra", "geometry"]):
        pool = math_pool
    elif any(k in category for k in ["physics", "chemistry", "science"]):
        pool = science_pool
    elif any(k in category for k in ["engineering", "electronics"]):
        pool = eng_pool
    elif any(k in category for k in ["mba", "business", "management", "economics"]):
        pool = business_pool
    else:
        pool = general_pool

    photo_id = pool[idx % len(pool)]
    return f"https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w=300&q=80"


def _book_dict(row: pd.Series, score: float | None = None) -> dict[str, Any]:
    copies = int(_as_float(row.get("copies", row.get("copies_available", 0))))
    total_copies = int(_as_float(row.get("total_copies", row.get("copies_total", copies))))
    borrowed = int(_as_float(row.get("borrowed_count", max(total_copies - copies, 0))))
    availability = _first(row, "availability", "availability_status", default="Available" if copies else "Borrowed")
    book = {
        "isbn": _first(row, "isbn", "isbn13"),
        "isbn13": _first(row, "isbn13", "isbn"),
        "title": _first(row, "title", default="Untitled"),
        "author": _first(row, "author", "authors", default="Unknown author"),
        "authors": _first(row, "authors", "author", default="Unknown author"),
        "category": _first(row, "category", "categories", default="General"),
        "categories": _first(row, "categories", "category", default="General"),
        "publisher": _first(row, "publisher", default="Unknown publisher"),
        "year": _first(row, "year", "published_year", default=""),
        "description": _first(row, "description", default="No description available."),
        "keywords": _first(row, "keywords"),
        "language": _first(row, "language", default="English"),
        "availability": availability,
        "copies": copies,
        "total_copies": total_copies,
        "borrowed_count": borrowed,
        "expected_return": _first(row, "expected_return", "expected_return_date"),
        "shelf": _first(row, "shelf", "shelf_location", default="Not assigned"),
        "popularity_score": round(popularity_score(row), 3),
        "difficulty_level": _first(row, "difficulty_level", default="Intermediate"),
        "target_audience": _first(row, "target_audience", default="College students"),
        "table_of_contents": _first(row, "table_of_contents"),
        "thumbnail": _first(row, "thumbnail"),
        "match_score": round(score * 100, 2) if score is not None else 100,
    }
    book["image_url"] = get_book_cover(book)
    return book


def search_by_isbn(isbn: str) -> dict[str, Any] | None:
    cleaned = _isbn_digits(isbn)
    local = df[
        df.apply(
            lambda row: cleaned
            in {_isbn_digits(_first(row, "isbn", "isbn13")), _isbn_digits(_first(row, "isbn10"))},
            axis=1,
        )
    ]
    if not local.empty:
        return _book_dict(local.iloc[0], 1.0)

    return fetch_isbn_metadata(cleaned)


def _find_local_index(isbn: str) -> int | None:
    cleaned = _isbn_digits(isbn)
    matches = df[
        df.apply(
            lambda row: cleaned
            in {_isbn_digits(_first(row, "isbn", "isbn13")), _isbn_digits(_first(row, "isbn10"))},
            axis=1,
        )
    ]
    if matches.empty:
        return None
    return int(matches.index[0])


def _save_dataset() -> None:
    if ENHANCED_DATASET_PATH.exists():
        df.to_csv(ENHANCED_DATASET_PATH, index=False)


def borrow_book(isbn: str) -> tuple[bool, str, dict[str, Any] | None]:
    index = _find_local_index(isbn)
    if index is None:
        return False, "Book not found in the local library dataset.", None

    copies = int(_as_float(df.at[index, "copies"] if "copies" in df.columns else df.at[index, "copies_available"]))
    if copies <= 0:
        return False, "No copy is available to borrow today.", _book_dict(df.loc[index], 1.0)

    total = int(_as_float(df.at[index, "total_copies"] if "total_copies" in df.columns else copies))
    df.at[index, "copies"] = copies - 1
    df.at[index, "copies_available"] = copies - 1
    df.at[index, "borrowed_count"] = int(_as_float(df.at[index, "borrowed_count"])) + 1
    df.at[index, "availability"] = "Available" if copies - 1 > 0 else "Borrowed"
    df.at[index, "availability_status"] = df.at[index, "availability"]
    if copies - 1 <= 0:
        df.at[index, "expected_return"] = (date.today() + timedelta(days=14)).isoformat()
        df.at[index, "expected_return_date"] = df.at[index, "expected_return"]
    df.at[index, "total_copies"] = total
    _save_dataset()
    return True, "Borrow recorded successfully.", _book_dict(df.loc[index], 1.0)


def return_book(isbn: str) -> tuple[bool, str, dict[str, Any] | None]:
    index = _find_local_index(isbn)
    if index is None:
        return False, "Book not found in the local library dataset.", None

    copies = int(_as_float(df.at[index, "copies"] if "copies" in df.columns else df.at[index, "copies_available"]))
    total = int(_as_float(df.at[index, "total_copies"] if "total_copies" in df.columns else copies))
    if copies >= total:
        return False, "All copies are already marked as returned.", _book_dict(df.loc[index], 1.0)

    df.at[index, "copies"] = copies + 1
    df.at[index, "copies_available"] = copies + 1
    df.at[index, "borrowed_count"] = max(0, int(_as_float(df.at[index, "borrowed_count"])) - 1)
    df.at[index, "availability"] = "Available"
    df.at[index, "availability_status"] = "Available"
    df.at[index, "expected_return"] = ""
    df.at[index, "expected_return_date"] = ""
    _save_dataset()
    return True, "Return recorded successfully.", _book_dict(df.loc[index], 1.0)


def _fetch_json(url: str, timeout: int = 6) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def fetch_isbn_metadata(isbn: str) -> dict[str, Any] | None:
    open_library = _fetch_json(
        "https://openlibrary.org/api/books?"
        + urllib.parse.urlencode({"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"})
    )
    item = (open_library or {}).get(f"ISBN:{isbn}")
    if item:
        authors = "; ".join(author.get("name", "") for author in item.get("authors", []))
        subjects = "; ".join(subject.get("name", "") for subject in item.get("subjects", [])[:8])
        book = {
            "isbn": isbn,
            "title": item.get("title", "Unknown title"),
            "author": authors or "Unknown author",
            "category": subjects.split(";")[0].strip() if subjects else "General",
            "publisher": "; ".join(pub.get("name", "") for pub in item.get("publishers", [])) or "Unknown publisher",
            "year": item.get("publish_date", ""),
            "description": item.get("notes", "Metadata fetched from Open Library."),
            "keywords": subjects,
            "language": "English",
            "availability": "Not in local library",
            "copies": 0,
            "total_copies": 0,
            "borrowed_count": 0,
            "expected_return": "",
            "shelf": "Not assigned",
            "popularity_score": 0.4,
            "difficulty_level": infer_difficulty(item.get("title", ""), subjects),
            "target_audience": infer_audience(subjects),
            "table_of_contents": subjects,
            "match_score": 100,
            "source": "Open Library",
        }
        book["image_url"] = get_book_cover(book)
        return book

    google = _fetch_json(f"https://www.googleapis.com/books/v1/volumes?q=isbn:{urllib.parse.quote(isbn)}")
    items = (google or {}).get("items", [])
    if items:
        info = items[0].get("volumeInfo", {})
        categories = "; ".join(info.get("categories", []))
        book = {
            "isbn": isbn,
            "title": info.get("title", "Unknown title"),
            "author": "; ".join(info.get("authors", [])) or "Unknown author",
            "category": categories.split(";")[0].strip() if categories else "General",
            "publisher": info.get("publisher", "Unknown publisher"),
            "year": info.get("publishedDate", ""),
            "description": info.get("description", "Metadata fetched from Google Books."),
            "keywords": categories,
            "language": info.get("language", "English"),
            "availability": "Not in local library",
            "copies": 0,
            "total_copies": 0,
            "borrowed_count": 0,
            "expected_return": "",
            "shelf": "Not assigned",
            "popularity_score": 0.4,
            "difficulty_level": infer_difficulty(info.get("title", ""), categories),
            "target_audience": infer_audience(categories),
            "table_of_contents": categories,
            "match_score": 100,
            "source": "Google Books",
        }
        book["image_url"] = get_book_cover(book)
        return book

    return None


def infer_difficulty(title: str, text: str = "") -> str:
    lowered = f"{title} {text}".lower()
    if any(term in lowered for term in ["advanced", "research", "graduate", "deep learning", "compiler"]):
        return "Advanced"
    if any(term in lowered for term in ["beginning", "beginner", "introduction", "fundamentals", "basics"]):
        return "Beginner"
    return "Intermediate"


def infer_audience(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ["ai", "machine learning", "data"]):
        return "AI Engineers; ML Students; Data Science Students"
    if any(term in lowered for term in ["business", "management", "economics"]):
        return "MBA Students; Management Students"
    if any(term in lowered for term in ["engineering", "mechanical", "civil", "electrical"]):
        return "Engineering Students; Research Students"
    return "College students; Faculty; Exam preparation students"


def summarize_book(book: dict[str, Any]) -> str:
    fallback = build_summary_sections(book)
    if client is None:
        return fallback

    prompt = f"""
Generate the exact sections below for a college library ISBN result.

Title: {_first(book, "title")}
Authors: {_first(book, "author", "authors")}
Category: {_first(book, "category", "categories")}
Description: {_first(book, "description")}
Keywords: {_first(book, "keywords")}
Table of contents: {_first(book, "table_of_contents")}
Difficulty: {_first(book, "difficulty_level")}
Audience: {_first(book, "target_audience")}

Sections:
Book Summary
This book covers:
- topic
Recommended for:
- audience
Difficulty Level:
"""
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=350,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return fallback


def build_summary_sections(book: dict[str, Any]) -> str:
    description = _first(book, "description", default="No description available.")
    topics = _split_terms(_first(book, "keywords", "table_of_contents"))[:5]
    if not topics:
        topics = _clean(_first(book, "category", "categories", default="General")).split()[:5]
    audience = _split_terms(_first(book, "target_audience", default="College students"))[:4]
    lines = ["Book Summary", "", description[:700], "", "This book covers:"]
    lines.extend(f"- {topic}" for topic in topics)
    lines.extend(["", "Recommended for:"])
    lines.extend(f"- {person}" for person in audience)
    lines.extend(["", "Difficulty Level:", _first(book, "difficulty_level", default="Intermediate")])
    return "\n".join(lines)


def explain_book(book: dict[str, Any], query: str) -> str:
    topics = _split_terms(_first(book, "keywords", "table_of_contents"))[:3]
    if not topics:
        topics = [_first(book, "category", default="the requested topic")]
    audience = _split_terms(_first(book, "target_audience", default="college students"))[:1]
    audience_text = audience[0] if audience else "college students"
    difficulty = _first(book, "difficulty_level", default="Intermediate")
    return "\n".join(
        [
            f"✓ Similar to {query}",
            f"✓ Covers {', '.join(topics)}",
            f"✓ Popular among {audience_text}",
            f"✓ {difficulty}-level textbook",
        ]
    )


def _preprocess_query(query: str) -> str:
    expanded = query.strip()
    replacements = {
        r"\bllm\b": "large language model artificial intelligence machine learning computer science nlp",
        r"\bllms\b": "large language models artificial intelligence machine learning computer science nlp",
        r"\bai\b": "artificial intelligence computer science machine learning",
        r"\bml\b": "machine learning artificial intelligence computer science",
        r"\bnlp\b": "natural language processing artificial intelligence language model",
        r"\bsql\b": "database SQL programming query",
        r"\boop\b": "object-oriented programming computer science",
        r"\bcs\b": "computer science",
        r"\bcse\b": "computer science engineering",
    }
    for pattern, replacement in replacements.items():
        expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
    return expanded


def recommend_books(query: str, top_n: int = 10) -> list[dict[str, Any]]:
    processed_query = _preprocess_query(query)

    # Use SentenceTransformer embeddings if available
    if st_model is not None and book_embeddings is not None:
        query_embedding = st_model.encode([processed_query], convert_to_numpy=True)
        if len(book_embeddings) == len(df):
            if cosine_similarity is not None:
                semantic_scores = cosine_similarity(query_embedding, book_embeddings)[0]
            else:
                norm_q = np.linalg.norm(query_embedding[0])
                norm_b = np.linalg.norm(book_embeddings, axis=1)
                dot = np.dot(book_embeddings, query_embedding[0])
                semantic_scores = dot / (norm_q * norm_b + 1e-9)
        else:
            if tfidf_vectorizer is not None and tfidf_matrix is not None and cosine_similarity is not None:
                q_emb = tfidf_vectorizer.transform([processed_query])
                semantic_scores = cosine_similarity(q_emb, tfidf_matrix)[0]
            else:
                semantic_scores = _fallback_semantic_scores(processed_query)
    elif tfidf_vectorizer is not None and tfidf_matrix is not None and cosine_similarity is not None:
        query_embedding = tfidf_vectorizer.transform([processed_query])
        semantic_scores = cosine_similarity(query_embedding, tfidf_matrix)[0]
    else:
        semantic_scores = _fallback_semantic_scores(processed_query)

    scored: list[tuple[int, float]] = []

    for idx, row in df.iterrows():
        semantic = float(semantic_scores[idx])
        category = _category_match(row, query)
        author = _author_similarity(row, query)
        popularity = popularity_score(row)
        final_score = (
            0.5 * semantic
            + 0.2 * category
            + 0.15 * author
            + 0.15 * popularity
        ) * _availability_penalty(row)
        scored.append((idx, final_score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return [_book_dict(df.iloc[idx], score) for idx, score in scored[:top_n]]
