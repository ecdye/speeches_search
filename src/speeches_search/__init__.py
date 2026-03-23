from next_plaid_client import NextPlaidClient
import json
import argparse

from .indexer import create_speeches_index, delete_speaker, index_speaker
from .searcher import search_by_speaker, search_speeches
from .speeches_scrape.scrape import scrape_speaker, scrape_speakers
from .resources import Speaker
from .logging import get_logger

NEXTPLAID_URL = "http://localhost:8080"
logger = get_logger()


def scrape_and_save_speeches():
    speakers = scrape_speakers()
    if not speakers:
        logger.error("Failed to scrape any speakers.")
        return

    json.dump(speakers, open("speakers.json", "w"), indent=2)


def main():
    args = argparse.ArgumentParser(description="Scrape, index, and search BYU speeches")
    args.add_argument("--scrape", action="store_true", help="Scrape speeches from the website")
    args.add_argument("--index", action="store_true", help="Index scraped speeches into NextPlaid")
    args.add_argument("--search", action="store_true", help="Search indexed speeches")
    parsed_args = args.parse_args()

    if parsed_args.scrape:
        scrape_and_save_speeches()
    elif parsed_args.index:
        speakers: list[Speaker] = json.load(open("speakers.json"))
        with NextPlaidClient(NEXTPLAID_URL) as client:
            create_speeches_index(client)
            for speaker in speakers:
                index_speaker(client, speaker)
                logger.info(f"Indexed {len(speaker['talks'])} talks for {speaker['name']}")
    elif parsed_args.search:
        with NextPlaidClient(NEXTPLAID_URL) as client:
            query = input("Enter a search query: ")
            results = search_speeches(client, query)
            for qr in results.results:
                print(f"\nSearch results for '{query}':")
                for score, meta in zip(
                     qr.scores, qr.metadata or []
                ):
                    print(f"  [{score:.4f}] {meta}")
    else:
        args.print_help()
