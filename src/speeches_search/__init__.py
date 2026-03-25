from next_plaid_client import NextPlaidClient
import argparse

from .indexer import create_speeches_index, index_speaker
from .searcher import search_by_speaker, search_speeches
from .speeches_scrape.scrape import scrape_speakers
from .database import create_tables, populate_speaker, get_speakers_for_indexing
from .resources import Speaker
from .logging import get_logger

NEXTPLAID_URL = "http://localhost:8080"
logger = get_logger()


def scrape_and_save_speeches():
    create_tables()
    speakers = scrape_speakers()
    if not speakers:
        logger.error("Failed to scrape any speakers.")
        return

    for speaker in speakers:
        populate_speaker(speaker)


def main():
    args = argparse.ArgumentParser(description="Scrape, index, and search BYU speeches")
    args.add_argument("--scrape", action="store_true", help="Scrape speeches from the website")
    args.add_argument("--index", action="store_true", help="Index scraped speeches into NextPlaid")
    args.add_argument("--search", action="store_true", help="Search indexed speeches")
    parsed_args = args.parse_args()

    if parsed_args.scrape:
        scrape_and_save_speeches()
    elif parsed_args.index:
        speakers = get_speakers_for_indexing()
        with NextPlaidClient(NEXTPLAID_URL) as client:
            create_speeches_index(client)
            for speaker in speakers:
                index_speaker(client, speaker)
                logger.info(f"Indexed {len(speaker['talks'])} talks for {speaker['name']}")
    elif parsed_args.search:
        with NextPlaidClient(NEXTPLAID_URL) as client:
            while True:
                query = input("Enter a search query (or 'quit' to exit): ")
                if query.lower() == "quit":
                    break
                speaker = input("Filter by speaker name (leave blank for all): ").strip()
                if speaker:
                    results = search_by_speaker(client, query, speaker, top_k=5)
                else:
                    results = search_speeches(client, query, top_k=5)
                for qr in results.results:
                    print(f"\nSearch results for '{query}':")
                    for score, meta in zip(
                        qr.scores, qr.metadata or []
                    ):
                        assert meta is not None
                        print(f"  Talk: {meta.get('speech_title', 'Unknown')}"
                               f" by {meta.get('speaker_name', 'Unknown')},"
                               f" Paragraph: {meta.get('paragraph_index', 'Unknown')} [{score:.4f}]")
                        print(f"    URL: {meta.get('speech_url', 'Unknown')}\n")

    else:
        args.print_help()
