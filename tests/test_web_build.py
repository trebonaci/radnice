"""Statický web radnice.trebonaci.cz (#191): web/build.py."""
from web import build


def test_sestaveni_bez_zbylych_znacek():
    html = build.sestav()
    assert "__STITEK__" not in html and "__DATA__" not in html
    assert "neschváleno" not in html
    assert "Nejde o web Města Třeboň" in html


def test_nahled_je_oznaceny():
    assert "neschváleno ke zveřejnění" in build.sestav(nahled=True)


def test_datum_z_behu():
    assert build._datum({"zacatek": "2026-11-21T13:41:17+00:00"}) == "21. 11. 2026"
    assert build._datum({}) == ""


def test_usneseni_pro_web_odkaz_na_stranu_a_razeni():
    from web.build import usneseni_pro_web
    jd = [{"id": "rm-1", "organ": "rada", "cislo": "1", "datum": "2026-11-04", "dokument": {"url": "https://z.pdf"}},
          {"id": "zm-1", "organ": "zastupitelstvo", "cislo": "1", "datum": "2026-11-02", "dokument": {"url": "https://y.pdf"}}]
    us = [{"id": "zm-1-u1", "cislo": "ZM 1/2026-1", "jednani_id": "zm-1", "vysledek_hlasovani": "prijato",
           "shrnuti": "S", "shrnuti_ai": True, "kategorie": ["samosprava"], "citace": {"strany": [4]}},
          {"id": "rm-1-u1", "cislo": "RM 1/2026-1", "jednani_id": "rm-1", "vysledek_hlasovani": "neprijato",
           "pro_obcany": {"text": "P"}, "pro_obcany_ai": True, "kategorie": [], "citace": {"strany": []}}]
    r = usneseni_pro_web(us, jd)
    assert [x["id"] for x in r] == ["rm-1-u1", "zm-1-u1"]
    assert r[1]["url"] == "https://y.pdf#page=4" and r[0]["url"] == "https://z.pdf"
    assert r[0]["shrnuti"] == "P" and r[0]["kategorie"] == ["ostatni"] and r[0]["vysledek"] == "neprijato"


def test_co_se_deje_ma_sest_okruhu_a_sest_polozek_menu():
    import re
    html = build.sestav()
    okruhy = re.search(r"const OK=(\[.*?\]);\n", html)
    assert okruhy and okruhy.group(1).count('"popis"') == 6
    menu = re.search(r'<nav id="menu"[^>]*>(.*?)</nav>', html).group(1)
    assert re.findall(r'href="([^"]*)"', menu) == ["#", "#investice", "#projekty", "#usneseni", "#mista", "#mapa"]
    assert re.findall(r">([^<]+)</a>", menu) == ["Co se děje", "Investice a opravy", "Projekty", "Usnesení", "Místa a služby", "Mapa"]
    # Rozpočet, V číslech, Připravované a Dokončené zůstávají v patičce
    pata = re.search(r"<footer.*?</footer>", html, re.S).group(0)
    for h in ("#pripravovane", "#dokoncene", "#rozpocet", "#cisla"):
        assert f'href="{h}"' in pata
    assert "Tailwind" not in html and "fonts.googleapis" not in html and "cdn." not in html


def test_stare_adresy_se_presmeruji():
    html = build.sestav()
    assert 'stavby:"investice","casova-osa":"projekty"' in html
    assert "const [h0,...hz]=h.split" in html   # okruh za lomítkem zůstává (#stavby/skoly → #investice/skoly)
    assert "#stavby" not in html and "#casova-osa" not in html


def test_pisma_jsou_ve_webu_a_se_kopiruji(tmp_path, monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["build", "--vystup", str(tmp_path)])
    build.main()
    for f in ("inter-latin.woff2", "inter-latin-ext.woff2", "OFL-Inter.txt"):
        assert (tmp_path / "fonts" / f).stat().st_size > 1000
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "url(fonts/inter-latin.woff2)" in html


def test_datova_json_a_cors_pro_modul_radnice(tmp_path, monkeypatch):
    """Modul /radnice/ na trebonaci.cz (#177): build vystaví prehled/ukazatele/beh.json
    do _site/data/ a _headers je zpřístupní cizí doméně (CORS), aby se denně aktualizovaly
    automaticky bez ručního uploadu do WordPressu."""
    import json
    import sys
    monkeypatch.setattr(sys, "argv", ["build", "--vystup", str(tmp_path)])
    build.main()
    for nazev in ("prehled", "ukazatele", "beh"):
        cesta = tmp_path / "data" / f"{nazev}.json"
        assert cesta.exists(), nazev
        json.loads(cesta.read_text(encoding="utf-8"))  # platné JSON
    hlavicky = (tmp_path / "_headers").read_text(encoding="utf-8")
    assert "/data/*" in hlavicky and "Access-Control-Allow-Origin: *" in hlavicky


