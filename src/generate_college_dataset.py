from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_DIR / "data" / "books_enhanced.csv"


CATEGORIES = [
    {
        "category": "Artificial Intelligence",
        "prefixes": ["Applied", "Modern", "Practical", "Advanced", "Foundations of"],
        "topics": ["AI", "machine learning", "neural networks", "search", "knowledge representation", "NLP"],
        "audience": "CSE students; AI engineers; ML students",
    },
    {
        "category": "Machine Learning",
        "prefixes": ["Hands-On", "Applied", "Mathematics for", "Projects in", "Production"],
        "topics": ["supervised learning", "unsupervised learning", "model evaluation", "feature engineering", "Python"],
        "audience": "ML students; data science students; AI engineers",
    },
    {
        "category": "Data Science",
        "prefixes": ["Data-Driven", "Practical", "Statistical", "Python for", "Business"],
        "topics": ["statistics", "data analysis", "visualization", "data cleaning", "predictive modeling"],
        "audience": "data science students; analysts; research students",
    },
    {
        "category": "Programming",
        "prefixes": ["Learning", "Professional", "Beginning", "Clean", "Problem Solving with"],
        "topics": ["Python", "Java", "C++", "OOP", "debugging", "software design"],
        "audience": "first-year students; CSE students; programming beginners",
    },
    {
        "category": "Database Systems",
        "prefixes": ["Database", "SQL", "Distributed", "Modern", "Designing"],
        "topics": ["SQL", "normalization", "transactions", "query optimization", "NoSQL"],
        "audience": "CSE students; backend developers; database administrators",
    },
    {
        "category": "Cybersecurity",
        "prefixes": ["Cyber", "Network", "Ethical", "Applied", "Defensive"],
        "topics": ["security", "cryptography", "penetration testing", "risk", "secure coding"],
        "audience": "cybersecurity students; CSE students; security analysts",
    },
    {
        "category": "Computer Networks",
        "prefixes": ["Computer", "Wireless", "Cloud", "Practical", "Network"],
        "topics": ["TCP/IP", "routing", "switching", "protocols", "network security"],
        "audience": "CSE students; ECE students; network engineers",
    },
    {
        "category": "Operating Systems",
        "prefixes": ["Operating", "Modern", "Linux", "Systems", "Concurrent"],
        "topics": ["processes", "memory management", "file systems", "scheduling", "Linux"],
        "audience": "CSE students; systems programmers; exam preparation students",
    },
    {
        "category": "Software Engineering",
        "prefixes": ["Software", "Agile", "Clean", "Engineering", "Testing"],
        "topics": ["requirements", "design patterns", "testing", "DevOps", "project management"],
        "audience": "CSE students; software engineers; project teams",
    },
    {
        "category": "Cloud Computing",
        "prefixes": ["Cloud", "Distributed", "Serverless", "DevOps for", "Scalable"],
        "topics": ["virtualization", "containers", "Kubernetes", "AWS", "microservices"],
        "audience": "cloud engineers; CSE students; DevOps learners",
    },
    {
        "category": "Mathematics",
        "prefixes": ["Engineering", "Discrete", "Applied", "Calculus for", "Linear"],
        "topics": ["calculus", "linear algebra", "probability", "discrete math", "optimization"],
        "audience": "engineering students; CSE students; exam preparation students",
    },
    {
        "category": "Physics",
        "prefixes": ["Engineering", "Modern", "Applied", "Fundamentals of", "University"],
        "topics": ["mechanics", "optics", "electricity", "magnetism", "quantum physics"],
        "audience": "engineering students; physics students; first-year students",
    },
    {
        "category": "Chemistry",
        "prefixes": ["Engineering", "Organic", "Physical", "Applied", "Environmental"],
        "topics": ["chemical bonding", "thermodynamics", "polymers", "materials", "environment"],
        "audience": "engineering students; chemistry students; first-year students",
    },
    {
        "category": "Electronics",
        "prefixes": ["Digital", "Analog", "Embedded", "Microcontroller", "Electronic"],
        "topics": ["circuits", "signals", "microcontrollers", "VLSI", "embedded systems"],
        "audience": "ECE students; embedded engineers; electronics students",
    },
    {
        "category": "Electrical Engineering",
        "prefixes": ["Electrical", "Power", "Control", "Machines", "Renewable"],
        "topics": ["power systems", "control systems", "machines", "circuits", "renewable energy"],
        "audience": "EEE students; electrical engineers; engineering students",
    },
    {
        "category": "Mechanical Engineering",
        "prefixes": ["Mechanical", "Thermal", "Manufacturing", "Fluid", "Machine"],
        "topics": ["thermodynamics", "fluid mechanics", "machine design", "manufacturing", "CAD"],
        "audience": "mechanical students; design engineers; production engineers",
    },
    {
        "category": "Civil Engineering",
        "prefixes": ["Civil", "Structural", "Geotechnical", "Transportation", "Construction"],
        "topics": ["structures", "concrete", "soil mechanics", "surveying", "construction management"],
        "audience": "civil students; site engineers; structural engineers",
    },
    {
        "category": "MBA",
        "prefixes": ["Managerial", "Strategic", "Business", "Marketing", "Operations"],
        "topics": ["management", "marketing", "finance", "operations", "strategy"],
        "audience": "MBA students; managers; entrepreneurs",
    },
    {
        "category": "Economics",
        "prefixes": ["Principles of", "Managerial", "Development", "Indian", "Applied"],
        "topics": ["microeconomics", "macroeconomics", "markets", "policy", "development"],
        "audience": "commerce students; MBA students; economics students",
    },
    {
        "category": "Communication Skills",
        "prefixes": ["Technical", "Business", "Professional", "Academic", "Workplace"],
        "topics": ["presentation", "writing", "interviews", "group discussion", "reports"],
        "audience": "all college students; placement students; first-year students",
    },
    {
        "category": "Research Methodology",
        "prefixes": ["Research", "Academic", "Quantitative", "Qualitative", "Project"],
        "topics": ["literature review", "methodology", "citations", "survey design", "data collection"],
        "audience": "final-year students; research students; faculty",
    },
    {
        "category": "Environmental Science",
        "prefixes": ["Environmental", "Sustainable", "Climate", "Green", "Ecology"],
        "topics": ["sustainability", "pollution", "climate change", "biodiversity", "waste management"],
        "audience": "all college students; environmental science students; project teams",
    },
]

