#!/usr/bin/env python3
"""
Genera un feed RSS non ufficiale dei comunicati della Questura di Mantova,
a partire da:

  - due pagine di archivio sul sito questure.poliziadistato.it (sezione
    Mantova), scaricate e "parsate" con BeautifulSoup;
  - il feed RSS nazionale https://questure.poliziadistato.it/it/archivio/rss,
    filtrando solo le voci che riguardano Mantova.

Il risultato viene scritto in docs/feed.xml (RSS 2.0), pronto per essere
pubblicato con GitHub Pages.

Uso:
    python scripts/generate_feed.py
"""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime, format_datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------
# Configurazione
# --------------------------------------------------------------------------

ARCHIVE_PAGES = [
    "https://questure.poliziadistato.it/it/Mantova/archivio/view/5730dc9d1c604802219614",
    "https://questure.poliziadistato.it/it/Mantova/archivio/category/5730dc9f408ec587750440",
]

NATIONAL_RSS_URL = "https://questure.poliziadistato.it/it/archivio/rss"

# Filtro per selezionare, dal feed nazionale, solo le voci relative a Mantova
MANTOVA_KEYWORDS = ("mantova",)

FEED_TITLE = "Comunicati Questura di Mantova (non ufficiale)"
FEED_LINK = "https://questure.poliziadistato.it/it/Mantova"
FEED_DESCRIPTION = (
    "Feed RSS non ufficiale generato automaticamente a partire dalle pagine "
    "di archivio della Questura di Mantova e dal feed RSS nazionale della "
    "Polizia di Stato, filtrato sui soli comunicati relativi a Mantova."
)
# Aggiornare con l'URL reale di GitHub Pages una volta pubblicato il repo
FEED_SELF_URL = "https://mbmichele.github.io/feed_questura_mn/feed.xml"

TIMEZONE = ZoneInfo("Europe/Rome")

USER_AGENT = (
    "Mozilla/5.0 (compatible; feed-questura-mn/1.0; "
    "+https://github.com/mbmichele/feed_questura_mn)"
)

REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9",
}

# Pattern del link di dettaglio di un comunicato, es.:
#   cs_context.jsp?ID_LINK=...&id_context=1234567
DETAIL_LINK_PATTERN = re.compile(r"cs_context\.jsp\?.*id_context=", re.IGNORECASE)

# Pattern di una data italiana nel testo, es. "10 settembre 2026"
MONTHS_IT = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5,
    "giugno": 6, "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10,
    "novembre": 11, "dicembre": 12,
}
DATE_PATTERN = re.compile(
    r"\b(\d{1,2})\s+(" + "|".join(MONTHS_IT.keys()) + r")\s+(\d{4})\b",
    re.IGNORECASE,
)

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "feed.xml"

REQUEST_TIMEOUT = 20


# --------------------------------------------------------------------------
# Modello dato
# --------------------------------------------------------------------------

