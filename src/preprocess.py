from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_PATH = PROJECT_DIR / "data" / "books.csv"
ENHANCED_DATASET_PATH = PROJECT_DIR / "data" / "books_enhanced.csv"


def _clean_text(value: object) -> str:
    if value in (None, ""):
        return ""
    return " ".join(str(value).split())


def _ensure_base_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().fillna("")

    if "title" not in df.columns:
        df["title"] = ""
    if "authors" not in df.columns:
        df["authors"] = df.get("author", "")
    if "categories" not in df.columns:
        df["categories"] = df.get("category", "")
    if "description" not in df.columns:
        df["description"] = ""
    if "isbn13" not in df.columns:
        df["isbn13"] = df.get("isbn", "")
    if "isbn10" not in df.columns:
        df["isbn10"] = ""
    if "published_year" not in df.columns:
        df["published_year"] = df.get("year", "")
    if "average_rating" not in df.columns:
        df["average_rating"] = 0
    if "ratings_count" not in df.columns:
        df["ratings_count"] = 0
    if "publisher" not in df.columns:
        df["publisher"] = "Unknown publisher"
    if "year" not in df.columns:
        df["year"] = df["published_year"]
    if "language" not in df.columns:
        df["language"] = "English"
    if "availability" not in df.columns:
        df["availability"] = df.get("availability_status", "")
    if "copies" not in df.columns:
        df["copies"] = df.get("copies_available", "")
    if "total_copies" not in df.columns:
        df["total_copies"] = df.get("copies_total", "")
    if "expected_return" not in df.columns:
        df["expected_return"] = df.get("expected_return_date", "")
    if "shelf" not in df.columns:
        df["shelf"] = df.get("shelf_location", "")

    df["title"] = df["title"].astype(str).map(_clean_text)
    df["authors"] = df["authors"].astype(str).map(_clean_text)
    df["categories"] = df["categories"].astype(str).map(_clean_text)
    df["description"] = df["description"].astype(str).map(_clean_text)
    df["isbn13"] = df["isbn13"].astype(str).map(_clean_text)
    df["isbn10"] = df["isbn10"].astype(str).map(_clean_text)
    df["published_year"] = df["published_year"].astype(str).map(_clean_text)

    return df


def _build_keywords(row: pd.Series) -> str:
    tokens = []
    for value in [row["title"], row["authors"], row["categories"], row["description"]]:
        for token in _clean_text(value).replace(";", " ").replace(",", " ").split():
            token = token.strip().lower()
            if len(token) > 4 and token not in tokens:
                tokens.append(token)
    return ", ".join(tokens[:10])


def _difficulty_from_row(row: pd.Series) -> str:
    text = f"{row['title']} {row['categories']} {row['description']}".lower()
    if any(term in text for term in ["advanced", "research", "algorithms", "machine learning", "artificial intelligence"]):
        return "Advanced"
    if any(term in text for term in ["introduction", "beginner", "fundamentals", "basics", "primer"]):
        return "Beginner"
    return "Intermediate"


def _availability_from_row(index: int, row: pd.Series, max_ratings: int) -> dict[str, object]:
    ratings_count = int(pd.to_numeric(pd.Series([row["ratings_count"]]), errors="coerce").fillna(0).iloc[0])
    copies_total = max(3, min(24, 3 + (ratings_count // 2000) + (index % 5)))
    borrowed_count = min(copies_total, max(0, (copies_total // 2) + (index % 3)))
    copies_available = max(0, copies_total - borrowed_count)
    availability_status = "Available" if copies_available > 0 else "Borrowed"
    popularity_score = 0.0
    avg_rating = pd.to_numeric(pd.Series([row["average_rating"]]), errors="coerce").fillna(0).iloc[0]
    if max_ratings > 0:
        popularity_score = 0.4 * (float(avg_rating) / 5.0) + 0.6 * (ratings_count / max_ratings)

    return {
        "availability_status": availability_status,
        "copies_total": copies_total,
        "copies_available": copies_available,
        "borrowed_count": borrowed_count,
        "expected_return_date": ""
        if copies_available > 0
        else (datetime.today() + timedelta(days=7 + (index % 10))).strftime("%d %B %Y"),
        "shelf_location": f"A-{(index % 24) + 1:02d}-{(index % 8) + 1}",
        "popularity_score": round(min(max(popularity_score, 0.0), 1.0), 4),
    }


def _enhance_books(df: pd.DataFrame) -> pd.DataFrame:
    df = _ensure_base_columns(df)

    numeric_ratings = pd.to_numeric(df["ratings_count"], errors="coerce").fillna(0).astype(int)
    max_ratings = max(int(numeric_ratings.max()), 1)

    if "keywords" not in df.columns or df["keywords"].astype(str).str.strip().eq("").all():
        df["keywords"] = df.apply(_build_keywords, axis=1)
    if "difficulty_level" not in df.columns or df["difficulty_level"].astype(str).str.strip().eq("").all():
        df["difficulty_level"] = df.apply(_difficulty_from_row, axis=1)

    if "copies_available" not in df.columns or df["copies_available"].astype(str).str.strip().eq("").all():
        availability_rows = [
            _availability_from_row(index, row, max_ratings)
            for index, row in df.iterrows()
        ]
        availability_df = pd.DataFrame(availability_rows)
        for column in availability_df.columns:
            df[column] = availability_df[column]

    df["category"] = df["categories"]
    df["author"] = df["authors"]
    df["isbn"] = df["isbn13"]
    df["year"] = df["year"].where(df["year"].astype(str).str.strip() != "", df["published_year"])
    df["availability"] = df["availability"].where(
        df["availability"].astype(str).str.strip() != "",
        df.get("availability_status", "Available"),
    )
    df["copies"] = df["copies"].where(
        df["copies"].astype(str).str.strip() != "",
        df.get("copies_available", 0),
    )
    df["total_copies"] = df["total_copies"].where(
        df["total_copies"].astype(str).str.strip() != "",
        df.get("copies_total", df["copies"]),
    )
    df["expected_return"] = df["expected_return"].where(
        df["expected_return"].astype(str).str.strip() != "",
        df.get("expected_return_date", ""),
    )
    df["shelf"] = df["shelf"].where(
        df["shelf"].astype(str).str.strip() != "",
        df.get("shelf_location", ""),
    )
    if "target_audience" not in df.columns:
        df["target_audience"] = "College students"
    df["semantic_text"] = (
        df["title"].astype(str)
        + " "
        + df["authors"].astype(str)
        + " "
        + df["categories"].astype(str)
        + " "
        + df["description"].astype(str)
        + " "
        + df["keywords"].astype(str)
    )
    df["combined"] = df["semantic_text"]
    if "table_of_contents" not in df.columns or df["table_of_contents"].astype(str).str.strip().eq("").all():
        df["table_of_contents"] = df.apply(
            lambda row: "; ".join(
                [
                    f"Introduction to {row['title'] or 'the subject'}",
                    f"Core concepts in {row['categories'] or 'the topic'}",
                    "Applied examples and exercises",
                ]
            ),
            axis=1,
        )
    df["source"] = "books.csv"

    return df


def build_enhanced_dataset(source_path: Path = DEFAULT_DATASET_PATH, output_path: Path = ENHANCED_DATASET_PATH) -> pd.DataFrame:
    df = pd.read_csv(source_path)
    df = _enhance_books(df)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def load_books(enhanced: bool = True):
    dataset_path = ENHANCED_DATASET_PATH if enhanced and ENHANCED_DATASET_PATH.exists() else DEFAULT_DATASET_PATH
    df = pd.read_csv(dataset_path)
    return _enhance_books(df)
