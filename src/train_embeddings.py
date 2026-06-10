from sentence_transformers import SentenceTransformer
from src.preprocess import load_books
import pickle

print("Loading dataset...")

df = load_books()

print("Loading model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

print("Generating embeddings...")

embeddings = model.encode(
    df["combined"].tolist(),
    show_progress_bar=True
)

with open("models/book_embeddings.pkl", "wb") as f:
    pickle.dump(embeddings, f)

print("Embeddings saved successfully!")