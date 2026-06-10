import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from src.preprocess import load_books

df = load_books()

with open("models/book_embeddings.pkl", "rb") as f:
    book_embeddings = pickle.load(f)

model = SentenceTransformer("all-MiniLM-L6-v2")


def recommend_books(query, top_n=5):
    query_embedding = model.encode([query])

    similarities = cosine_similarity(
        query_embedding,
        book_embeddings
    )[0]

    top_indices = np.argsort(similarities)[::-1][:top_n]

    results = []

    for idx in top_indices:
        results.append({
            "title": df.iloc[idx]["title"],
            "author": df.iloc[idx]["authors"],
            "category": df.iloc[idx]["categories"]
        })

    return results