import html
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, unquote, urlparse
import requests
from bs4 import BeautifulSoup

URL = "https://sites.google.com/view/muhammath/5-sinif/%C3%B6dev/%C3%B6dev-5b"
SINIF_ADI = "5B Sınıfı Ödevleri"
CIKTI_DOSYASI = "docs/5b.html"
RENK = "#2563eb"

BLOCK_TAGS = {"div", "p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article"}
GEREKSIZ_METINLER = {
    "search this site", "embedded files", "skip to main content", "skip to navigation",
    "report abuse", "google sites", "page details", "page updated",
    "bu sitede ara", "ana içeriğe geç", "ana içeriğe atla", "gezinmeye geç", "gezinmeye atla",
    "kötüye kullanımı bildir", "sayfa ayrıntıları", "sayfa güncellendi", "<<", ">>",
}


def google_linkini_temizle(href: str) -> str:
    if not href:
        return ""
    try:
        parsed = urlparse(href)
        if "google.com" in parsed.netloc and parsed.path == "/url":
            qs = parse_qs(parsed.query)
            if "q" in qs and qs["q"]:
                return unquote(qs["q"][0])
    except Exception:
        pass
    return href


def icerik_cek(url: str) -> list:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    yanit = requests.get(url, headers=headers, timeout=20)
    yanit.raise_for_status()
    yanit.encoding = "utf-8"

    soup = BeautifulSoup(yanit.text, "html.parser")
    ana_alan = soup.find("div", attrs={"role": "main"}) or soup.find("main") or soup.body

    for etiket in ana_alan.find_all(["script", "style", "noscript", "nav", "header", "footer", "svg"]):
        etiket.decompose()

    bloklar = []
    gorulenler = set()

    for el in ana_alan.find_all(["h1", "h2", "h3", "h4", "p", "li", "div"]):
        if el.find(BLOCK_TAGS):
            continue

        for br in el.find_all("br"):
            br.replace_with("\n")

        linkler = []
        for a in el.find_all("a", href=True):
            href = google_linkini_temizle(a["href"].strip())
            link_metni = " ".join(a.get_text(" ", strip=True).split()) or href
            if href.startswith(("http://", "https://")) and link_metni.lower() not in GEREKSIZ_METINLER:
                linkler.append((link_metni, href))

        satirlar = [" ".join(s.split()) for s in el.get_text("\n").splitlines()]
        satirlar = [s for s in satirlar if s]
        tip = "baslik" if el.name in ("h1", "h2", "h3", "h4") else "madde"

        for idx, satir in enumerate(satirlar):
            if satir.lower() in GEREKSIZ_METINLER or satir in gorulenler:
                continue
            gorulenler.add(satir)
            bloklar.append((tip, satir, linkler if idx == len(satirlar) - 1 else []))

    return bloklar


def html_olustur(bloklar: list) -> str:
    tr_saati = datetime.now(timezone(timedelta(hours=3)))
    guncelleme = tr_saati.strftime("%d.%m.%Y %H:%M")

    if not bloklar:
        icerik_html = '<p class="bos">Şu an görüntülenebilecek bir ödev bulunamadı.</p>'
    else:
        parcalar = []
        for tip, metin, linkler in bloklar:
            guvenli = html.escape(metin)
            if tip == "baslik":
                parcalar.append(f"<h2>{guvenli}</h2>")
            else:
                link_html = ""
                if linkler:
                    ogeler = " ".join(
                        f'<a href="{html.escape(h)}" target="_blank" rel="noopener noreferrer">{html.escape(y)}</a>'
                        for y, h in linkler
                    )
                    link_html = f'<div class="linkler">{ogeler}</div>'
                parcalar.append(f'<div class="kart"><p>{guvenli}</p>{link_html}</div>')
        icerik_html = "\n".join(parcalar)

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{SINIF_ADI}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; color: #1e293b; margin: 0; padding: 16px; line-height: 1.6; }}
    .kapsayici {{ max-width: 800px; margin: 0 auto; }}
    .ust {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; border-bottom: 2px solid {RENK}; padding-bottom: 10px; margin-bottom: 16px; }}
    .ust h1 {{ margin: 0; font-size: 1.35rem; color: {RENK}; }}
    .tarih {{ font-size: 0.85rem; color: #64748b; }}
    h2 {{ font-size: 1.1rem; color: #0f172a; margin: 16px 0 8px; }}
    .kart {{ background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid {RENK}; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; }}
    .kart p {{ margin: 0; }}
    .linkler {{ margin-top: 8px; display: flex; flex-wrap: wrap; gap: 8px; }}
    .linkler a {{ font-size: 0.85rem; color: {RENK}; text-decoration: none; background: #f1f5f9; padding: 4px 10px; border-radius: 6px; }}
    .linkler a:hover {{ text-decoration: underline; }}
    .bos {{ color: #64748b; font-style: italic; }}
  </style>
</head>
<body>
  <div class="kapsayici">
    <div class="ust">
      <h1>{SINIF_ADI}</h1>
      <span class="tarih">Son güncelleme: {guncelleme}</span>
    </div>
    {icerik_html}
  </div>
</body>
</html>
"""


def main():
    os.makedirs("docs", exist_ok=True)
    bloklar = icerik_cek(URL)
    with open(CIKTI_DOSYASI, "w", encoding="utf-8") as f:
        f.write(html_olustur(bloklar))
    print(f"{CIKTI_DOSYASI} güncellendi ({len(bloklar)} öğe).")


if __name__ == "__main__":
    main()
