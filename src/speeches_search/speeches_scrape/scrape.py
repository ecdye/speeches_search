from typing import Callable
from concurrent.futures import ThreadPoolExecutor


import requests
from bs4 import BeautifulSoup

from ..resources import Speaker, Speech
from ..database import get_existing_talk_titles
from ..logging import get_logger


logger = get_logger()


def scrape_speakers(populate_speaker: Callable[[Speaker], None]) -> None:
    url = "https://speeches.byu.edu/speakers/"
    response = requests.get(url)

    speaker_links: list[str] = []
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        speaker_elements = soup.find_all('h3', class_='archive-listing__item')
        for element in speaker_elements:
            if link_element := element.find('a', class_='archive-item__link'):
                speaker_links.append(str(link_element['href']).rstrip('/').split('/')[-1])
                logger.info(f"Found speaker link: {link_element['href']}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(scrape_speaker, link) for link in speaker_links]
        for future in futures:
            if speaker:= future.result():
                populate_speaker(speaker)


def scrape_speaker(speaker_name: str) -> Speaker | None:
    url = f"https://speeches.byu.edu/speakers/{speaker_name}"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        # Extract relevant information about the speaker
        name = "Unknown Speaker"
        if name_element := soup.find('h1', class_='single-speaker__name'):
            name = name_element.text.strip()

        bio = "No biography available"
        if bio_element := soup.find('div', class_='single-speaker__bio-text'):
            if bio_element := bio_element.find('div', class_='expandable__element'):
                bio = bio_element.text.strip()

        talks: list[Speech] = []
        if talks_container := soup.find('section', class_='single-speaker__talks'):
            for article in talks_container.find_all('article'):
                title = "Unknown Title"
                link = "Unknown URL"
                date = "Unknown Date"
                if h2_element := article.find('h2'):
                    title = h2_element.text.strip()
                    if link_element := h2_element.find('a'):
                        link = str(link_element['href'])

                if date_element := article.find('span', class_='card__speech-date'):
                    date = date_element.text.strip()

                talks.append({
                    'title': title,
                    'date': date,
                    'url': link,
                })

        speaker = Speaker(
            name=name,
            bio=bio,
            talks=talks
        )

        existing_titles = get_existing_talk_titles(name)
        scrape_speaker_talks(speaker, existing_titles)
        logger.info(f"Scraped speaker: {speaker['name']} with {len(speaker['talks'])} talks")

        return speaker
    else:
        logger.error(f"Failed to retrieve data for {speaker_name}")
        return None


def scrape_speaker_talks(speaker: Speaker, existing_titles: set[str]) -> None:
    for talk in speaker['talks']:
        if talk['title'] in existing_titles:
            logger.info(f"Skipping already downloaded talk: {talk['title']}")
            continue
        talk_url = talk['url']
        response = requests.get(talk_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            content_element = soup.find('div', class_='single-speech__content')
            if content_element:
                for sup in content_element.find_all('sup'):  # Remove footnote markers for our text
                    if sup.string and sup.string.strip().isdigit():
                        sup.decompose()
                paragraphs = content_element.find_all('p')
                found_all_paragraphs = False
                for p in paragraphs:
                    if "The text for this speech is unavailable." in p.text.strip() or \
                       "The text of this speech is unavailable." in p.text.strip() or \
                       "The text of this speech is being edited and will be available soon." in p.text.strip():
                        logger.warning(f"Text unavailable for talk: {talk['title']} at {talk_url}")
                        paragraphs = []
                        break
                    elif "©" in p.text.strip():
                        p.decompose()
                    elif "Notes" == p.text.strip():
                        p.decompose()
                        found_all_paragraphs = True
                    elif found_all_paragraphs:
                        p.decompose()
                    elif p.text.strip() == "":
                        p.decompose()

                talk['content'] = [p.text.strip() for p in paragraphs if not p.decomposed and p.text.strip() != ""]
        else:
            logger.error(f"Failed to retrieve content for talk: {talk['title']} at {talk_url}")
