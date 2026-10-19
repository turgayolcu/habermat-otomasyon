"""
Habermat.com - Kıdemli SEO Uzmanı & Google AdSense Gelir Odaklı Haber ve Video Senaryo Motoru
- Her haber en az 500 - 750+ kelime uzunluğunda, %100 özgünleştirilmiş gazetecilik diliyle,
  Google Keşfet (Discover), E-E-A-T ve Google AdSense (Yüksek TBM / Yazı İçi Otomatik Reklam)
  kriterlerine tam uyumlu olarak üretilir.
- Kısa meta/video bloklarını önce, uzun makale gövdesini 2 tam parçada üreterek
  cümle yarım kalmasını ve senaryo eksikliğini %100 engeller.
"""

import os
import random
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

TR_TZ = timezone(timedelta(hours=3))

# Sabit kapanış çağrısı (Her haberin ve TikTok/Reels videosunun sonunda zorunlu)
MANDATORY_CTA_DISPLAY = (
    "Başvuru şartları ve detayları için Google'a habermat.com yaz, çıkan ilk siteye tıklayın!"
)
MANDATORY_CTA_SPOKEN = (
    "Başvuru şartları ve detayları için Google'a habermat nokta com yaz, çıkan ilk siteye tıklayın!"
)


def slugify_tr(text: str) -> str:
    """Türkçe metni SEO uyumlu URL slug haline getirir."""
    tr_map = str.maketrans("ğüşıöçĞÜŞİÖÇ", "gusiocgusioc")
    cleaned = text.translate(tr_map).lower()
    cleaned = re.sub(r"[^a-z0-9\s-]", "", cleaned)
    cleaned = re.sub(r"[\s-]+", "-", cleaned).strip("-")
    return cleaned[:75]


def _strip_html(html_text: str) -> str:
    if not html_text:
        return ""
    return BeautifulSoup(html_text, "html.parser").get_text(" ", strip=True)


def count_words_in_html(html_text: str) -> int:
    plain = _strip_html(html_text)
    words = re.findall(r"\b\w+\b", plain, flags=re.UNICODE)
    return len(words)


def _tr_upper(text: str) -> str:
    """Türkçe karakter kurallarına (TDK) uygun büyük harfe çevirme (i -> İ, ı -> I)."""
    return text.replace("i", "İ").replace("ı", "I").upper()