def test_usneseni_pro_web_nese_okruhy():
    from web.build import usneseni_pro_web
    r = usneseni_pro_web([{"id": "u", "jednani_id": "x", "okruh": "skoly", "okruhy": ["skoly", "rozvoj_sprava"]}], [])
    assert r[0]["okruh"] == "skoly" and r[0]["okruhy"] == ["skoly", "rozvoj_sprava"]


def test_mapa_po_okruzich():
    html = build.sestav()
    assert 'okruhChips("mapa")' in html and "data-gtema" not in html
    assert '["investice","projekty","usneseni","mista","mapa"].includes(str)' in html   # okruh v adrese i pro mapu a časovou osu


def test_stranky_okruhu_maji_vsechny_pomocne_funkce():
    """Usnesení a Místa používají radekOkruhu a PROCEDURALNI; bez nich se stránka nevykreslí."""
    html = build.sestav()
    for jmeno in ("function radekOkruhu(", "const PROCEDURALNI=", "function blokStranky("):
        assert jmeno in html, jmeno
def test_kpi_investic_jen_z_dat():
    def p(faze, castka, neuplne=()):
        return {"faze": faze, "souhrn": {"celkova_cena_s_dph": {"castka": castka, "neuplne": list(neuplne)}}}
    projekty = [p("probiha", 1000000.5), p("probiha", 2000000.25, ["dodatek"]), p("probiha", None),
                p("dokonceno", 9999999.0), p("soutezi_se", 5.0), p("pripravuje_se", None)]
    k = build.kpi_investic(projekty, {"rok": 2026, "bez_rezervy_po_zmenach": 268436840.0})
    assert k["pocty"] == {"probiha": 3, "soutezi_se": 1, "pripravuje_se": 1, "dokonceno": 1, "celkem": 6}
    # sečtou se jen probíhající akce, dokončené a chystané ne
    assert k["cena_probihajicich"] == {"castka": 3000000.75, "akci": 3, "akci_s_cenou": 2, "neuplnych": 1,
                                       "druh": "smluvni", "s_dph": True}
    assert k["rozpocet"]["castka"] == 268436840.0 and k["rozpocet"]["rok"] == 2026
    assert build.kpi_investic([], None)["rozpocet"]["castka"] is None


def test_kpi_v_datech_odpovida_projektum():
    import json
    projekty = json.loads((build.KOREN / "data" / "projekty.json").read_text(encoding="utf-8"))
    k = build.kpi_investic(projekty, None)
    assert k["pocty"]["celkem"] == len(projekty) == sum(k["pocty"][f] for f in ("probiha", "soutezi_se", "pripravuje_se", "dokonceno"))


def test_investice_nema_nedolozene_ukazatele():
    html = build.sestav()
    for zakazane in ("termínová spolehlivost", "Termínová spolehlivost", "z toho dotace", "zpoždění"):
        assert zakazane not in html
    assert "Jak evidujeme investice" in html


def test_lhuta_ze_smlouvy_se_na_karte_investice_escapuje():
    """Review #255 (P1): citace lhůty ze smlouvy je text z dokumentu, do HTML se vkládá přes esc()."""
    import re
    html = build.sestav()
    radek = re.search(r'<dl class="ak-d">.*?</dl>', html, re.S).group(0)
    assert "${esc(t.h||t.pozn)}" in radek and "${esc(t.pozn)}" in radek


def test_barvy_okruhu_jsou_v_css_i_v_js_pro_kazdy_okruh():
    """Každý okruh má svou barvu v CSS (.o-<id>) i v JS (pruh rozložení) a obě sady se shodují."""
    import re

    import yaml

    html = build.SABLONA.read_text(encoding="utf-8")
    okruhy = yaml.safe_load((build.KOREN / "config" / "okruhy.yaml").read_text(encoding="utf-8"))["okruhy"]
    js = re.search(r"const BARVY_OKRUHU=\{(.*?)\};", html).group(1)
    barvy_js = dict(re.findall(r"(\w+):\"(#[0-9a-f]{6})\"", js))
    for o in okruhy:
        css = re.search(r"\.o-%s\{--ok:(#[0-9a-f]{6});--ok-tint:(#[0-9a-f]{6});--ok-ink:(#[0-9a-f]{6});--ok-tma:(#[0-9a-f]{6})\}" % o["id"], html)
        assert css, f"okruh {o['id']} nemá v CSS třídu .o-{o['id']}"
        assert barvy_js.get(o["id"]) == css.group(1), f"okruh {o['id']} má v JS jinou barvu než v CSS"
    assert len(barvy_js) == len(okruhy)
    assert len({c for c in barvy_js.values()}) == len(okruhy), "dva okruhy mají stejnou barvu"


