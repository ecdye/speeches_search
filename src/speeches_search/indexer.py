import time

from next_plaid_client import IndexConfig, IndexExistsError, IndexNotFoundError, NextPlaidClient

from .resources import Speaker
from .logging import get_logger

INDEX_NAME = "speeches"
BATCH_SIZE = 64
RETRY_DELAY = 15
MAX_RETRIES = 10
logger = get_logger()


def create_speeches_index(client: NextPlaidClient) -> None:
    try:
        logger.info("Creating NextPlaid index for speeches...")
        client.create_index(INDEX_NAME, IndexConfig(nbits=4))
    except IndexExistsError:
        logger.info("NextPlaid index already exists, skipping creation.")
        pass


def index_speaker(client: NextPlaidClient, speaker: Speaker) -> None:
    for talk in speaker["talks"]:
        paragraphs = talk.get("content")
        if not paragraphs:
            continue

        talk_metadata = {
            "speaker_name": speaker["name"],
            "speech_title": talk["title"],
            "speech_date": talk["date"],
            "speech_url": talk["url"],
        }

        total = len(paragraphs)
        for start in range(0, total, BATCH_SIZE):
            end = min(start + BATCH_SIZE, total)
            batch_docs = paragraphs[start:end]
            batch_meta = [{**talk_metadata, "paragraph_index": i} for i in range(start, end)]

            try:
                if count := client.query_metadata(INDEX_NAME, "speaker_name = ? AND speech_title = ? AND paragraph_index BETWEEN ? AND ?",
                                                    [speaker["name"], talk["title"], start, end - 1]):
                    if count['count'] == end - start:
                        logger.info(
                            f"Skipping paragraphs {start} to {end} for {speaker['name']} - {talk['title']} (already indexed)")
                        continue
                    elif count['count'] > 0:
                        logger.warning(
                            f"Partial data exists for paragraphs {start} to {end} for {speaker['name']}"
                            f" - {talk['title']} (count: {count['count']})"
                        )
                        logger.warning(
                            f"Deleting existing paragraphs {start} to {end} for {speaker['name']} - {talk['title']} before re-indexing")
                        client.delete(INDEX_NAME, "speaker_name = ? AND speech_title = ? AND paragraph_index BETWEEN ? AND ?",
                                    [speaker["name"], talk["title"], start, end - 1])
            except IndexNotFoundError:
                logger.warning(f"Index not found when checking existing paragraphs for {speaker['name']} - {talk['title']}. Proceeding to add without check.")
            for attempt in range(MAX_RETRIES):
                try:
                    client.add(INDEX_NAME, batch_docs, metadata=batch_meta)
                    logger.info(f"Added paragraphs {start} to {end} for {speaker['name']} - {talk['title']}")
                    break
                except Exception:
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"Queue full, retrying in {RETRY_DELAY}s (attempt {attempt + 1}/{MAX_RETRIES})")
                        time.sleep(RETRY_DELAY)
                    else:
                        logger.error(f"Failed to add paragraphs {start} to {end}"
                                      f" for {speaker['name']} - {talk['title']} after {MAX_RETRIES} attempts")
                        raise


def delete_speaker(client: NextPlaidClient, speaker_name: str) -> None:
    client.delete(INDEX_NAME, "speaker_name = ?", [speaker_name])


def delete_speeches_index(client: NextPlaidClient) -> None:
    client.delete_index(INDEX_NAME)
    logger.info("Dropped NextPlaid speeches index.")
