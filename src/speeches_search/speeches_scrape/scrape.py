import requests
from bs4 import BeautifulSoup

from ..resources import Speaker, Speech


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

        scrape_speaker_talks(speaker)

        return speaker
    else:
        print(f"Failed to retrieve data for {speaker_name}")
        return None


def scrape_speaker_talks(speaker: Speaker) -> None:
    for talk in speaker['talks']:
        talk_url = talk['url']
        response = requests.get(talk_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            content_element = soup.find('div', class_='single-speech__content')
            if content_element:
                paragraphs = content_element.find_all('p')
                talk['content'] = [p.text.strip() for p in paragraphs]
        else:
            print(f"Failed to retrieve content for talk: {talk['title']} at {talk_url}")
