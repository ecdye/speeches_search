import psycopg
from psycopg.rows import dict_row, DictRow

from .resources import Speaker
from .logging import get_logger

DATABASE_URL = "postgresql://speeches:speeches@localhost:5432/speeches"
logger = get_logger()


def get_connection() -> psycopg.Connection[DictRow]:
    return psycopg.Connection[DictRow].connect(DATABASE_URL, row_factory=dict_row)


def create_tables():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS speaker (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                bio TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS talk (
                id SERIAL PRIMARY KEY,
                speaker_id INTEGER NOT NULL REFERENCES speaker(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                url TEXT NOT NULL,
                UNIQUE(speaker_id, title)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS paragraph (
                id SERIAL PRIMARY KEY,
                talk_id INTEGER NOT NULL REFERENCES talk(id) ON DELETE CASCADE,
                paragraph_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                UNIQUE(talk_id, paragraph_index)
            )
        """)
        conn.commit()
        logger.info("Database tables created.")


def drop_tables():
    with get_connection() as conn:
        conn.execute("DROP TABLE IF EXISTS paragraph CASCADE")
        conn.execute("DROP TABLE IF EXISTS talk CASCADE")
        conn.execute("DROP TABLE IF EXISTS speaker CASCADE")
        conn.commit()
        logger.info("All database tables dropped.")


def populate_from_speakers(speakers: list[Speaker]):
    with get_connection() as conn:
        for speaker in speakers:
            _populate_speaker(conn, speaker)
            logger.info(f"Populated {len(speaker['talks'])} talks for {speaker['name']}")

        conn.commit()
        logger.info("Database population complete.")


def populate_speaker(speaker: Speaker):
    with get_connection() as conn:
        _populate_speaker(conn, speaker)
        conn.commit()
        logger.info(f"Populated {len(speaker['talks'])} talks for {speaker['name']}")


def _populate_speaker(conn, speaker: Speaker):
    row = conn.execute(
        """
        INSERT INTO speaker (name, bio) VALUES (%s, %s)
        ON CONFLICT (name) DO UPDATE SET bio = EXCLUDED.bio
        RETURNING id
        """,
        (speaker["name"], speaker["bio"]),
    ).fetchone()
    assert row is not None
    speaker_id = row["id"]

    for talk in speaker["talks"]:
        row = conn.execute(
            """
            INSERT INTO talk (speaker_id, title, date, url)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (speaker_id, title) DO UPDATE SET date = EXCLUDED.date, url = EXCLUDED.url
            RETURNING id
            """,
            (speaker_id, talk["title"], talk["date"], talk["url"]),
        ).fetchone()
        assert row is not None
        talk_id = row["id"]

        paragraphs = talk.get("content")
        if not paragraphs:
            continue

        for i, paragraph in enumerate(paragraphs):
            conn.execute(
                """
                INSERT INTO paragraph (talk_id, paragraph_index, content)
                VALUES (%s, %s, %s)
                ON CONFLICT (talk_id, paragraph_index) DO UPDATE SET content = EXCLUDED.content
                """,
                (talk_id, i, paragraph),
            )


def get_all_speakers() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT id, name FROM speaker ORDER BY name").fetchall()
        return rows


def get_paragraph_content(speaker_name: str, speech_title: str, paragraph_index: int) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT p.content
            FROM paragraph p
            JOIN talk t ON p.talk_id = t.id
            JOIN speaker s ON t.speaker_id = s.id
            WHERE s.name = %s AND t.title = %s AND p.paragraph_index = %s
            """,
            (speaker_name, speech_title, paragraph_index),
        ).fetchone()
        return row["content"] if row else None


def get_talks_by_speaker(speaker_name: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT t.id, t.title, t.date, t.url
            FROM talk t
            JOIN speaker s ON t.speaker_id = s.id
            WHERE s.name = %s
            ORDER BY t.title
            """,
            (speaker_name,),
        ).fetchall()
        return rows


def get_speakers_for_indexing() -> list[Speaker]:
    with get_connection() as conn:
        speaker_rows = conn.execute("SELECT id, name, bio FROM speaker ORDER BY name").fetchall()
        speakers: list[Speaker] = []
        for sr in speaker_rows:
            talk_rows = conn.execute(
                "SELECT id, title, date, url FROM talk WHERE speaker_id = %s ORDER BY title",
                (sr["id"],),
            ).fetchall()
            talks = []
            for tr in talk_rows:
                para_rows = conn.execute(
                    "SELECT content FROM paragraph WHERE talk_id = %s ORDER BY paragraph_index",
                    (tr["id"],),
                ).fetchall()
                if len(para_rows) == 0:
                    logger.warning(f"No paragraphs found for talk: {tr['title']} by {sr['name']}, skipping")
                    continue
                talks.append({
                    "title": tr["title"],
                    "date": tr["date"],
                    "url": tr["url"],
                    "content": [pr["content"] for pr in para_rows],
                })
            speakers.append(Speaker(name=sr["name"], bio=sr["bio"], talks=talks))
        return speakers


def get_existing_talk_titles(speaker_name: str) -> set[str]:
    """Return titles of talks that already have paragraph content in the DB."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT t.title
            FROM talk t
            JOIN speaker s ON t.speaker_id = s.id
            JOIN paragraph p ON p.talk_id = t.id
            WHERE s.name = %s
            GROUP BY t.title
            """,
            (speaker_name,),
        ).fetchall()
        return {r["title"] for r in rows}
