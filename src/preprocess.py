import pandas as pd


def load_books():
    df = pd.read_csv("data/books.csv")

    df = df.fillna("")

    df["combined"] = (
        df["title"].astype(str)
        + " "
        + df["categories"].astype(str)
        + " "
        + df["description"].astype(str)
    )

    return df