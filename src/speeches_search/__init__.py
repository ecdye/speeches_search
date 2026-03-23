from .speeches_scrape.scrape import scrape_speaker

def main():
    speaker = scrape_speaker("dallin-h-oaks")
    num_talks = len(speaker['talks']) if speaker else 0
    print(f"Speaker: {speaker['name'] if speaker else 'N/A'} - Number of Talks: {num_talks}")
    print(f"Biography: {speaker['bio'] if speaker else 'N/A'}")
    print("Talks:")
    if speaker:
        for talk in speaker['talks']:
            print(f"Title: {talk['title']}, Date: {talk['date']}, URL: {talk['url']}")
            print(f"Content: {talk.get('content', 'No content available')[:100]}...")  # Print first 100 characters of content

if __name__ == "__main__":
    main()
