from typing import TypedDict, NotRequired


class Speech(TypedDict):
    title: str
    date: str
    url: str
    content: NotRequired[list[str]]


class Speaker(TypedDict):
    name: str
    bio: str
    talks: list[Speech]
