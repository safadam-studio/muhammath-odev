import os
import html
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs, unquote
import requests
from bs4 import BeautifulSoup

# ==============================================================================
# AYARLAR (5B SINIFI)
# ==============================================================================
SINIF_ADI = "5B"
KAYNAK_URL = "https://sites.google.com/view/muhammath/5-sinif/%C3%B6dev/%C3%B6dev-5b"
CIKTI_KLASORU = "docs"
CIKTI_DOSYASI = os.path.join(CIKTI_KLASORU, "5b.html")

# Google Sites'ın alt bilgisinde veya menüsünde çıkan gereksiz metinler
FILTRELENECEK_METINLER = {
    "google sites",
    "report abuse",
    "kötüye kullanımı bildir",
    "page details",
    "sayfa ayrıntıları",
    "page updated",
    "sayfa güncellendi",
    "skip to main content",
    "ana içeriğe atla",
    "ana içeriğe geç",
    "skip to navigation",
    "gezinmeye atla",
    "gezinmeye geç",
    "search this site",
    "bu sitede ara",
    "embedded files",
}


def turkiye_saati_al() -> str:
    """GitHub Actions sunucuları UTC saatinde çalışır. Türkiye saatini (UTC+3) döndürür."""
    tr_tz = timezone(timedelta(hours=3))
    simdi = datetime.now(tr_tz)
    return simdi.strftime("%d.%m.%Y %H:%M")


def google_linkini_temizle(href: str) -> str:
    """Google Sites'ın yönlendirme (google.com/url?q=...) linklerini gerçek linke çevirir."""
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


