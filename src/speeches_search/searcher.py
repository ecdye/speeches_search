from next_plaid_client import NextPlaidClient, SearchParams, SearchResult

INDEX_NAME = "speeches"


def search_speeches(
    client: NextPlaidClient, query: str, top_k: int = 10
) -> SearchResult:
    return client.search(INDEX_NAME, [query], params=SearchParams(top_k=top_k))


def search_by_speaker(
    client: NextPlaidClient, query: str, speaker_name: str, top_k: int = 10
) -> SearchResult:
    return client.search(
        INDEX_NAME,
        [query],
        params=SearchParams(top_k=top_k),
        filter_condition="speaker_name = ?",
        filter_parameters=[speaker_name],
    )
