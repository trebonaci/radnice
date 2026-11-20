# Formát anotace zápisu (`anotace/<jednani_id>.yaml`)

Anotace je návrh AI (model A) k jednomu zápisu. Strukturu, čísla usnesení a hlasování nevytváří: ty
deterministicky čte `pipeline/zapisy.py`. Sestavení (`python -m pipeline.sestav`) každou citaci ověří
doslova (po sjednocení mezer) v textu zápisu; co neprojde, zůstane ve stavu `navrh` nebo sestavení selže.
Obecná pravidla: `METODIKA.md`, `AGENTS.md` (Pravidla obsahu). Vzorem jsou existující soubory v `anotace/`.

## Hlavička

```yaml
jednani:
  organ: rada            # rada / zastupitelstvo
  druh: radne            # radne / mimoradne / ustavujici
  cislo: 2
  datum: "2026-11-18"
  obdobi: "2026-2030"
  pritomno: 7
  clenu: 7
  citace: "…doslova věta o přítomnosti…"
  dokument_id: zapis-rm-2026-11-18
```

## Usnesení (klíč = id z `pipeline/zapisy.py`, např. `rm-2026-j2-u15`)

| Pole | Povinné | Obsah |
|---|---|---|
| `tema` | ano | krátký neutrální název |
| `kategorie` | ano | kódy z `config/kategorie.yaml` |
| `shrnuti` | ano | co orgán rozhodl, jednou až dvěma větami; čísla jen opsaná |
| `citace` | ano | doslovný úsek usnesení |
| `castky[]` | ne | `hodnota`, `jednotka`, `druh` (DATOVY_MODEL, „castka“), `s_dph` (true/false/null), `citace` (částka musí být v citaci) |
| `parcely[]` | ne | `ku`, `cislo`, `cast`, `citace` |
| `stitky[]` | ne | `stitek`, `duvod`, `citace`, `faze` (`config/stitky.yaml`) |
| `anonymizace[]` | ne | řetězce s osobními údaji nevolených osob, které se ve výstupu nahradí |
| `pro_obcany` | ne | věta „Co se mění pro vás“, viz níže |
| `poznamka`, `otazky[]` | ne | omezení zdroje, nejasnosti |

## `pro_obcany` – Co se mění pro vás

Jedna věta pro běžného čtenáře o tom, co rozhodnutí mění pro lidi v Třeboni. Zobrazuje se jako karta
v přehledu „Co se v Třeboni mění“, proto musí obstát i bez kontextu.

```yaml
    pro_obcany:
      kdo: "Klubovna, Chelčického 2/II"   # organizace nebo místo do nadpisu karty
      text: "Klubovna v domě s pečovatelskou službou v Chelčického ulici zůstává do konce roku 2030 seniorům, šachistům, pěveckému sboru a malířům; náklady na provoz hradí město."
      oblast: socialni
      plati_od: "2027-01-01"     # jen když datum výslovně uvádí zdroj, jinak pole vynechat
      citace: "prodloužení doby výprůjčky do 31.12.2030"
```

**Kdy ano:** služby a jejich provoz, prostory pro spolky a setkávání, byty (DPS, sociální), školy a školky,
kultura, sport, sociální péče, doprava, voda a odpady, vyhlášky, ceníky a poplatky, územní plán, dary
městu nebo od města s konkrétním účelem.

**Kdy ne:** procedurální body (program, ověřovatelé, zápisy komisí, „bere na vědomí“ bez dopadu),
personální věci, interní správa, rozpočtová opatření, tabulky dotací (ty čte `pipeline/dotace.py`),
investice (mají vlastní kartu), majetkové převody bez dopadu na veřejné užívání.

**Jak psát:**
- z pohledu občana, ne úřadu: ne „Rada schválila…“ / „Zastupitelstvo…“ (sestavení to odmítne);
- schválení není dokončení: „může přijmout“, „bude mít“, „přijme“, ne „dostala“, „má“;
- nejvýš 220 znaků, bez zkratek a úředních obratů;
- čísla a data jen opsaná ze zdroje, nic nepočítat;
- žádná jména nevolených osob (fyzická osoba = „fyzická osoba“), žádné hodnocení;
- `oblast` z číselníku: `socialni`, `sport`, `kultura`, `skolstvi`, `komunity_spolky`, `doprava`,
  `voda_odpady`, `uzemni_plan`, `bydleni`, `zivotni_prostredi`, `bezpecnost`, `jine`;
- `kdo` = krátký název organizace nebo místa, kterého se věc týká (nejvýš 60 znaků; „ZŠ Sokolská“, „MŠ Sluníčko“,
  „Hotel Sport, sportovní hala“); zobrazí se jako nadpis karty, aby se podobné karty nepletly. Slova musí být
  v textu usnesení (sestavení to ověří, toleruje skloňování); zkratky ZŠ, MŠ, DPS jsou povolené;
- `citace` = doslovný úsek usnesení, který větu dokládá; nesmí obsahovat řetězec z `anonymizace`.