def sayfa_icerigini_cek(url: str) -> list[dict]:
    """
    Google Sites sayfasına istek atar ve ana içerik alanındaki
    başlık, paragraf, liste ve bağlantıları temiz bir liste olarak döndürür.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")

    # Google Sites ana içeriği genellikle role="main" içinde yer alır
    ana_alan = soup.find(attrs={"role": "main"}) or soup.find("main") or soup.body
    if not ana_alan:
        raise ValueError("Sayfada ana içerik alanı bulunamadı.")

    # Gereksiz etiketleri temizle
    for gereksiz in ana_alan.find_all(
        ["script", "style", "noscript", "svg", "nav", "header", "footer", "button", "input"]
    ):
        gereksiz.decompose()

    bloklar = []
    gorulen_metinler = set()

    # Başlıkları, paragrafları ve liste öğelerini sırayla topla
    for etiket in ana_alan.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        # Eğer bir <p> etiketi bir <li> içindeyse çift yazmamak için atla
        if etiket.name == "p" and etiket.find_parent("li") is not None:
            continue

        metin = " ".join(etiket.get_text(" ", strip=True).split())
        if not metin:
            continue

        if metin.lower() in FILTRELENECEK_METINLER:
            continue

        # Aynı metnin tekrar eklenmesini engelle
        if metin in gorulen_metinler:
            continue
        gorulen_metinler.add(metin)

        # Etiket içinde bağlantı (link) varsa onları da al
        linkler = []
        for a in etiket.find_all("a", href=True):
            temiz_href = google_linkini_temizle(a["href"])
            link_metni = " ".join(a.get_text(" ", strip=True).split()) or temiz_href
            if temiz_href.startswith(("http://", "https://")):
                linkler.append({"metin": link_metni, "url": temiz_href})

        bloklar.append({
            "tip": etiket.name,
            "metin": metin,
            "linkler": linkler,
        })

    return bloklar


def html_olustur(bloklar: list[dict], guncelleme_zamani: str) -> str:
    """Çekilen ödev bloklarını Google Sites'a gömülmeye uygun modern bir HTML sayfasına dönüştürür."""
    icerik_parcalari = []

    if not bloklar:
        icerik_parcalari.append(
            '<div class="bos-mesaj">Şu an için yayınlanmış bir ödev bulunmamaktadır.</div>'
        )
    else:
        for blok in bloklar:
            tip = blok["tip"]
            guvenli_metin = html.escape(blok["metin"])

            if tip in ("h1", "h2"):
                icerik_parcalari.append(f'<h2 class="baslik">{guvenli_metin}</h2>')
            elif tip in ("h3", "h4"):
                icerik_parcalari.append(f'<h3 class="alt-baslik">{guvenli_metin}</h3>')
            elif tip == "li":
                icerik_parcalari.append(f'<div class="madde">• {guvenli_metin}</div>')
            else:
                icerik_parcalari.append(f'<p class="paragraf">{guvenli_metin}</p>')

            if blok["linkler"]:
                link_html = "".join(
                    f'<a class="link-btn" href="{html.escape(l["url"])}" '
                    f'target="_blank" rel="noopener noreferrer">🔗 {html.escape(l["metin"])}</a>'
                    for l in blok["linkler"]
                )
                icerik_parcalari.append(f'<div class="link-grubu">{link_html}</div>')

    govde_html = "\n        ".join(icerik_parcalari)

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{SINIF_ADI} Ödevleri | MuhamMath</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --card: #ffffff;
      --text: #1e293b;
      --muted: #64748b;
      --accent: #2563eb;
      --accent-soft: #eff6ff;
      --border: #e2e8f0;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #0f172a;
        --card: #1e293b;
        --text: #f1f5f9;
        --muted: #94a3b8;
        --accent: #60a5fa;
        --accent-soft: #1e3a5f;
        --border: #334155;
      }}
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      padding: 16px;
      line-height: 1.6;
    }}
    .kart {{
      max-width: 820px;
      margin: 0 auto;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    }}
    .ust-bar {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      padding-bottom: 16px;
      margin-bottom: 20px;
      border-bottom: 1px solid var(--border);
    }}
    .rozet {{
      display: inline-block;
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 700;
      font-size: 0.95rem;
      padding: 6px 14px;
      border-radius: 999px;
    }}
    .tarih {{
      font-size: 0.85rem;
      color: var(--muted);
    }}
    .baslik {{
      font-size: 1.35rem;
      font-weight: 700;
      margin: 18px 0 10px;
      color: var(--accent);
    }}
    .alt-baslik {{
      font-size: 1.1rem;
      font-weight: 600;
      margin: 14px 0 8px;
    }}
    .paragraf {{
      margin-bottom: 10px;
      font-size: 1rem;
    }}
    .madde {{
      margin: 6px 0 6px 12px;
      font-size: 1rem;
    }}
    .link-grubu {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 8px 0 14px;
    }}
    .link-btn {{
      display: inline-block;
      text-decoration: none;
      background: var(--accent-soft);
      color: var(--accent);
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 0.9rem;
      font-weight: 500;
      border: 1px solid var(--border);
    }}
    .link-btn:hover {{
      opacity: 0.85;
    }}
    .bos-mesaj {{
      text-align: center;
      padding: 32px 16px;
      color: var(--muted);
      font-size: 1rem;
    }}
  </style>
</head>
<body>
  <div class="kart">
    <div class="ust-bar">
      <span class="rozet">📚 {SINIF_ADI} Sınıfı Ödevleri</span>
      <span class="tarih">Son Güncelleme: {guncelleme_zamani}</span>
    </div>
    <div class="icerik">
        {govde_html}
    </div>
  </div>
</body>
</html>
"""


def main():
    print(f"[{SINIF_ADI}] Ödevler çekiliyor: {KAYNAK_URL}")
    try:
        bloklar = sayfa_icerigini_cek(KAYNAK_URL)
        guncelleme_zamani = turkiye_saati_al()
        sayfa_html = html_olustur(bloklar, guncelleme_zamani)

        os.makedirs(CIKTI_KLASORU, exist_ok=True)
        with open(CIKTI_DOSYASI, "w", encoding="utf-8") as f:
            f.write(sayfa_html)

        print(f"[{SINIF_ADI}] Başarıyla kaydedildi -> {CIKTI_DOSYASI} ({len(bloklar)} içerik bloğu)")
    except requests.exceptions.RequestException as e:
        print(f"[{SINIF_ADI}] Ağ/bağlantı hatası oluştu: {e}")
        raise
    except Exception as e:
        print(f"[{SINIF_ADI}] Beklenmeyen bir hata oluştu: {e}")
        raise


if __name__ == "__main__":
    main()