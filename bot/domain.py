from typing import Literal

type Category = Literal["films", "series", "mangas"]
type MediaTypeInput = Literal["movie", "serie", "manga"]
type ScraperSource = Literal["wawacity"]

VALID_CATEGORIES: tuple[Category, ...] = ("films", "series", "mangas")
VALID_MEDIA_TYPE_INPUTS: tuple[MediaTypeInput, ...] = ("movie", "serie", "manga")
CATEGORY_TO_MEDIA_TYPE: dict[Category, MediaTypeInput] = {
    "films": "movie",
    "series": "serie",
    "mangas": "manga",
}
