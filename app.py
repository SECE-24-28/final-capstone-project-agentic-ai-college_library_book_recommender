from src.recommender import (
    recommend_books,
    explain_book,
    search_by_isbn,
    summarize_book
)

print("\nCOLLEGE LIBRARY AI ASSISTANT")
print("-" * 50)

query = input(
    "\nEnter a book title, topic, or ISBN: "
)

# ISBN Search
if query.isdigit():

    book = search_by_isbn(query)

    if book:

        print("\nBOOK FOUND")
        print("=" * 60)

        print(
            f"Title : {book['title']}"
        )

        print(
            f"Author : {book['authors']}"
        )

        print(
            f"Category : {book['categories']}"
        )

        print()

        print(
            summarize_book(book)
        )

    else:

        print(
            "\nNo book found."
        )

# Recommendation Search
else:

    results = recommend_books(
        query
    )

    print(
        "\nTop 5 Recommendations\n"
    )

    for i, book in enumerate(
        results,
        start=1
    ):

        print("=" * 70)

        print(
            f"{i}. {book['title']}"
        )

        print(
            f"Author : {book['author']}"
        )

        print(
            f"Category : {book['category']}"
        )

        print(
            f"ISBN : {book['isbn']}"
        )

        print(
            f"Match Score : {book['match_score']}%"
        )

        print()

        print(
            explain_book(
                book,
                query
            )
        )

        print()