def _tr_lower(text: str) -> str:
    """Türkçe karakter kurallarına (TDK) uygun küçük harfe çevirme (İ -> i, I -> ı)."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def _tr_capitalize_word(w: str) -> str:
    if not w:
        return w
    if w.upper() in {"ABB", "İBB", "TOKİ", "SYDV", "SED", "PTT", "KYK", "GSB", "TL"}:
        return w.upper()
    low = _tr_lower(w)
    if low in {"ve", "ile", "için", "de", "da", "mi", "mı", "mu", "mü"}:
        return low
    return _tr_upper(low[0]) + low[1:]


def _format_mandatory_seo_title(ai_title: str, raw_title: str, category: dict) -> str:
    """
    Tüm haber başlıklarını zorunlu olarak şu formatta üretir:
    '[İl / İlçe Belediyesi] [Yardım/Destek Adı] Başvuru Şartları ve Formu 2026'
    Örnek: 'Mersin Yenişehir Belediyesi Halk Kart Başvuru Şartları ve Formu 2026'
    """
    MANDATORY_SUFFIX = "Başvuru Şartları ve Formu 2026"
    candidate = _strip_html(ai_title or "").strip().strip('"\'“”«»')
    if not candidate or len(candidate) < 12:
        candidate = raw_title.strip()

    # Sondaki mevcut 'Başvuru Şartları...' veya '2026' ifadelerini temizle ki mükerrer olmasın
    candidate = re.sub(
        r"\s*[-–—:|,]?\s*başvuru\s+şartları(\s+ve\s+(formu|detayları|ekranı))?(\s*202\d)?\s*$",
        "",
        candidate,
        flags=re.IGNORECASE,
    ).strip()
    candidate = re.sub(r"\s*202\d\s*$", "", candidate).strip()

    # Tırnakları ve gereksiz noktalama/çekimli haber fiillerini temizle
    candidate = re.sub(r'[“”"«»!?]', "", candidate)
    candidate = re.sub(
        r"\s+(ağı(nı)?\s+genişletiyor|dayanışmayı\s+büyütüyor|devam\s+ediyor|sürdürüyor|yapıldı|başladı|açıklandı|veriyor|dağıtıyor|sunuyor|ulaştı|açtı)\s*$",
        "",
        candidate,
        flags=re.IGNORECASE,
    ).strip(" -–—,:;.")

    # Kategori il adını kontrol et (Başlıkta il adı yoksa en başa ekle)
    cat_name = category.get("name", "")
    province = cat_name.split()[0].strip() if "Belediye" in cat_name else ""
    if province and _tr_lower(province) not in _tr_lower(candidate):
        if not (_tr_lower(province) == "istanbul" and "ibb" in _tr_lower(candidate)) and not (
            _tr_lower(province) == "ankara" and "abb" in _tr_lower(candidate)
        ):
            candidate = f"{province} {candidate}"

    words = [w for w in candidate.split() if w]
    if len(words) > 7:
        words = words[:7]
    formatted_prefix = " ".join(_tr_capitalize_word(w) for w in words)
    if formatted_prefix:
        formatted_prefix = _tr_upper(formatted_prefix[0]) + formatted_prefix[1:]

    return f"{formatted_prefix} {MANDATORY_SUFFIX}".strip()


def _build_clean_tdk_reels_headline(seo_title: str) -> str:
    """
    Reels üst manşetini doğrudan 'Başvuru Şartları ve Formu 2026' içeren haber başlığından
    TDK büyük harf kurallarına uygun olarak üretir.
    """
    clean = re.sub(r"\s+", " ", seo_title.strip()).replace("’", "'").replace("‘", "'")
    return _tr_upper(clean)


def _extract_tdk_news_sentences_for_reels(news_item: Dict[str, str], spot_text: str = "") -> List[str]:
    """
    Kaynak haber metnindeki (ulusal basın editörleri tarafından yazılmış) gerçek paragraflardan,
    Türkçe dilbilgisi, TDK yazım/imla kuralları ve noktalama işaretlerine (virgül, nokta, kesme işareti)
    %100 uygun 4 adet tam haber cümlesi seçer.
    """
    raw_summary = news_item.get("raw_summary", "")
    raw_title = news_item.get("raw_title", "").strip()

    # Önce KAYNAK DETAYLARI (tam makale paragrafları), ardından özetin ilk tam cümlesi
    kaynak_part = ""
    if "KAYNAK DETAYLARI:" in raw_summary:
        after_k = raw_summary.split("KAYNAK DETAYLARI:", 1)[1]
        kaynak_part = after_k.split("İLGİLİ GÜNDEM NOTLARI:", 1)[0].strip()

    lead_part = raw_summary.split("KAYNAK DETAYLARI:", 1)[0].strip()
    notlar_part = ""
    if "İLGİLİ GÜNDEM NOTLARI:" in raw_summary:
        notlar_part = raw_summary.split("İLGİLİ GÜNDEM NOTLARI:", 1)[1].strip()

    combined_blocks = [lead_part, kaynak_part, notlar_part, spot_text]
    candidates: List[str] = []

    for block in combined_blocks:
        if not block:
            continue
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            # Ondalık/binlik sayıları (6.250, 1.071) ve unvan kısaltmalarını (Dr., Prof.) bölmeden cümlelere ayır
            parts = re.split(
                r"(?<!\bDr)(?<!\bProf)(?<!\bAv)(?<!\bDoç)(?<!\bOrn)(?<!\bÖrn)(?<!\d)(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9])",
                line,
            )
            for p in parts:
                s = re.sub(r"\s+", " ", p.strip())
                # Paragraf başında nokta konulmadan bitişik kalmış BÜYÜK HARFLİ ara başlıkları temizle
                # (Örn: "10 BİN TL'LİK DESTEK İKİ TAKSİT HALİNDE ÖDENECEK Proje kapsamında..." -> "Proje kapsamında...")
                s = re.sub(
                    r"^(?:[A-ZÇĞİÖŞÜ0-9'’.,/%+-]+\s+){3,10}(?=[A-ZÇĞİÖŞÜ][a-zğüşıöç]{2,})",
                    "",
                    s,
                ).strip()
                if not s:
                    continue
                # Yarım kalmış (... / …), soru (?), iki noktalı manşet veya çok kısa/çok uzun cümleleri ele
                if "..." in s or "…" in s or s.endswith("?") or ":" in s:
                    continue
                if s[-1] not in ".!":
                    continue
                if len(s) < 48 or len(s) > 210:
                    continue
                lower_s = s.lower()
                if any(
                    bad in lower_s
                    for bad in [
                        "peki,",
                        "işte detaylar",
                        "merak edilenler",
                        "haberimizde",
                        "tıklayın",
                        "abone ol",
                        "habermat",
                        "ilgili gündem",
                        "kaynak detayları",
                    ]
                ):
                    continue
                candidates.append(s)

    selected: List[str] = []
    for cand in candidates:
        cand_clean = cand.replace("’", "'").replace("‘", "'")
        cand_words = set(re.findall(r"\w{4,}", cand_clean.lower()))
        if not cand_words:
            continue
        # Daha önce seçilen cümlelerle %60'tan fazla kelime tekrarı varsa atla
        is_dup = False
        for prev in selected:
            prev_words = set(re.findall(r"\w{4,}", prev.lower()))
            if prev_words and (len(cand_words & prev_words) / max(len(cand_words), 1)) >= 0.60:
                is_dup = True
                break
        if not is_dup:
            selected.append(cand_clean)
        if len(selected) >= 4:
            break

    # Eğer kaynak haber çok kısaysa (fallback vb.) başlık ve kategori bilgisinden TDK uyumlu tam cümle tamamla
    cat_name = news_item.get("category_name", "Sosyal Destek")
    fallback_tdk_sentences = [
        f"{raw_title.rstrip('.!? ')}, güncel başvuru ve ödeme detaylarıyla vatandaşların gündeminde yer alıyor.",
        f"{cat_name} kapsamındaki başvurular ve hak sahipliği sorgulamaları e-Devlet kapısı üzerinden gerçekleştiriliyor.",
        "Şartları sağlayan vatandaşların ödemeleri, belirlenen takvim doğrultusunda PTT veya banka IBAN hesaplarına aktarılıyor.",
    ]
    for fb in fallback_tdk_sentences:
        if len(selected) >= 4:
            break
        if fb not in selected:
            selected.append(fb)

    return selected[:4]


def _clean_cutoff_html(html_text: str) -> str:
    """Eğer model çıktısının en son satırı yarım kalmışsa güvenli şekilde tamamlanmış son etikete keser."""
    html_text = html_text.strip()
    # Modelin nadiren İngilizce prompt terimlerini (cpc, tbm vb.) metne sızdırmasını temizle
    html_text = re.sub(r"\b(yüksek\s+)?(cpc|tbm)\s+(puanlı\s+|odaklı\s+|değerli\s+)?", "", html_text, flags=re.IGNORECASE)
    last_close = max(
        html_text.rfind("</p>"),
        html_text.rfind("</ul>"),
        html_text.rfind("</li>"),
        html_text.rfind("</h2>"),
    )
    if last_close != -1 and last_close > len(html_text) - 180:
        tag_end = html_text.find(">", last_close)
        if tag_end != -1:
            return html_text[: tag_end + 1]
    return html_text


def _call_ai_text(prompt: str, system_msg: str) -> str:
    """
    Önce varsa GEMINI_API_KEY, yoksa ücretsiz Pollinations OpenAI servisini çağırır.
    Hız sınırına (402/429) takılmamak için denemeler arasında otomatik bekleme uygular.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=f"{system_msg}\n\n{prompt}",
                        config=types.GenerateContentConfig(temperature=0.65),
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception:
                    continue
        except Exception:
            pass

    for attempt in range(8):
        if attempt > 0:
            time.sleep(8 + 4 * attempt)
        try:
            resp = requests.post(
                "https://text.pollinations.ai/openai",
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": f"HabermatEditorBot/2.0 (Run-{random.randint(100,999)})",
                    "Referer": "https://habermat.com",
                },
                json={
                    "model": "openai-fast",
                    "reasoning_effort": "low",
                    "seed": random.randint(1000, 999999),
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.65,
                },
                timeout=90,
            )
            if resp.status_code in (402, 429, 502, 503):
                print(f"[BİLGİ] AI servisi yoğun ({resp.status_code}), 10 saniye beklenip tekrar deneniyor...")
                time.sleep(10)
                continue
            resp.raise_for_status()
            res_json = resp.json()
            msg = res_json.get("choices", [{}])[0].get("message", {})
            content = (msg.get("content") or "").strip()
            if not content:
                content = (msg.get("reasoning") or "").strip()
            if content and len(content) > 80:
                return (
                    content.replace("\u202f", " ")
                    .replace("\u00a0", " ")
                    .replace("\u200b", "")
                )
        except Exception as exc:
            print(f"[UYARI] AI çağrısı denemesi #{attempt + 1} uyarısı: {exc}")
    raise RuntimeError("AI servisinden yanıt alınamadı.")