@dataclass
class Comunicato:
    titolo: str
    link: str
    descrizione: str
    data: datetime | None
    guid: str = field(init=False)

    def __post_init__(self) -> None:
        base = self.link if self.link else self.titolo
        self.guid = hashlib.sha1(base.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------------

def is_category_label(text: str) -> bool:
    """
    Le etichette di categoria (es. "Per il cittadino,", "Sicurezza,
    Attualità,") terminano sempre con una virgola. Vengono scartate
    a prescindere da quante e quali sono presenti, senza un elenco fisso.
    """
    text = text.strip()
    return bool(text) and text.endswith(",")


def parse_italian_date(text: str) -> datetime | None:
    match = DATE_PATTERN.search(text)
    if not match:
        return None
    day, month_name, year = match.groups()
    month = MONTHS_IT[month_name.lower()]
    try:
        return datetime(int(year), month, int(day), tzinfo=TIMEZONE)
    except ValueError:
        return None


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def fetch(url: str) -> requests.Response:
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp


# --------------------------------------------------------------------------
# Scraping delle pagine di archivio
# --------------------------------------------------------------------------

def extract_from_archive_page(html: str, page_url: str) -> list[Comunicato]:
    """
    Individua ogni comunicato a partire dai link di dettaglio
    (pattern cs_context.jsp?...id_context=...), risale al blocco di testo
    che li contiene ed estrae titolo, data, link e descrizione.
    """
    soup = BeautifulSoup(html, "html.parser")
    comunicati: list[Comunicato] = []
    seen_links: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if not DETAIL_LINK_PATTERN.search(href):
            continue

        link = requests.compat.urljoin(page_url, href)
        if link in seen_links:
            continue

        titolo = clean_text(anchor.get_text())
        if not titolo or is_category_label(titolo):
            # a volte il primo <a> trovato è in realtà l'etichetta di
            # categoria: si prova a risalire al blocco contenitore per
            # cercare un titolo migliore più sotto
            titolo = ""

        # Risale al blocco che contiene l'intero comunicato (titolo,
        # eventuali etichette di categoria, data, riassunto)
        block = anchor.find_parent(["div", "li", "article", "tr"]) or anchor.parent
        block_text_lines = []
        if block is not None:
            for el in block.stripped_strings:
                block_text_lines.append(clean_text(el))
        block_text_lines = [line for line in block_text_lines if line]

        # Scarta automaticamente le etichette di categoria (terminano
        # sempre con una virgola)
        content_lines = [
            line for line in block_text_lines if not is_category_label(line)
        ]

        if not content_lines:
            continue

        if not titolo:
            titolo = content_lines[0]

        # La data, se presente, viene individuata cercando un pattern
        # "giorno mese anno" in una qualunque delle righe del blocco
        data = None
        for line in content_lines:
            data = parse_italian_date(line)
            if data:
                break

        # La descrizione è il resto del testo del blocco, escludendo il
        # titolo, eventuali etichette di categoria e la riga di data
        descrizione_lines = [
            line for line in content_lines
            if line != titolo and not DATE_PATTERN.fullmatch(line)
        ]
        descrizione = clean_text(" ".join(descrizione_lines))

        if not titolo:
            continue

        comunicati.append(
            Comunicato(
                titolo=titolo,
                link=link,
                descrizione=descrizione or titolo,
                data=data,
            )
        )
        seen_links.add(link)

    return comunicati


def scrape_archive_pages() -> list[Comunicato]:
    risultati: list[Comunicato] = []
    for url in ARCHIVE_PAGES:
        try:
            resp = fetch(url)
        except requests.RequestException as exc:
            print(f"[WARN] impossibile scaricare {url}: {exc}", file=sys.stderr)
            continue
        risultati.extend(extract_from_archive_page(resp.text, url))
    return risultati


# --------------------------------------------------------------------------
# Feed RSS nazionale, filtrato su Mantova
# --------------------------------------------------------------------------

def matches_mantova(*parti_testo: str) -> bool:
    testo = " ".join(parti_testo).lower()
    return any(keyword in testo for keyword in MANTOVA_KEYWORDS)


def scrape_national_rss() -> list[Comunicato]:
    try:
        resp = fetch(NATIONAL_RSS_URL)
    except requests.RequestException as exc:
        print(f"[WARN] impossibile scaricare {NATIONAL_RSS_URL}: {exc}", file=sys.stderr)
        return []

    soup = BeautifulSoup(resp.content, "xml")
    comunicati: list[Comunicato] = []

    for item in soup.find_all("item"):
        titolo = clean_text(item.title.get_text() if item.title else "")
        link = clean_text(item.link.get_text() if item.link else "")
        descrizione = clean_text(
            item.description.get_text() if item.description else ""
        )
        categorie = " ".join(
            clean_text(cat.get_text()) for cat in item.find_all("category")
        )

        if not matches_mantova(titolo, descrizione, link, categorie):
            continue

        data = None
        pub_date_tag = item.find("pubDate")
        if pub_date_tag and pub_date_tag.get_text(strip=True):
            try:
                data = parsedate_to_datetime(pub_date_tag.get_text(strip=True))
                if data.tzinfo is None:
                    data = data.replace(tzinfo=TIMEZONE)
                else:
                    data = data.astimezone(TIMEZONE)
            except (TypeError, ValueError):
                data = parse_italian_date(descrizione) or parse_italian_date(titolo)
        else:
            data = parse_italian_date(descrizione) or parse_italian_date(titolo)

        if not titolo or not link:
            continue

        comunicati.append(
            Comunicato(
                titolo=titolo,
                link=link,
                descrizione=descrizione or titolo,
                data=data,
            )
        )

    return comunicati


# --------------------------------------------------------------------------
# Generazione RSS 2.0
# --------------------------------------------------------------------------

def dedup_and_sort(comunicati: list[Comunicato]) -> list[Comunicato]:
    per_link: dict[str, Comunicato] = {}
    for c in comunicati:
        if c.link not in per_link:
            per_link[c.link] = c

    def sort_key(c: Comunicato):
        return c.data or datetime(1970, 1, 1, tzinfo=TIMEZONE)

    return sorted(per_link.values(), key=sort_key, reverse=True)


def build_rss(comunicati: list[Comunicato]) -> str:
    now = datetime.now(tz=TIMEZONE)

    items_xml = []
    for c in comunicati:
        pub_date = format_datetime(c.data) if c.data else format_datetime(now)
        items_xml.append(
            "    <item>\n"
            f"      <title>{escape(c.titolo)}</title>\n"
            f"      <link>{escape(c.link)}</link>\n"
            f"      <guid isPermaLink=\"false\">{escape(c.guid)}</guid>\n"
            f"      <pubDate>{escape(pub_date)}</pubDate>\n"
            f"      <description>{escape(c.descrizione)}</description>\n"
            "    </item>"
        )

    items_block = "\n".join(items_xml)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{escape(FEED_TITLE)}</title>\n"
        f"    <link>{escape(FEED_LINK)}</link>\n"
        f"    <description>{escape(FEED_DESCRIPTION)}</description>\n"
        '    <language>it-it</language>\n'
        f"    <lastBuildDate>{escape(format_datetime(now))}</lastBuildDate>\n"
        f'    <atom:link href="{escape(FEED_SELF_URL)}" rel="self" '
        'type="application/rss+xml" />\n'
        f"{items_block}\n"
        "  </channel>\n"
        "</rss>\n"
    )


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> None:
    comunicati = scrape_archive_pages() + scrape_national_rss()
    comunicati = dedup_and_sort(comunicati)

    if not comunicati:
        print(
            "[WARN] nessun comunicato trovato: verifico che le pagine siano "
            "raggiungibili e che i pattern di parsing siano ancora validi.",
            file=sys.stderr,
        )

    rss_xml = build_rss(comunicati)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(rss_xml, encoding="utf-8")
    print(f"Scritte {len(comunicati)} voci in {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
