import html
import os
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup

URL = "https://sites.google.com/view/muhammath/5-sinif/%C3%B6dev/%C3%B6dev-5a"
SINIF_ADI = "5A Sınıfı Ödevleri"
CIKTI_DOSYASI = "docs/5a.html"

GEREKSIZ_METINLER = {
    "search this site",
    "embedded files",
    "skip to main content",
    "skip to navigation",
    "report abuse",
    "google sites",
    "page details",
    "page updated",
    "bu sitede ara",
    "ana içeriğe geç",
    "gezinmeye geç",
    "kötüye kullanımı bildir",
    "sayfa ayrıntıları",
    "sayfa güncellendi",
}


def icerik_cek(url: str) -> list[tuple[str, str]]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
    }
    yanit = requests.get(url, headers=headers, timeout=20)
    yanit.raise_for_status()
    yanit.encoding = "utf-8"

    soup = BeautifulSoup(yanit.text, "html.parser")
    ana_alan = soup.find("div", attrs={"role": "main"}) or soup.body

    for etiket in ana_alan.find_all(["script", "style", "nav", "header", "footer", "svg"]):
        etiket.decompose()

    bloklar = []
    gorulenler = set()

    for el in ana_alan.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        # li içindeki p etiketlerini iki kez almamak için atla
        if el.name == "p" and el.find_parent("li"):
            continue

        metin = " ".join(el.get_text(" ", strip=True).split())
        if not metin or metin.lower() in GEREKSIZ_METINLER:
            continue
        if metin in gorulenler:
            continue
        gorulenler.add(metin)

        # Varsa ödev içindeki linkleri koru
        linkler = []
        for a in el.find_all("a", href=True):
            href = a["href"].strip()
            link_metni = a.get_text(" ", strip=True) or href
            if href.startswith("http"):
                linkler.append((link_metni, href))

        etiket_tipi = "baslik" if el.name in ("h1", "h2", "h3", "h4") else "madde"
        bloklar.append((etiket_tipi, metin, linkler))

    return bloklar


def html_olustur(bloklar: list) -> str:
    tr_saati = datetime.now(timezone(timedelta(hours=3)))
    guncelleme = tr_saati.strftime("%d.%m.%Y %H:%M")

    if not bloklar:
        icerik_html = '<p class="bos">Şu an görüntülenebilecek bir ödev bulunamadı.</p>'
    else:
        parcalar = []
        for tip, metin, linkler in bloklar:
            guvenli_metin = html.escape(metin)
            if tip == "baslik":
                parcalar.append(f"<h2>{guvenli_metin}</h2>")
            else:
                link_html = ""
                if linkler:
                    link_ogeleri = " ".join(
                        f'<a href="{html.escape(href)}" target="_blank" rel="noopener">{html.escape(yazi)}</a>'
                        for yazi, href in linkler
                    )
                    link_html = f'<div class="linkler">{link_ogeleri}</div>'
                parcalar.append(f'<div class="kart"><p>{guvenli_metin}</p>{link_html}</div>')
        icerik_html = "\n".join(parcalar)

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{SINIF_ADI}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f8fafc;
      color: #1e293b;
      margin: 0;
      padding: 16px;
      line-height: 1.6;
    }}
    .kapsayici {{
      max-width: 800px;
      margin: 0 auto;
    }}
    .ust {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      border-bottom: 2px solid #2563eb;
      padding-bottom: 10px;
      margin-bottom: 16px;
    }}
    .ust h1 {{
      margin: 0;
      font-size: 1.35rem;
      color: #1d4ed8;
    }}
    .tarih {{
      font-size: 0.85rem;
      color: #64748b;
    }}
    h2 {{
      font-size: 1.1rem;
      color: #0f172a;
      margin: 18px 0 8px;
    }}
    .kart {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-left: 4px solid #2563eb;
      border-radius: 8px;
      padding: 12px 14px;
      margin-bottom: 10px;
    }}
    .kart p {{
      margin: 0;
    }}
    .linkler {{
      margin-top: 8px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .linkler a {{
      font-size: 0.85rem;
      color: #2563eb;
      text-decoration: none;
      background: #eff6ff;
      padding: 4px 10px;
      border-radius: 6px;
    }}
    .linkler a:hover {{
      text-decoration: underline;
    }}
    .bos {{
      color: #64748b;
      font-style: italic;
    }}
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
    sayfa = html_olustur(bloklar)
    with open(CIKTI_DOSYASI, "w", encoding="utf-8") as f:
        f.write(sayfa)
    print(f"{CIKTI_DOSYASI} güncellendi ({len(bloklar)} öğe).")


if __name__ == "__main__":
    main()
