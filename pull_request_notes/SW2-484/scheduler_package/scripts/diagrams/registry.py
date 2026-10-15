from dataclasses import dataclass
from typing import Callable


@dataclass
class Fig:
    name: str          # output file stem in figures/
    title: str         # viewer title
    doc: str           # which Markdown file shows it
    fn: Callable


FIGURES: list[Fig] = []


def figure(name: str, title: str, doc: str):
    def deco(fn):
        FIGURES.append(Fig(name, title, doc, fn))
        FIGURES.sort(key=lambda f: f.name)
        return fn
    return deco
