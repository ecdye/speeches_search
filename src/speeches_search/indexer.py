import time

from next_plaid_client import IndexConfig, IndexExistsError, NextPlaidClient

from .resources import Speaker
from .logging import get_logger

INDEX_NAME = "speeches"
BATCH_SIZE = 64
RETRY_DELAY = 30
MAX_RETRIES = 5
logger = get_logger()


def create_speeches_index(client: NextPlaidClient) -> None:
    try:
        client.create_index(INDEX_NAME, IndexConfig(nbits=4))
    except IndexExistsError:
        pass


def index_speaker(client: NextPlaidClient, speaker: Speaker) -> None:
    documents: list[str] = []
    metadata: list[dict] = []

    for talk in speaker["talks"]:
        paragraphs = talk.get("content")
        if not paragraphs:
            continue

        for i, paragraph in enumerate(paragraphs):
            documents.append(paragraph)
            metadata.append(
                {
                    "speaker_name": speaker["name"],
                    "speech_title": talk["title"],
                    "speech_date": talk["date"],
                    "speech_url": talk["url"],
                    "paragraph_index": i,
                }
            )

    total = len(documents)
    for start in range(0, total, BATCH_SIZE):
        end = start + BATCH_SIZE
        for attempt in range(MAX_RETRIES):
            try:
                client.add(INDEX_NAME, documents[start:end], metadata=metadata[start:end])
                logger.info(f"Added paragraphs {start} to {min(end, total)} for {speaker['name']}")
                break
            except Exception:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Queue full, retrying in {RETRY_DELAY}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Failed to add paragraphs {start} to {min(end, total)}"
                                  f" for {speaker['name']} after {MAX_RETRIES} attempts")
                    raise


def delete_speaker(client: NextPlaidClient, speaker_name: str) -> None:
    client.delete(INDEX_NAME, "speaker_name = ?", [speaker_name])
