from dataclasses import dataclass, field


@dataclass
class Section:
    """One source's part of the newsletter."""

    name: str
    stories: list
    summary: str | None = None
    paywalled_urls: set = field(default_factory=set)
    failed: bool = False