PUBLISHERS = [
    "Pearson",
    "McGraw Hill",
    "Oxford University Press",
    "Cambridge University Press",
    "MIT Press",
    "O'Reilly Media",
    "Springer",
    "Wiley",
    "Apress",
    "PHI Learning",
]

AUTHORS = [
    "A. Sharma",
    "R. Kumar",
    "S. Iyer",
    "Meera Nair",
    "K. Srinivasan",
    "Priya Menon",
    "Daniel Roberts",
    "Nisha Verma",
    "Arun Patel",
    "Leena Thomas",
]


def _isbn(index: int) -> str:
    return f"97893{index + 10000000:08d}"


def _difficulty(index: int, category: str) -> str:
    if category in {"Artificial Intelligence", "Machine Learning", "Operating Systems", "Cybersecurity"} and index % 3 == 0:
        return "Advanced"
    if index % 5 == 0:
        return "Beginner"
    return "Intermediate"


def _row(index: int) -> dict[str, object]:
    group = CATEGORIES[index % len(CATEGORIES)]
    topic = group["topics"][index % len(group["topics"])]
    prefix = group["prefixes"][index % len(group["prefixes"])]
    category = group["category"]
    sequence = (index // len(CATEGORIES)) + 1
    title = f"{prefix} {category}: {topic.title()} Casebook {sequence}"
    year = 2014 + (index % 13)
    total_copies = 2 + (index % 8)
    copies = 0 if index % 7 == 0 else 1 + (index % total_copies)
    copies = min(copies, total_copies)
    borrowed = total_copies - copies + (index % 13)
    expected_return = "" if copies else (date(2026, 6, 12) + timedelta(days=2 + (index % 21))).isoformat()
    difficulty = _difficulty(index, category)
    topics = group["topics"]
    description = (
        f"{title} is designed for college library users studying {category}. "
        f"It explains {topics[0]}, {topics[1]}, and {topics[2]} with examples, exercises, and project-oriented cases. "
        f"The book is useful for semester study, lab preparation, interviews, and capstone project reference."
    )
    return {
        "isbn": _isbn(index),
        "isbn13": _isbn(index),
        "isbn10": str(8100000000 + index),
        "title": title,
        "author": AUTHORS[index % len(AUTHORS)],
        "authors": AUTHORS[index % len(AUTHORS)],
        "category": category,
        "categories": category,
        "publisher": PUBLISHERS[index % len(PUBLISHERS)],
        "year": year,
        "published_year": year,
        "description": description,
        "keywords": "; ".join([category, topic, *topics]),
        "language": "English",
        "availability": "Available" if copies else "Borrowed",
        "availability_status": "Available" if copies else "Borrowed",
        "copies": copies,
        "copies_available": copies,
        "total_copies": total_copies,
        "copies_total": total_copies,
        "borrowed_count": borrowed,
        "expected_return": expected_return,
        "expected_return_date": expected_return,
        "shelf": f"{chr(65 + (index % 6))}-{(index % 24) + 1:02d}-{(index % 8) + 1}",
        "shelf_location": f"{chr(65 + (index % 6))}-{(index % 24) + 1:02d}-{(index % 8) + 1}",
        "popularity_score": round(0.45 + ((index * 17) % 55) / 100, 2),
        "difficulty_level": difficulty,
        "target_audience": group["audience"],
        "table_of_contents": "; ".join(
            [
                f"Introduction to {category}",
                f"Core concepts in {topic}",
                f"Tools and methods for {topics[1]}",
                "Solved examples",
                "Mini project and assessment questions",
            ]
        ),
        "average_rating": round(3.4 + ((index * 7) % 16) / 10, 2),
        "ratings_count": 50 + ((index * 97) % 9500),
        "source": "generated_college_dataset",
    }


def generate_dataset(count: int = 1000, output_path: Path = OUTPUT_PATH) -> pd.DataFrame:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(_row(index) for index in range(count))
    df.to_csv(output_path, index=False)
    return df


if __name__ == "__main__":
    generated = generate_dataset()
    print(f"Generated {len(generated)} rows at {OUTPUT_PATH}")
