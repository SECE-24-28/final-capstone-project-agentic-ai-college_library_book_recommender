import pickle
import numpy as np
import pandas as pd
from groq import Groq
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from src.preprocess import load_books

# =====================================
# GROQ API KEY
# =====================================

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(
    api_key=GROQ_API_KEY
)

# =====================================
# LOAD DATA
# =====================================

df = load_books()

with open("models/book_embeddings.pkl", "rb") as f:
    book_embeddings = pickle.load(f)

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

df["ratings_count"] = (
    pd.to_numeric(
        df["ratings_count"],
        errors="coerce"
    )
)

df["average_rating"] = (
    pd.to_numeric(
        df["average_rating"],
        errors="coerce"
    )
)

max_rating_count = (
    df["ratings_count"]
    .fillna(0)
    .max()
)

# =====================================
# POPULARITY SCORE
# =====================================

def popularity_score(row):

    rating = row.get(
        "average_rating",
        0
    )

    ratings_count = row.get(
        "ratings_count",
        0
    )

    try:
        rating_score = (
            float(rating) / 5
        )
    except:
        rating_score = 0

    try:
        count_score = (
            float(ratings_count)
            / max_rating_count
        )
    except:
        count_score = 0

    return (
        0.4 * rating_score
        + 0.6 * count_score
    )

# =====================================
# ISBN SEARCH
# =====================================

def search_by_isbn(isbn):

    result = df[
        df["isbn13"]
        .astype(str)
        == str(isbn)
    ]

    if len(result) == 0:
        return None

    row = result.iloc[0]

    return row.to_dict()

# =====================================
# BOOK SUMMARY USING GROQ
# =====================================

def summarize_book(book):

    prompt = f"""
Book Title:
{book['title']}

Author:
{book['authors']}

Category:
{book['categories']}

Description:
{book['description']}

Generate:

1. Book Summary
2. Topics Covered
3. Difficulty Level
4. Recommended Audience

Keep it concise.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return (
        response
        .choices[0]
        .message
        .content
    )

# =====================================
# EXPLAIN MATCH
# =====================================

def explain_book(book, query):

    prompt = f"""
User searched:

{query}

Book Title:
{book['title']}

Author:
{book['author']}

Category:
{book['category']}

Description:
{book['description']}

Explain WHY this book matches the user's query.

Return:

Why This Book Matches:
(3-5 sentences)

Topics Covered:
- topic
- topic
- topic

Difficulty Level:
Beginner / Intermediate / Advanced

Recommended For:
- audience
- audience

Keep it concise.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return (
        response
        .choices[0]
        .message
        .content
    )

# =====================================
# RECOMMENDATION ENGINE
# =====================================

def recommend_books(
    query,
    top_n=5
):

    query_embedding = model.encode(
        [query]
    )

    semantic_scores = cosine_similarity(
        query_embedding,
        book_embeddings
    )[0]

    recommendations = []

    query_lower = query.lower()

    for idx, row in df.iterrows():

        semantic_score = (
            semantic_scores[idx]
        )

        category_score = 0

        category = str(
            row.get(
                "categories",
                ""
            )
        ).lower()

        if (
            category
            and category != "nan"
        ):
            if category in query_lower:
                category_score = 1

        pop_score = popularity_score(
            row
        )

        final_score = (
            0.60 * semantic_score
            + 0.20 * category_score
            + 0.20 * pop_score
        )

        recommendations.append(
            (
                idx,
                final_score
            )
        )

    recommendations.sort(
        key=lambda x: x[1],
        reverse=True
    )

    results = []

    for idx, score in recommendations[:top_n]:

        row = df.iloc[idx]

        results.append({

            "isbn":
                row["isbn13"],

            "title":
                row["title"],

            "author":
                row["authors"],

            "category":
                row["categories"],

            "description":
                row["description"],

            "rating":
                row["average_rating"],

            "year":
                row["published_year"],

            "match_score":
                round(
                    score * 100,
                    2
                )
        })

    return results