def test_pripominky_24_11_filtr_menu_a_rozbalovani_stavu():
    """Připomínky 24. 11.: filtr nemění svislý posun, menu je lepkavé, stavy se rozbalují samostatně."""
    html = build.sestav()
    # filtr: render si pamatuje posun a při stejné stránce ho vrací (žádný skok na začátek)
    assert "yPosun=window.scrollY" in html and "function posun2(pred,nyni)" in html
    # nahoru se jde jen při přechodu na jinou stránku (posun2) a na kartu akce
    assert html.count("window.scrollTo(0,0)") == 2
    # menu je samostatný prvek za hlavičkou, aby lepkavost platila pro celou stránku
    assert '</header>\n<nav id="menu"' in html
    assert "nav#menu.skryte{transform:translateY(-100%)}" in html
    # stavy na Investicích se rozbalují každý zvlášť
    assert '<details class="stav"' in html and 'Zobrazit další (${pocet-2})' in html
    assert '["Projektuje se",seznam,prip],["Hotovo",mrizka,hot],["Náměty ze Strategického plánu",namety,nam]' in html


def test_vyberove_rizeni_je_soutez_na_dodavatele_stavby():
    """Krok „Výběrové řízení“ v pruhu fází bere soutěž na dodavatele stavby (role==="stavba"),
    ne první soutěž bez ohledu na roli – ta u akcí s výběrkem na PD ukazovala datum výběrka na projekt.
    Regrese k #270."""
    import re
    html = build.sestav()
    telo = re.search(r"function pruhFazi\(p\)\{(.*?)\n\}", html, re.S)
    assert telo, "funkce pruhFazi ve webu chybí"
    telo = telo.group(1)
    # „Výběrové řízení“ se počítá z proměnné soutez
    assert '["Výběrové řízení",soutez?.datum' in telo
    # a ta filtruje soutěže na roli stavba a vynechává zrušené
    assert 'const soutez=' in telo
    sout = re.search(r"const soutez=(.*?);", telo).group(1)
    assert 'e.typ==="soutez"' in sout and 'e.role==="stavba"' in sout and '!e.zruseno' in sout
    # původní chyba: první soutěž bez ohledu na roli
    assert 'prvni("soutez")' not in telo


def test_harmonogram_filtr_stavu_a_oddeleni_v_kategoriich():
    """Harmonogram (návrh 25. 11.): filtr podle stavu (vše/běžící/plánované/dokončené) a oddělení stavů
    uvnitř kategorie; jen z dat harmonogramu, nic vymyšleného."""
    html = build.sestav()
    # stavový filtr a jeho logika
    assert "function harmFiltr" in html
    assert "class=\"harm-tabs\"" in html
    for s in ("Běžící", "Plánované", "Dokončené"):
        assert f">{s} " in html  # tlačítko s počtem
    # stav řádku a oddělené podskupiny v kategorii
    assert "const stavRadku=" in html and 'data-stav="${stavRadku(r)}"' in html
    assert 'class="sub" data-stav=' in html and 'class="sub-h"' in html
    assert 'class="harm" data-f="vse"' in html
    # pořád bez CDN
    assert "cdn." not in html and "fonts.googleapis" not in html and "Tailwind" not in html


def test_detail_investice_v2_jen_dolozena_data():
    """Nový layout karty investice (návrh 24. 11.): bohatší vzhled, ale jen doložená data –
    skluz termínu a zaplaceno dle E-ZAK (jen když souhlasí s cenou), rozpad nákladů ze skladby,
    zástupná ilustrace (ne vizualizace stavby). Žádné odhadované procento postupu."""
    html = build.sestav()
    # doložitelné metriky místo odhadovaného „% postupu"
    assert "function postupVeta(p)" in html
    assert "souhlas_zaplaceno" in html  # zaplaceno se ukáže jen když souhlasí se smluvní cenou
    assert "Skutečný postup prací v datech není" in html  # fyzický postup se netvrdí
    # rozpad nákladů jde ze souhrnu, ne z ručních čísel
    assert "function rozpadNakladu(p)" in html and "skladba_s_dph" in html
    # zástupná ilustrace dle okruhu, s možností nahradit reálným foto (p.foto)
    assert "Zástupná ilustrace" in html and "p.foto" in html
    # feed s filtrem
    assert "function histFiltr" in html and 'data-kind=' in html
    # pořád bez CDN
    assert "cdn." not in html and "fonts.googleapis" not in html and "Tailwind" not in html
