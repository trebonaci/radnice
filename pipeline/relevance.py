"""Relevance usnesení k investicím a rozpočtu investic (#278, širší definice, rozhodnutí Ondřeje 25. 11. 2026).

Pro historická jednání (staré volební období, před ustavujícím ZM 2. 11. 2026) bereme jen usnesení relevantní
k investicím – kód (ne AI) je pozná z textu usnesení. Aktuální rada a zastupitelstvo se nefiltrují (sekce
Usnesení zůstává kompletní). „Širší“ zahrnuje i majetek a dotace směřující do investic.

Relevantní je usnesení, které se týká některé z těchto skupin:
- veřejná zakázka / zadávací řízení / výběr dodavatele,
- smlouva o dílo nebo její dodatek, technický dozor, BOZP, projektová dokumentace,
- stavba / rekonstrukce / přístavba / investiční akce,
- rozpočtové opatření ke kapitálovým (investičním) výdajům,
- nabytí/převod majetku (pozemky, nemovitosti, věcná břemena) – širší vazba na investice,
- dotace na investiční akci / stavbu.

Klasifikace je záměrně spíš širší (radši vzít hraniční než minout investici); doladí se na reálných
historických zápisech. `duvod` vrací, která skupina usnesení zařadila (pro kontrolu a testy).
"""
from __future__ import annotations

import re

SKUPINY = [
    ("zakázka", r"ve[řr]ejn\w*\s+zak[aá]zk\w*|zad[aá]vac\w*\s+[řr][ií]zen\w*|v[ýy]b[ěe]rov\w*\s+[řr][ií]zen\w*"
                r"|nejv[ýy]hodn[ěe]j[šs][ií]\s+nab[ií]dk\w*|v[ýy]b[ěe]r\w*\s+(?:dodavatele|zhotovitele)"),
    ("smlouva o dílo", r"smlouv\w*\s+o\s+d[ií]lo|dodatk\w*[^.]{0,40}smlouv\w*\s+o\s+d[ií]lo|technick\w*\s+dozor"
                       r"|koordin[aá]tor\w*\s+BOZP|projektov\w*\s+dokumentac\w*|zhotoven[ií]\s+(?:stavby|d[ií]la)"),
    ("stavba", r"stavebn[ií]\s+pr[aá]c\w*|rekonstrukc\w*|revitalizac\w*|p[řr][ií]stavb\w*|n[aá]stavb\w*"
               r"|v[ýy]stavb\w*|investi[čc]n\w*\s+akc\w*|zateplen\w*|\bZTV\b|technick\w*\s+vybavenost"
               r"|in[žz]en[ýy]rsk\w*\s+s[ií]t\w*|ve[řr]ejn\w*\s+osv[ěe]tlen\w*|kanalizac\w*|vodovod\w*"
               r"|chodn[ií]k\w*|\bmost\w*|oprav\w*\s+(?:komunikac|vozovk|chodn[ií]k|m[ůu]stk|mostu|povrch|ploch)"),
    ("rozpočet investic", r"(?=.*rozpo[čc]tov\w*\s+opat[řr]en)(?=.*(?:kapit[aá]lov\w*|investi[čc]n\w*|\bORG\b|investi[čc]n\w*\s+akc\w*))"),
    ("majetek", r"(?:koup[ěe]|n[aá]byt[ií]|prodej\w*|sm[ěe]n\w*|pron[aá]jem\w*|v[ýy]p[ůu]j[čc]k\w*)[^.]{0,40}"
                r"(?:pozemk\w*|nemovit\w*|parcel\w*|objekt\w*|budov\w*)|v[ěe]cn\w*\s+b[řr]emen\w*"),
    ("dotace na investici", r"dotac\w*[^.]{0,60}(?:investi[čc]n\w*|na\s+stavb\w*|na\s+akc\w*|na\s+rekonstrukc\w*|kapit[aá]lov\w*)"),
]
RE_SKUPINY = [(n, re.compile(p, re.I)) for n, p in SKUPINY]


def investicni(text: str) -> tuple[bool, str | None]:
    """(je relevantní k investicím, která skupina zařadila | None). Širší definice – viz modul."""
    t = " ".join((text or "").split())
    for nazev, rx in RE_SKUPINY:
        if rx.search(t):
            return True, nazev
    return False, None