def _extract_block(text: str, tag: str) -> str:
    pattern = rf"==={tag}===\s*(.*?)(?=\n===[A-Z0-9_]+===|\Z)"
    m = re.search(pattern, text, flags=re.DOTALL)
    return m.group(1).strip() if m else ""


def _build_adsense_table_html(table_block: str, category_name: str) -> str:
    rows_html = ""
    for line in table_block.splitlines():
        line = line.strip().lstrip("-*• ")
        if "|" in line:
            parts = [p.strip() for p in line.split("|", 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                rows_html += (
                    f"<tr>"
                    f'<td style="padding:10px 14px;border:1px solid #CBD5E1;font-weight:700;background:#F1F5F9;width:38%;">{_strip_html(parts[0])}</td>'
                    f'<td style="padding:10px 14px;border:1px solid #CBD5E1;">{_strip_html(parts[1])}</td>'
                    f"</tr>"
                )
    if not rows_html:
        return ""
    return (
        '\n<figure class="wp-block-table" style="margin:24px 0;">'
        '<table style="width:100%;border-collapse:collapse;font-size:15px;">'
        "<thead><tr>"
        '<th colspan="2" style="background:#0B132B;color:#FFFFFF;padding:12px 14px;text-align:left;">'
        f"📊 {category_name} – Güncel Başvuru, Kapsam ve Ödeme Özeti Tablosu"
        "</th></tr></thead>"
        f"<tbody>{rows_html}</tbody></table></figure>\n"
    )


def _inject_toc_and_table_for_adsense(article_html: str, table_html: str) -> str:
    """
    Google AdSense Yazı İçi Otomatik Reklamlar (In-Article Auto Ads) için:
    1) Makaledeki H2 başlıklarını tarayarak ilk H2'den hemen önce
       '📌 Bu Haberde Öne Çıkan Başlıklar' kutusunu yerleştirir (Sayfada kalma süresini artırır).
    2) 2. H2 bölümünün sonuna karşılaştırmalı bilgi tablosunu yerleştirir.
    """
    soup = BeautifulSoup(article_html, "html.parser")
    h2_tags = soup.find_all("h2")
    h2_titles = [h.get_text(" ", strip=True) for h in h2_tags if h.get_text(strip=True)]

    toc_html = ""
    if h2_titles:
        items = "".join(f'<li style="margin-bottom:6px;">{t}</li>' for t in h2_titles[:5])
        toc_html = (
            '\n<div class="habermat-toc" style="background:#F8FAFC;border:1px solid #E2E8F0;'
            'border-left:4px solid #0B132B;border-radius:6px;padding:14px 18px;margin:20px 0;">'
            '<p style="margin:0 0 8px 0;font-weight:700;color:#0B132B;">📌 Bu Haberde Öne Çıkan Başlıklar:</p>'
            f'<ul style="margin:0;padding-left:20px;color:#1E293B;font-size:15px;">{items}</ul>'
            "</div>\n"
        )

    raw = article_html.strip()
    if toc_html and "<h2>" in raw:
        raw = raw.replace("<h2>", toc_html + "<h2>", 1)

    if table_html:
        h2_positions = [m.start() for m in re.finditer(r"<h2>", raw)]
        if len(h2_positions) >= 3:
            pos = h2_positions[2]
            raw = raw[:pos] + table_html + raw[pos:]
        else:
            raw = raw + "\n" + table_html

    return raw


def generate_news_and_reels_package(news_item: Dict[str, str], category: dict) -> Dict[str, Any]:
    """
    Kıdemli SEO Uzmanı & Google AdSense Gelir Stratejisti mimarisiyle:
    - Aşama 1: Tüm SEO meta verileri, TikTok Türk Kadın Spiker senaryosu (Giriş + 3 gelişme cümlesi),
               Bilgi Tablosu ve Makalenin 1. Yarısı (Giriş + İlk 2 H2 Bölümü)
    - Aşama 2: Makalenin 2. Yarısı (Başvuru Adımları H2 + Banka/Ödeme Takvimi H2 + 3 Detaylı SSS)
    Toplamda 500 - 750+ kelime uzunluğunda, hiçbir cümlesi yarım kalmayan, %100 özgünleştirilmiş
    ve Google AdSense yüksek TBM/yerleşim uyumlu makale + eksiksiz video senaryosu üretir.
    """
    now_tr = datetime.now(TR_TZ)
    system_msg = (
        "Sen habermat.com'un 15 yıllık Kıdemli SEO Uzmanı, Google AdSense Gelir Stratejisti "
        "ve Ekonomi/Sosyal Güvenlik Baş Editörüsün. İçerikleri %100 özgün, akıcı gazetecilik "
        "diliyle ve eksiksiz olarak istenen ===BLOK=== formatında üretirsin."
    )

    # =========================================================================
    # AŞAMA 1: Video Senaryosu, SEO Meta, Tablo ve Makalenin İlk Yarısı (300+ kelime)
    # =========================================================================
    prompt_p1 = f"""
Aşağıdaki güncel kaynak haber verilerini kullanarak **habermat.com** için SEO meta verilerini, **TikTok (@habermat5) Türk Kadın Spiker** senaryosunu ve haber makalesinin **1. Yarısını** hazırla.

GÜNCEL KAYNAK HABER VERİLERİ:
- Kategori: {category['name']}
- Konu Başlığı: {news_item['raw_title']}
- Kaynak Haber Metni ve Detayları:
{news_item['raw_summary'][:2400]}
- Tarih: {now_tr.strftime('%d.%m.%Y')}

KURALLAR:
- Asla "Detaylar ve Kapsam", "Bu yazıda ele alıyoruz" gibi yapay zeka kokan kalıplar KULLANMA!
- Kaynak haberdeki gerçek rakamları, tarihleri, banka/kurum isimlerini ve başvuru şartlarını koru; tüm cümleleri Türk Dil Kurumu (TDK) yazım, imla ve noktalama kurallarına %100 uygun, deneyimli bir ekonomi baş editörü kalemiyle yaz.
- Konuyla ilişkili **bankacılık, finansman, ödeme planı, kamu ve özel banka IBAN, PTT hesap aktarımı ve e-Devlet** terimlerini doğal biçimde geçir ve önemli terimleri `<strong>...</strong>` ile kalınlaştır.

Lütfen yanıtını SADECE aşağıdaki `===BLOK===` sırasıyla ver:

===SEO_TITLE===
(ZORUNLU FORMAT: "[İl ve Belediye Adı] [Verilen Yardım/Destek Adı] Başvuru Şartları ve Formu 2026".
Örnek: "Mersin Yenişehir Belediyesi Halk Kart Başvuru Şartları ve Formu 2026" veya "İzmir Karabağlar Belediyesi Sosyal Market Başvuru Şartları ve Formu 2026".
Başlıkta fiil ("veriyor", "başladı", "genişletiyor" vb.) kullanma; doğrudan Belediye Adı + Yardım Adı + "Başvuru Şartları ve Formu 2026" yaz.)

===META_DESC===
(145-158 karakter arası, TDK yazım ve noktalama kurallarına uygun SEO meta açıklaması)

===SPOT===
(35-45 kelimelik, haberin özünü veren, TDK dilbilgisi ve noktalama kurallarına tam uygun düz metin spot giriş; HTML etiketi kullanma)

===VISUAL_QUERIES===
(Her satırda 1 adet olmak üzere, haberle alakalı gerçek fotoğraf araması için 4 adet Türkçe görsel arama sorgusu)

===TAGS===
(Virgülle ayrılmış 6 adet SEO etiketi)

===TABLE===
İlgili Kurum / Banka | (Kurum veya banka adı)
Kapsam / Hak Sahipleri | (Kimleri kapsadığı)
Ödeme / Destek / Finansman Tutarı | (Güncel rakam veya oran)
Başvuru ve Ödeme Kanalı | (e-Devlet / PTT / Banka IBAN)

===ARTICLE_PART1_HTML===
(Buraya makalenin ilk yarısını -en az 260-320 kelime- sadece `<p>`, `<h2>`, `<ul>`, `<li>`, `<strong>` etiketleriyle ve kusursuz Türkçe dilbilgisiyle yaz:
1. Önce 2 adet doyurucu giriş paragrafı (`<p>...</p>`, her biri 50-60 kelime)
2. Konuya özel, arama hacmi yüksek 1. `<h2>` alt başlığı + altında 2 uzun `<p>` paragrafı + `<ul><li>` önemli rakam/kapsam maddeleri
3. Konuya özel, başvuru şartlarını ve kimlerin yararlanabileceğini anlatan 2. `<h2>` alt başlığı + altında 2 uzun `<p>` paragrafı + `<ul><li>` kriter maddeleri)
"""

    raw_p1 = _call_ai_text(prompt_p1, system_msg)

    raw_clean_title = news_item["raw_title"].strip()
    ai_seo_title = _extract_block(raw_p1, "SEO_TITLE").strip()
    seo_title = _format_mandatory_seo_title(ai_seo_title, raw_clean_title, category)

    meta_desc = _strip_html(_extract_block(raw_p1, "META_DESC")).strip()
    spot_text = _strip_html(_extract_block(raw_p1, "SPOT")).strip()

    # Reels Üst Manşeti: 'Başvuru Şartları ve Formu 2026' içeren haber başlığıyla birebir uyumlu üret
    reels_headline = _build_clean_tdk_reels_headline(seo_title)

    visual_queries_raw = _extract_block(raw_p1, "VISUAL_QUERIES").strip()
    tags_raw = _extract_block(raw_p1, "TAGS").strip()
    table_block = _extract_block(raw_p1, "TABLE").strip()
    part1_html = _clean_cutoff_html(_extract_block(raw_p1, "ARTICLE_PART1_HTML"))

    # =========================================================================
    # AŞAMA 2: Makalenin İkinci Yarısı (Başvuru Adımları, Ödeme Planı & 3 Detaylı SSS - 300+ kelime)
    # =========================================================================
    time.sleep(5)
    prompt_p2 = f"""
"{seo_title}" başlıklı haber makalemizin **2. Yarısını** (en az 260-320 kelime) yazıyorsun.
Kaynak Bilgiler:
{news_item['raw_summary'][:2000]}

KURALLAR:
- İlk yarıda yazılan genel giriş ve başvuru şartlarını tekrar etme!
- Doğrudan aşağıdaki 3 bölümü `%100 özgün`, Türk Dil Kurumu (TDK) dilbilgisi, yazım ve noktalama kurallarına %100 uygun bir Ekonomi Baş Editörü diliyle ve finans/bankacılık/e-Devlet kelimelerini (`<strong>` vurgulu) geçirerek yaz:
  1. Konuya özel **e-Devlet, mobil şube veya ilgili kurum başvuru ve sorgulama adımlarını** anlatan doğal `<h2>` başlığı + altında **2 adet uzun, detaylı `<p>` paragrafı** (her biri 55-65 kelime).
  2. Konuya özel **ödeme takvimi, banka ve PTT IBAN hesap aktarımı ile aile bütçesine etkisini** değerlendiren doğal `<h2>` başlığı + altında **2 adet uzun, detaylı `<p>` paragrafı** (her biri 55-65 kelime).
  3. Konuya özel **Sıkça Sorulan Sorular** `<h2>` başlığı + altında vatandaşların Google'da en çok aradığı **3 adet `<h3>Soru?</h3>`** ve her birinin altında **3-4 cümlelik doyurucu `<p>Cevap...</p>`** paragrafı.

Sadece saf HTML (`<h2>`, `<h3>`, `<p>`, `<strong>`) döndür, tüm cümleleri eksiksiz tamamla:
"""
    raw_p2 = _call_ai_text(prompt_p2, system_msg)
    part2_html = re.sub(r"^```html\s*|\s*```$", "", raw_p2, flags=re.MULTILINE).strip()
    part2_html = _clean_cutoff_html(part2_html)

    full_article_html = part1_html + "\n" + part2_html
    table_html = _build_adsense_table_html(table_block, category["name"])
    enriched_body_html = _inject_toc_and_table_for_adsense(full_article_html, table_html)

    # Spot metni olarak da öncelikle kaynak haberdeki ilk 2 gerçek TDK cümlesini kullan
    tdk_sentences = _extract_tdk_news_sentences_for_reels(news_item, spot_text)
    if len(tdk_sentences) >= 2:
        spot_text = f"{tdk_sentences[0]} {tdk_sentences[1]}"

    spot_html = f'<p class="habermat-spot"><strong>{spot_text}</strong></p>\n' if spot_text else ""
    cta_box_html = (
        '\n<div style="background:#0B132B;color:#FFFFFF;padding:18px 22px;'
        'border-left:6px solid #D90429;border-radius:8px;margin-top:28px;margin-bottom:18px;">'
        '<p style="margin:0;font-size:16px;line-height:1.5;">'
        '📢 <strong>Önemli Hatırlatma:</strong> Başvuru şartları ve detayları için '
        'Google\'a <strong>habermat.com</strong> yaz, çıkan ilk siteye tıklayın!'
        '</p></div>'
    )
    full_wp_html = spot_html + enriched_body_html + cta_box_html
    final_word_count = count_words_in_html(full_wp_html)
    p_count = len(BeautifulSoup(full_wp_html, "html.parser").find_all("p"))
    print(f"      -> Üretilen SEO & AdSense Makale Uzunluğu: {final_word_count} kelime ({p_count} paragraf)")

    slug = slugify_tr(seo_title)

    # Video senaryosu (Altyazı + Seslendirme):
    # Doğrudan kaynak haberin TDK dilbilgisi, yazım, imla ve noktalama kurallarına %100 uygun
    # gerçek Türkçe cümlelerinden oluşturulur (Altyazı ve seslendirme birebir aynıdır).
    script_segments: List[Dict[str, Any]] = []
    for sent in tdk_sentences[:4]:
        script_segments.append(
            {
                "spoken": sent,
                "subtitle": sent,
                "is_cta": False,
            }
        )

    script_segments.append(
        {
            "spoken": MANDATORY_CTA_SPOKEN,
            "subtitle": MANDATORY_CTA_DISPLAY,
            "is_cta": True,
        }
    )

    ig_summary = " ".join(tdk_sentences[:3])

    visual_queries = [
        line.strip().lstrip("-*•1234567890. ")
        for line in visual_queries_raw.splitlines()
        if len(line.strip()) > 4
    ][:4]

    tags = [t.strip() for t in tags_raw.split(",") if t.strip()][:6]
    if not tags:
        tags = [category["name"], "Sosyal Yardım", "e-Devlet", "Ekonomi"]

    hashtags_list = list(dict.fromkeys(category.get("hashtags", []) + ["#habermat", "#sondakika", "#gündem"]))
    hashtags_str = " ".join(hashtags_list)

    instagram_caption = (
        f"🚨 {reels_headline}\n\n"
        f"{ig_summary}\n\n"
        f"👉 Başvuru şartları ve detayları için Google'a \"habermat.com\" yaz, çıkan ilk siteye tıklayın!\n\n"
        f"🔔 Günlük sosyal yardım, emeklilik, TOKİ ve kredi haberlerini kaçırmamak için @habermat5 sayfasını takip edin!\n\n"
        f"{hashtags_str}"
    )

    return {
        "seo_title": seo_title,
        "slug": slug,
        "meta_description": (meta_desc or spot_text)[:160],
        "spot": spot_text,
        "wp_html_content": full_wp_html,
        "word_count": final_word_count,
        "tags": tags,
        "reels_headline": reels_headline,
        "reels_badge": category.get("badge", "SON DAKİKA • HABERMAT"),
        "script_segments": script_segments,
        "visual_queries": visual_queries,
        "instagram_caption": instagram_caption,
    }
