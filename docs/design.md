# BYU Speeches Search — Design Document

## Project Summary

**Purpose:**

- Provide a fast, modern, and user-friendly search engine for BYU devotional speeches.
- Allow users to search for relevant paragraphs, filter by speaker(s), and explore speeches interactively.
- Support advanced features like dark mode, infinite scroll, and multi-speaker filtering.

**Goals:**

- Make it easy to find inspirational and relevant content from BYU speeches.
- Enable deep search (semantic, not just keyword) and paragraph-level results.
- Provide a clean, modern, and accessible web interface.

## Initial ERD (Entity Relationship Diagram)

```mermaid
erDiagram
    SPEAKER ||--o{ TALK : gives
    TALK ||--o{ PARAGRAPH : contains
    SPEAKER {
        int id PK
        string name
        string bio
    }
    TALK {
        int id PK
        int speaker_id FK
        string title
        string date
        string url
    }
    PARAGRAPH {
        int id PK
        int talk_id FK
        int paragraph_index
        string content
    }
```

---

## System Design Diagram

```mermaid
graph TD
    subgraph User
        browser["Web Browser"]
    end
    subgraph Backend
        flask["Flask Web App"]
        plaid["NextPlaid/ColBERT Search Engine"]
        db[("Postgres DB")]
    end
    browser -- HTTP/HTML/JS --> flask
    flask -- REST/JSON/SQL Metadata --> plaid
    flask -- SQL --> db
```

---

## Initial Daily Goals

Spend 2-3 hours working on project.
