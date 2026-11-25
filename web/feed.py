"""Atom feed „Co se děje“ pro radnice.trebonaci.cz (#283, odběr novinek).

Statická náhrada e-mailového odběru: čtečka RSS/Atom nebo služba typu „newsletter z RSS“
si feed stáhne sama, bez serveru a databáze. Nic se tu nepočítá – jen se opisují titulek,
datum a shrnutí z už sestavených zpráv (`data/zpravy.json` přes `web.zpravy`), takže feed
nese stejné údaje jako stránka „Co se děje“ a drží se pravidla, že čísla počítá pipeline.
"""
from __future__ import annotations

from xml.sax.saxutils import escape, quoteattr

BASE = "https://radnice.trebonaci.cz"
NAZEV = "Otevřená radnice – co se děje v Třeboni"
POPIS = ("Investice, rozhodnutí rady a zastupitelstva a změny ve službách města Třeboně "
         "z veřejných zdrojů. Nejde o web Města Třeboň.")
POCET = 40  # kolik nejnovějších zpráv se dá do feedu


def _cas(datum: str) -> str:
    """Datum zprávy (YYYY-MM-DD) na časové razítko Atomu; poledne UTC, aby nezáleželo na letním čase."""
    return f"{datum}T12:00:00Z"


def _odkaz(z: dict) -> str:
    """Kam zpráva vede: na kartu akce na webu radnice, jinak na první zdroj, jinak na úvod."""
    if z.get("projekt_id"):
        return f"{BASE}/#{z['projekt_id']}"
    zdroje = z.get("zdroje") or []
    return (zdroje[0].get("url") if zdroje and zdroje[0].get("url") else BASE)


def atom(zpravy_web: dict, okruhy: list[dict], datum_behu: str | None = None) -> str:
    """Atom 1.0 feed z výstupu `web.zpravy.zpravy_pro_web` (klíč `zpravy`). `okruhy` jen pro názvy kategorií."""
    nazvy = {o["id"]: o.get("nazev") for o in (okruhy or [])}
    zpravy = (zpravy_web or {}).get("zpravy", [])[:POCET]
    aktualizace = _cas(zpravy[0]["datum"]) if zpravy else _cas(datum_behu or "1970-01-01")
    radky = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        f"  <title>{escape(NAZEV)}</title>",
        f"  <subtitle>{escape(POPIS)}</subtitle>",
        f'  <link href="{BASE}/" rel="alternate" type="text/html"/>',
        f'  <link href="{BASE}/feed.xml" rel="self" type="application/atom+xml"/>',
        f"  <id>{BASE}/</id>",
        f"  <updated>{aktualizace}</updated>",
        "  <author><name>Otevřená radnice – Třeboňáci</name></author>",
    ]
    for z in zpravy:
        radky.append("  <entry>")
        radky.append(f"    <title>{escape(z.get('titulek') or '')}</title>")
        radky.append(f'    <link href={quoteattr(_odkaz(z))} rel="alternate" type="text/html"/>')
        radky.append(f"    <id>urn:radnice:zprava:{escape(str(z.get('id') or ''))}</id>")
        radky.append(f"    <updated>{_cas(z['datum'])}</updated>")
        radky.append(f"    <published>{_cas(z['datum'])}</published>")
        okruh = z.get("okruh")
        if okruh:
            radky.append(f'    <category term={quoteattr(okruh)} label={quoteattr(nazvy.get(okruh) or okruh)}/>')
        shrnuti = z.get("shrnuti")
        if shrnuti:
            if z.get("shrnuti_ai"):
                shrnuti = f"[AI] {shrnuti} (Větu psala AI; závazné je znění ve zdroji.)"
            radky.append(f'    <summary type="text">{escape(shrnuti)}</summary>')
        radky.append("  </entry>")
    radky.append("</feed>")
    return "\n".join(radky) + "\n"
