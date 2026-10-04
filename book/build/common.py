"""Shared by the build and the checks: book.yaml, editions, and chapter loading.

The checks read chapters exactly as the build does (same pandoc call, same
edition filtering), so a check can't pass on text the build never saw.
"""
import glob, os, re, subprocess
import yaml
from bs4 import BeautifulSoup

BUILD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BUILD)
OUT = os.path.join(ROOT, "out")
SRC = os.path.join(ROOT, "src")
CHAPTERS = os.path.join(SRC, "chapters")


def load_yaml(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return yaml.safe_load(f) or default


BOOK = load_yaml(os.path.join(ROOT, "book.yaml"), {})
GLOSSARY = load_yaml(os.path.join(SRC, "glossary.yaml"), [])
CARDS = load_yaml(os.path.join(SRC, "cards.yaml"), {})


def editions():
    """{name: config}; every edition has 'file' and 'contents'."""
    eds = BOOK.get("editions") or {"book": {}}
    out = {}
    for name, cfg in eds.items():
        cfg = dict(cfg or {})
        cfg.setdefault("file", f"{re.sub(r'[^a-z0-9]+', '-', BOOK.get('title', 'book').lower()).strip('-')}-{name}.pdf")
        if not cfg.get("contents"):
            files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(CHAPTERS, "*.md")))
            cfg["contents"] = ["@cover", "@toc"] + files + ["@glossary"]
        out[name] = cfg
    return out


def chapter_files(cfg):
    return [os.path.join(CHAPTERS, c) for c in cfg["contents"] if not c.startswith("@")]


def pandoc(md):
    return subprocess.run(["pandoc", "-f", "markdown+smart-auto_identifiers", "-t", "html5", "--wrap=none"],
                          input=md, capture_output=True, text=True, check=True).stdout


def split_front_matter(md):
    m = re.match(r"(?s)^---\n(.*?)\n---\n", md)
    if not m:
        return {}, md
    return (yaml.safe_load(m.group(1)) or {}), md[m.end():]


def for_edition(soup, edition):
    """Keep `::: {.only editions="a,b"}` blocks only in the named editions.
    Pandoc writes a fenced div that opens with a heading as <section>, so
    both tags are handled here and everywhere else."""
    for d in soup.find_all(["div", "section"], class_="only"):
        names = re.split(r"[,\s]+", (d.get("data-editions") or d.get("editions") or d.get("data-edition") or "").strip())
        if edition in names:
            d.unwrap()
        else:
            d.decompose()
    return soup


def load_chapter(path, edition):
    """(front matter dict, BeautifulSoup of the chapter body for this edition)."""
    with open(path) as f:
        fm, md = split_front_matter(f.read())
    soup = BeautifulSoup(pandoc(md), "html.parser")
    return fm, for_edition(soup, edition)


def out_path(edition, kind):
    return os.path.join(OUT, f"{edition}-{kind}")
