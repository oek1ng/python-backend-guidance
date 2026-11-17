"""Load packaged Markdown guides and search them without external services."""

import re
from collections.abc import Iterable
from importlib.resources import files
from typing import Final

from .guide import Guide, parse_guide

_STOP_WORDS: Final[frozenset[str]] = frozenset(
    """a an and are as at be between by can code could creating do does each
    for from how i in into is it its make my not of on one or our per please
    should that the their them then these this to too use using want we what
    when where which with within without would your avoid ensure handle keep
    need prevent preserve stop trying again all include during async asyncio
    python""".split()
)


def load_guides() -> tuple[Guide, ...]:
    guides: list[Guide] = []
    directory = files("python_backend_guidance").joinpath("guides")
    for path in sorted(directory.iterdir(), key=lambda entry: entry.name):
        if not path.name.endswith(".md"):
            continue
        guides.append(parse_guide(path.read_text(encoding="utf-8"), filename=path.name))
    return tuple(guides)


def _terms(text: str) -> set[str]:
    terms: set[str] = set()
    for word in re.findall(r"[^\W_]+", text.casefold()):
        if word in _STOP_WORDS or len(word) < 2 or word.isdecimal():
            continue
        # Deliberately small English plural normalization, not an NLP stemmer.
        if len(word) > 4 and word.endswith("ies"):
            word = word[:-3] + "y"
        elif (
            len(word) > 3
            and word.endswith("s")
            and not word.endswith(("ss", "us", "is"))
        ):
            word = word[:-1]
        terms.add(word)
    return terms


def search_guides(
    query: str, guides: Iterable[Guide], *, limit: int = 5
) -> list[Guide]:
    terms = _terms(query)
    if len(terms) == 0:
        return []
    scored: list[tuple[int, int, int, Guide]] = []
    for guide in guides:
        fields = (
            (guide.id, 4),
            (" ".join(guide.tags), 4),
            (guide.title, 3),
            (guide.description, 2),
            (" ".join(guide.aliases), 4),
        )
        indexed = [(_terms(text), weight) for text, weight in fields]
        matched = terms & set().union(*(words for words, _ in indexed))
        if len(matched) < min(2, len(terms)) or len(matched) * 2 < len(terms):
            continue
        score = sum(len(terms & words) * weight for words, weight in indexed)
        # Prose only breaks relevance ties after capability metadata admits a
        # result. Examples, source URLs, and exclusion notes cannot admit it.
        body = guide.content.split("\n+++\n", 1)[-1].split("## Sources", 1)[0]
        prose = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
        scored.append((len(matched), score, len(terms & _terms(prose)), guide))
    scored.sort(key=lambda entry: (-entry[0], -entry[1], -entry[2], entry[3].id))
    return [guide for _, _, _, guide in scored[:limit]]
