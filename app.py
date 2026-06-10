from src.recommender import recommend_books

print("\nCOLLEGE LIBRARY BOOK RECOMMENDER")
print("-" * 40)

query = input("\nEnter a book title, topic, or interest: ")

results = recommend_books(query)

print("\nTop 5 Recommended Books:\n")

for i, book in enumerate(results, start=1):
    print(f"{i}. {book['title']}")
    print(f"   Author   : {book['author']}")
    print(f"   Category : {book['category']}")
    print()