# 📚 Library Book Recommendation System
### An Agentic AI Project using Claude API

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Project Title & Objective](#project-title--objective)
3. [Tech Stack](#tech-stack)
4. [System Architecture](#system-architecture)
5. [Agentic AI Concepts Used](#agentic-ai-concepts-used)
6. [Features](#features)
7. [File Structure](#file-structure)
8. [How It Works — Step by Step](#how-it-works--step-by-step)
9. [API Integration](#api-integration)
10. [Prompt Engineering](#prompt-engineering)
11. [UI & Frontend Design](#ui--frontend-design)
12. [Sample Input & Output](#sample-input--output)
13. [Error Handling](#error-handling)
14. [How to Run / Deploy](#how-to-run--deploy)
15. [Future Enhancements](#future-enhancements)
16. [Learning Outcomes](#learning-outcomes)
17. [References](#references)

---

## Project Overview

The **Library Book Recommendation System** is an Agentic AI application that acts as an intelligent virtual librarian. When a user provides a topic of interest and optionally selects a genre, the system invokes the **Claude AI API** (Anthropic) to reason about the user's needs and return exactly **5 curated, personalised book recommendations** — complete with titles, authors, reasons for recommendation, and descriptive tags.

This project demonstrates core **Agentic AI** principles: a user provides high-level intent, and an AI agent autonomously reasons, plans, and delivers structured, actionable output.

---

## Project Title & Objective

**Title:** Library Book Recommendation System using Agentic AI

**Objective:**
> To build an intelligent, conversational recommendation system that uses an AI agent (Claude) to understand user interests and recommend 5 relevant books with personalised justifications, simulating the experience of consulting a knowledgeable librarian.

**Key Goals:**
- Understand and apply the concept of an AI agent acting on behalf of a user
- Integrate the Anthropic Claude API for natural language reasoning
- Design a clean, accessible, and interactive user interface
- Parse and render structured AI output (JSON) as a polished UI
- Implement robust error handling for real-world reliability

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| AI / LLM | Anthropic Claude API (`claude-sonnet-4-20250514`) |
| Fonts | Google Fonts — Playfair Display, DM Sans |
| Icons | Tabler Icons (outline webfont) |
| Hosting | Claude.ai Artifacts (iframe sandbox) |
| API Protocol | REST — `POST /v1/messages` |

---

## System Architecture

```
┌──────────────────────────────────────────────────────┐
│                    USER INTERFACE                     │
│  ┌──────────────┐   ┌────────────┐   ┌────────────┐  │
│  │ Interest     │   │  Genre     │   │ Recommend  │  │
│  │ Text Input   │   │  Dropdown  │   │   Button   │  │
│  └──────────────┘   └────────────┘   └────────────┘  │
└───────────────────────────┬──────────────────────────┘
                            │ User submits query
                            ▼
┌──────────────────────────────────────────────────────┐
│                  JAVASCRIPT LAYER                     │
│  - Reads user input (interest + genre)               │
│  - Constructs structured prompt                      │
│  - Calls Anthropic API via fetch()                   │
│  - Parses JSON response                              │
│  - Renders book cards to DOM                         │
└───────────────────────────┬──────────────────────────┘
                            │ POST /v1/messages
                            ▼
┌──────────────────────────────────────────────────────┐
│              ANTHROPIC CLAUDE API                     │
│  Model: claude-sonnet-4-20250514                     │
│  - Receives structured prompt                        │
│  - Reasons about user's interest                     │
│  - Selects 5 appropriate books                       │
│  - Returns structured JSON array                     │
└───────────────────────────┬──────────────────────────┘
                            │ JSON response
                            ▼
┌──────────────────────────────────────────────────────┐
│                  RENDERED OUTPUT                      │
│  5 Book Cards — each with:                           │
│    • Title & Author                                  │
│    • Personalised Reason                             │
│    • Genre/Mood Tags                                 │
│    • Colour-coded Book Spine                         │
└──────────────────────────────────────────────────────┘
```

---

## Agentic AI Concepts Used

This project directly applies the following Agentic AI concepts:

### 1. Goal-Directed Behaviour
The agent is given a high-level user goal ("recommend books about X") and autonomously decides *which* books to select and *why* — without being explicitly told which books exist.

### 2. Reasoning & Planning
Claude internally reasons: "The user is interested in X. Given genre preference Y, which 5 books best serve their curiosity, learning goals, or entertainment needs?" — this is implicit chain-of-thought planning.

### 3. Structured Output Generation
The agent is instructed to produce output in a strict JSON schema. This is a key agentic pattern: the LLM's output becomes machine-readable data that drives downstream UI rendering.

### 4. Tool Use Simulation
The Anthropic API call acts as an *agent invocation* — the frontend "delegates" the recommendation task to an intelligent agent and awaits its structured response.

### 5. Single-Turn Agent Loop
This project implements a **single-turn agentic loop**:
```
User Intent → Agent Activation → Reasoning → Structured Output → UI Render
```

---

## Features

- **Natural Language Input** — Users describe their interest in plain English
- **Genre Filtering** — Optional genre dropdown (Fiction, Sci-fi, Mystery, Biography, History, etc.)
- **AI-Powered Recommendations** — 5 books recommended by Claude with personalised justifications
- **Structured JSON Parsing** — AI output is parsed and rendered as interactive cards
- **Book Tags** — Each book includes mood/theme tags for quick scanning
- **Animated UI** — Staggered fade-in animations for each book card reveal
- **Loading States** — Rotating status messages during AI inference
- **Error Handling** — Graceful fallback UI when the API fails
- **Enter Key Support** — Press Enter in the text field to trigger recommendation
- **Colour-Coded Spines** — Visual variety across the 5 book cards
- **Accessible Design** — Screen-reader friendly with ARIA labels and `sr-only` headings

---

## File Structure

```
library-book-recommender/
│
├── index.html          # Main application file (self-contained)
│   ├── <style>         # All CSS — design tokens, layout, animations
│   ├── <body>          # HTML structure — input form, status bar, book grid
│   └── <script>        # JavaScript — API call, JSON parsing, DOM rendering
│
└── README.md           # This file
```

> Note: The application is intentionally built as a single-file artifact for portability and easy deployment inside Claude.ai.

---

## How It Works — Step by Step

### Step 1 — User Input
The user types their interest (e.g., *"ancient civilisations"*) and optionally selects a genre from the dropdown (e.g., *"History"*).

### Step 2 — Prompt Construction
JavaScript builds a structured natural language prompt:
```
You are a knowledgeable librarian. A library patron is interested in:
"ancient civilisations". Genre preference: history.

Recommend exactly 5 books. Respond ONLY with a JSON array...
```

### Step 3 — API Call
The prompt is sent to the Anthropic Claude API via a `fetch()` POST request to `https://api.anthropic.com/v1/messages`.

### Step 4 — AI Reasoning
Claude processes the prompt and returns a JSON array of 5 books, each with:
- `title` — Book title
- `author` — Author's full name
- `reason` — 2-3 sentence personalised justification
- `tags` — Array of 2-4 descriptive tags

### Step 5 — Parsing & Rendering
JavaScript strips any markdown fences from the response, parses the JSON, and dynamically renders 5 book cards in the UI with staggered animation delays.

### Step 6 — Display
The user sees 5 beautifully presented book recommendations, each with a coloured spine icon, title, author, reason, and tags.

---

## API Integration

### Endpoint
```
POST https://api.anthropic.com/v1/messages
```

### Request Body
```json
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 1000,
  "messages": [
    {
      "role": "user",
      "content": "<constructed prompt>"
    }
  ]
}
```

### Response Structure
```json
{
  "content": [
    {
      "type": "text",
      "text": "[{\"title\":\"...\",\"author\":\"...\",\"reason\":\"...\",\"tags\":[...]}]"
    }
  ]
}
```

### Response Extraction
```javascript
const raw = data.content
  ?.filter(b => b.type === 'text')
  .map(b => b.text)
  .join('');

const clean = raw.replace(/```json|```/g, '').trim();
const books = JSON.parse(clean);
```

---

## Prompt Engineering

The system uses a **role-based, constrained output prompt** — a key technique in agentic AI development.

### Prompt Template
```
You are a knowledgeable librarian. A library patron is interested in: "{interest}".
{genreNote}

Recommend exactly 5 books. Respond ONLY with a JSON array (no markdown, no preamble):
[
  {
    "title": "Book Title",
    "author": "Author Name",
    "reason": "2-3 sentence personalised reason why this book matches the patron's interest",
    "tags": ["tag1", "tag2", "tag3"]
  }
]
```

### Why This Prompt Works Well

| Technique | Purpose |
|-----------|---------|
| Role assignment (`"You are a knowledgeable librarian"`) | Sets persona and domain expertise |
| Explicit count (`"exactly 5 books"`) | Prevents under/over-generation |
| `"Respond ONLY with a JSON array"` | Forces structured, parseable output |
| `"no markdown, no preamble"` | Prevents JSON wrapped in code fences or prose |
| Personalised reason field | Grounds recommendations in user's stated interest |
| Tags field | Adds scannability and metadata |

---

## UI & Frontend Design

### Design Philosophy
The UI follows an **editorial / warm library aesthetic** — combining the classical feel of a library with modern, clean digital design.

### Typography
- **Playfair Display** — Serif display font for book titles and headings; evokes the classic feel of printed books
- **DM Sans** — Clean sans-serif for body text, labels, and UI elements

### Colour Palette
- **Book Spine Background:** `#2C1810` (dark walnut brown)
- **Spine Text:** `#F5E6D0` (aged paper cream)
- **Book Spines:** 5 rotating pastel colours (purple, teal, coral, blue, amber) from CSS design tokens
- **Surfaces:** CSS variables for automatic light/dark mode support

### Key UI Components
- **Header** — Icon + title + subtitle
- **Input Row** — Text field + genre select + recommend button
- **Status Bar** — Animated dot + rotating loading messages
- **Book Cards** — Spine icon + book number + title + author + reason + tags
- **Empty State** — Placeholder with icon when no books are loaded
- **Error Box** — Danger-styled error message for API failures

### Animations
- Cards fade up with staggered delays (`animation-delay: N * 80ms`)
- Loading dot pulses (`opacity` keyframe animation)
- Button hover uses `opacity` transition

---

## Sample Input & Output

### Input
```
Interest: "dystopian societies and human resistance"
Genre:    Fiction
```

### Output (AI-generated JSON, rendered as cards)
```json
[
  {
    "title": "1984",
    "author": "George Orwell",
    "reason": "A foundational dystopian novel exploring totalitarian control and one man's desperate resistance against a surveillance state. Its themes of doublethink, propaganda, and suppressed rebellion are directly relevant to your interest.",
    "tags": ["dystopia", "totalitarianism", "classic", "political"]
  },
  {
    "title": "The Handmaid's Tale",
    "author": "Margaret Atwood",
    "reason": "Set in the theocratic Republic of Gilead, this novel follows Offred's quiet but determined resistance in a world where women have lost all autonomy. A powerful meditation on power, identity, and survival.",
    "tags": ["dystopia", "feminism", "resistance", "speculative"]
  },
  ...
]
```

---

## Error Handling

The application handles the following failure scenarios:

| Scenario | Handling |
|----------|---------|
| Empty input field | Input gains focus; no API call made |
| API network failure | `catch` block shows error card + error box |
| Malformed JSON response | `JSON.parse` throws; caught and shown as error |
| Empty books array | Explicit check throws and shows error state |
| API rate limit / auth error | Generic error message displayed |

```javascript
try {
  const res = await fetch('https://api.anthropic.com/v1/messages', { ... });
  const data = await res.json();
  const books = JSON.parse(clean);
  if (!Array.isArray(books) || books.length === 0) throw new Error('No books returned');
  // render books...
} catch (err) {
  errorBox.textContent = 'Something went wrong. Please try again.';
  errorBox.style.display = 'block';
}
```

---

## How to Run / Deploy

### Option 1 — Claude.ai Artifact (Current Setup)
The application runs as a self-contained artifact inside Claude.ai. The Anthropic API key is handled automatically by the platform — no configuration needed.

### Option 2 — Local HTML File
1. Save the full HTML as `index.html`
2. Add your Anthropic API key to the `fetch()` headers:
   ```javascript
   headers: {
     'Content-Type': 'application/json',
     'x-api-key': 'YOUR_API_KEY_HERE',
     'anthropic-version': '2023-06-01'
   }
   ```
3. Open `index.html` in a browser — note that CORS restrictions may apply; use a local server:
   ```bash
   npx serve .
   # or
   python -m http.server 8080
   ```

### Option 3 — Deploy to Netlify / Vercel
1. Wrap the API call in a serverless function to keep the API key server-side
2. Deploy static files to Netlify / Vercel
3. Call your serverless proxy endpoint instead of the Anthropic API directly

---

## Future Enhancements

| Feature | Description |
|---------|-------------|
| Multi-turn conversation | Let users ask follow-up questions like "Can you suggest something shorter?" |
| Save favourites | Persist liked books to localStorage or a backend |
| Book cover images | Fetch cover art from Open Library API |
| Reading level filter | Add a filter for children, YA, adult audiences |
| Export list | Download recommendations as PDF or send via email |
| Voice input | Use Web Speech API for hands-free queries |
| Goodreads integration | Link each recommendation to its Goodreads page |
| Feedback loop | Thumbs up/down per card to refine future recommendations |
| Multi-agent pipeline | One agent selects books, another writes reviews, a third fact-checks |

---

## Learning Outcomes

By building this project, you will have learned:

1. **Agentic AI fundamentals** — How to design a system where an AI agent acts autonomously on user intent
2. **Anthropic Claude API** — How to make POST requests, pass prompts, and parse model responses
3. **Prompt engineering** — Role prompting, output constraints, and JSON schema enforcement
4. **Structured output parsing** — Handling LLM-generated JSON safely in production code
5. **Frontend development** — Building accessible, animated, responsive UIs with vanilla HTML/CSS/JS
6. **Error handling** — Gracefully managing network failures and malformed AI outputs
7. **Design thinking** — Applying typography, colour, and layout to create a polished user experience

---

## References

- [Anthropic Claude API Documentation](https://docs.anthropic.com)
- [Claude Models Overview](https://docs.anthropic.com/en/docs/about-claude/models)
- [Prompt Engineering Guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)
- [Agentic AI Overview — Anthropic](https://www.anthropic.com/research)
- [Tabler Icons](https://tabler.io/icons)
- [Google Fonts — Playfair Display](https://fonts.google.com/specimen/Playfair+Display)
- [Google Fonts — DM Sans](https://fonts.google.com/specimen/DM+Sans)

---

> **Project by:** [Your Name]  
> **Course / Module:** Agentic AI  
> **Submission Date:** June 2026  
> **Model Used:** Claude Sonnet 4 (`claude-sonnet-4-20250514`)

