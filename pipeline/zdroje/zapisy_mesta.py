"""Zdroj: zápisy rady a zastupitelstva na webu města (PDF s textovou vrstvou).

Stránka s výpisem zápisů obsahuje odkazy na `/uploads/news/id<N>/<soubor>.pdf`.
Stahujeme jen dokumenty, které nemáme, nebo které podle plánu (`pipeline.verze`) čekají na kontrolu.
Stránky jsou odkazy z `STRANKY`; síť a extrakci textu lze v testech nahradit (`ziskej`, `extrahuj`).

POZOR: struktura HTML je zatím ověřena jen na vzorku (`tests/vzorky/`); z GitHub Actions
stahování z webu města zatím ověřeno nebylo (viz AGENTS.md, Neověřeno / TODO).
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin

from pipeline import verze
from pipeline.zdroje import ChybaZdroje, Dokument, Stazeno, Zdroj

STRANKY = (
    ("zapis_rada", "rm", "https://www.mesto-trebon.cz/cz/mestsky-urad-trebon/samosprava-mesta/rada-mesta/"
                         "zapisy-z-jednani-rady-mesta/volebni-obdobi-2026---2030.html"),
    ("zapis_zm", "zm", "https://www.mesto-trebon.cz/cz/mestsky-urad-trebon/samosprava-mesta/zastupitelstvo-mesta/"
                       "zapisy-zastupitelstva-mesta/volebni-obdobi-2026---2030-2.html"),
)
USER_AGENT = "radnice-pipeline/1.0"
MIN_ZNAKU = 200            # méně textu v celém PDF = pravděpodobně sken nebo prázdný dokument
POKLES = 0.5               # nabídka zdroje pod touto částí dosavadního počtu = podezřelý pokles
RE_DATUM_TEXT = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")
RE_DATUM_SOUBOR = re.compile(r"-(\d{2})-(\d{2})-(\d{2})(?:-[A-Za-z])?\.pdf$")


class _Odkazy(HTMLParser):
    def __init__(self):
        super().__init__()
        self.odkazy: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.odkazy.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


def datum_zapisu(text: str, soubor: str) -> str | None:
    """Datum jednání z názvu odkazu („ze dne 04.11.2026“), jinak z názvu souboru (Z-1-26-11-04.pdf)."""
    m = RE_DATUM_TEXT.search(text)
    if m:
        d, mm, r = map(int, m.groups())
        return f"{r:04d}-{mm:02d}-{d:02d}"
    m = RE_DATUM_SOUBOR.search(soubor)
    if m:
        r, mm, d = map(int, m.groups())
        return f"{2000 + r:04d}-{mm:02d}-{d:02d}"
    return None


def parsuj_stranku(html: str, url_stranky: str, typ: str, organ: str) -> tuple[list[Dokument], list[str]]:
    """Najde odkazy na PDF zápisů. Vrací (dokumenty bez obsahu, upozornění)."""
    p = _Odkazy()
    p.feed(html)
    dokumenty, upozorneni, videno = [], [], set()
    for href, text in p.odkazy:
        if "/uploads/news/" not in href or not href.lower().endswith(".pdf"):
            continue
        url = urljoin(url_stranky, href)
        if url in videno:
            continue
        videno.add(url)
        datum = datum_zapisu(text, url)
        if datum is None:
            upozorneni.append(f"odkaz bez data jednání přeskočen: {url}")
            continue
        dokumenty.append(Dokument(
            dokument_id=f"zapis-{organ}-{datum}", typ=typ, jednani_id=f"{organ}-{datum}",
            nazev=text or url.rsplit("/", 1)[-1], url=url, stranka_zdroje=url_stranky))
    return dokumenty, upozorneni


def ziskej_url(url: str) -> bytes:
    pozadavek = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(pozadavek, timeout=60) as odpoved:
            return odpoved.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ChybaZdroje(f"{url}: {e}") from e


def extrahuj_pdftotext(obsah: bytes) -> list[str]:
    """Text po stranách: `pdftotext -layout` odděluje strany znakem \\f."""
    try:
        vysledek = subprocess.run(["pdftotext", "-layout", "-", "-"], input=obsah, capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ChybaZdroje(f"pdftotext selhal: {e}") from e
    if vysledek.returncode != 0:
        raise ChybaZdroje("pdftotext selhal: " + vysledek.stderr.decode("utf-8", "replace")[:200])
    strany = vysledek.stdout.decode("utf-8").split("\f")
    if strany and not strany[-1].strip():
        strany.pop()
    return strany


class ZapisyMesta(Zdroj):
    nazev = "zapisy_mesta"
    typy = ("zapis_rada", "zapis_zm")

    def __init__(self, ziskej=ziskej_url, extrahuj=extrahuj_pdftotext, stranky=STRANKY, pauza: float = 1.0):
        self.ziskej, self.extrahuj, self.stranky, self.pauza = ziskej, extrahuj, stranky, pauza

    def stahni(self, manifest: list[dict], dnes) -> Stazeno:
        nabidka: list[Dokument] = []
        upozorneni: list[str] = []
        for typ, organ, url in self.stranky:
            html = self.ziskej(url).decode("utf-8", "replace")
            d, u = parsuj_stranku(html, url, typ, organ)
            nabidka += d
            upozorneni += u
        mame = {z["dokument_id"]: z for z in manifest}
        splatne = {z["dokument_id"] for z in verze.k_kontrole(manifest, dnes)}
        nabizene = {d.dokument_id for d in nabidka}
        for z in manifest:
            if z.get("typ") in self.typy and z["dokument_id"] not in nabizene:
                upozorneni.append(f"{z['dokument_id']}: zdroj ho už nenabízí (data zůstávají)")
        stazeno = Stazeno(odkazu=len(nabidka), upozorneni=upozorneni)
        for d in nabidka:
            z = mame.get(d.dokument_id)
            if z is not None and d.dokument_id not in splatne and z.get("url") == d.url:
                continue
            if stazeno.dokumenty and self.pauza:
                time.sleep(self.pauza)       # šetrné stahování
            obsah = self.ziskej(d.url)
            d.sha256, d.bytes = hashlib.sha256(obsah).hexdigest(), len(obsah)
            d.je_pdf = obsah.startswith(b"%PDF")
            if d.je_pdf and not (z and z["sha256"] == d.sha256):
                d.strany = self.extrahuj(obsah)
            stazeno.dokumenty.append(d)
        return stazeno

    def zkontroluj(self, stazeno: Stazeno, manifest: list[dict]) -> list[str]:
        chyby = []
        dosud = [z for z in manifest if z.get("typ") in self.typy]
        if stazeno.odkazu == 0:
            chyby.append(f"{self.nazev}: stránka neobsahuje žádné zápisy (prázdná nebo změněná stránka?)")
        elif len(dosud) >= 2 and stazeno.odkazu < len(dosud) * POKLES:
            chyby.append(f"{self.nazev}: prudký pokles nabídky ({stazeno.odkazu} proti dosavadním {len(dosud)})")
        jednani = [d.jednani_id for d in stazeno.dokumenty]
        for j in sorted({j for j in jednani if jednani.count(j) > 1}):
            chyby.append(f"{self.nazev}: k jednání {j} je víc dokumentů")
        mame = {z["dokument_id"]: z for z in manifest}
        for d in stazeno.dokumenty:
            if not d.je_pdf:
                chyby.append(f"{d.dokument_id}: odpověď není PDF (chybová stránka?): {d.url}")
                continue
            z = mame.get(d.dokument_id)
            if d.strany is None:
                continue                                   # otisk se nezměnil
            if not d.strany or sum(len(s.strip()) for s in d.strany) < MIN_ZNAKU:
                chyby.append(f"{d.dokument_id}: PDF nemá textovou vrstvu nebo je prázdné")
            elif z and z.get("pocet_stran") and len(d.strany) < z["pocet_stran"] * POKLES:
                chyby.append(f"{d.dokument_id}: nová verze má {len(d.strany)} stran proti dosavadním {z['pocet_stran']}")
        return chyby
