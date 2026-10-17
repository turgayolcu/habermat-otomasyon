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


def _clean_cutoff_html(html_text: str) -> str:
    """Eğer model çıktısının en son satırı yarım kalmışsa güvenli şekilde tamamlanmış son etikete keser."""
    html_text = html_text.strip()
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
- Kaynak haberdeki gerçek rakamları, tarihleri, banka/kurum isimlerini ve başvuru şartlarını koru; ancak cümleleri %100 özgünleştirerek deneyimli bir ekonomi baş editörü kalemiyle yaz.
- Google AdSense yüksek TBM (CPC) reklam eşleşmesi için konuyla ilişkili **bankacılık, finansman, ödeme planı, kamu/özel banka IBAN, PTT hesap aktarımı ve e-Devlet** terimlerini doğal biçimde geçir ve önemli terimleri `<strong>...</strong>` ile kalınlaştır.

Lütfen yanıtını SADECE aşağıdaki `===BLOK===` sırasıyla ver:

===SEO_TITLE===
(55-68 karakter arası, Google Keşfet tıklama oranı yüksek özgün Türkçe başlık)

===META_DESC===
(145-158 karakter arası, odak anahtar kelimeli SEO meta açıklaması)

===SPOT===
(35-45 kelimelik, haberin özünü veren güçlü düz metin spot giriş; HTML etiketi kullanma)

===REELS_HEADLINE===
(Makalenin başlığıyla birebir bağlantılı, videonun üst kartında yazacak BÜYÜK HARFLİ, maksimum 5-6 kelimelik çarpıcı kısa manşet!)

===REELS_HOOK===
(Makaledeki haberi tanıtan, videonun ilk 3 saniyesinde Türk kadın haber spikerinin tek nefeste kesintisiz okuyacağı, içinde virgül veya noktalı virgül OLMAYAN ve tam yüklemle biten 1 akıcı giriş cümlesi! Örn: "e-Devlet üzerinden yeni destek ödemeleri için başvuru ekranı bugün resmen açıldı.")

===REELS_BODY===
(Makaledeki haberin birebir özeti olan, her satırda 1 cümle olacak şekilde toplam 3 adet tek nefeste okunan TV haber spikeri cümlesi:
- Her cümle 10-13 kelime arası olmalı, cümle içinde sesin kesilmemesi için ASLA virgül (,) veya noktalı virgül (;) kullanılmamalı ve cümle sonunda çekimli Türkçe yüklem ("açıklandı", "yatırılıyor", "yapılabiliyor" vb.) yer almalıdır!
- Asla devrik/kesik cümle kurma, parantez kullanma, 'TL' yerine 'lira' yaz ve rakamları doğal konuşma diliyle yaz!)

===VISUAL_QUERIES===
(Her satırda 1 adet olmak üzere, haberle alakalı gerçek fotoğraf araması için 4 adet Türkçe görsel arama sorgusu)

===IG_SUMMARY===
(TikTok açıklaması için 3-4 cümlelik düz metin özet)

===TAGS===
(Virgülle ayrılmış 6 adet SEO etiketi)

===TABLE===
İlgili Kurum / Banka | (Kurum veya banka adı)
Kapsam / Hak Sahipleri | (Kimleri kapsadığı)
Ödeme / Destek / Finansman Tutarı | (Güncel rakam veya oran)
Başvuru ve Ödeme Kanalı | (e-Devlet / PTT / Banka IBAN)

===ARTICLE_PART1_HTML===
(Buraya makalenin ilk yarısını -en az 260-320 kelime- sadece `<p>`, `<h2>`, `<ul>`, `<li>`, `<strong>` etiketleriyle yaz:
1. Önce 2 adet doyurucu giriş paragrafı (`<p>...</p>`, her biri 50-60 kelime)
2. Konuya özel, arama hacmi yüksek 1. `<h2>` alt başlığı + altında 2 uzun `<p>` paragrafı + `<ul><li>` önemli rakam/kapsam maddeleri
3. Konuya özel, başvuru şartlarını ve kimlerin yararlanabileceğini anlatan 2. `<h2>` alt başlığı + altında 2 uzun `<p>` paragrafı + `<ul><li>` kriter maddeleri)
"""

    raw_p1 = _call_ai_text(prompt_p1, system_msg)

    seo_title = _strip_html(_extract_block(raw_p1, "SEO_TITLE") or news_item["raw_title"]).strip()
    meta_desc = _strip_html(_extract_block(raw_p1, "META_DESC")).strip()
    spot_text = _strip_html(_extract_block(raw_p1, "SPOT")).strip()
    reels_headline = _strip_html(_extract_block(raw_p1, "REELS_HEADLINE") or seo_title).strip().upper()
    # Eğer manşet çok uzunsa ilk 6 kelimeye kısalt
    if len(reels_headline.split()) > 7:
        reels_headline = " ".join(reels_headline.split()[:6])
    reels_hook = _strip_html(_extract_block(raw_p1, "REELS_HOOK")).strip()
    reels_body_raw = _extract_block(raw_p1, "REELS_BODY").strip()
    visual_queries_raw = _extract_block(raw_p1, "VISUAL_QUERIES").strip()
    ig_summary = _strip_html(_extract_block(raw_p1, "IG_SUMMARY") or spot_text).strip()
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
- Doğrudan aşağıdaki 3 bölümü `%100 özgün`, akıcı bir Kıdemli SEO Uzmanı & Ekonomi Editörü diliyle ve **Google AdSense yüksek TBM (CPC)** finans/bankacılık/e-Devlet kelimelerini (`<strong>` vurgulu) geçirerek yaz:
  1. Konuya özel **e-Devlet, mobil şube veya ilgili kurum başvuru/sorgulama adımlarını** anlatan doğal `<h2>` başlığı + altında **2 adet uzun, detaylı `<p>` paragrafı** (her biri 55-65 kelime).
  2. Konuya özel **ödeme takvimi, banka/PTT IBAN hesap aktarımı ve aile bütçesine/finansmana etkisini** değerlendiren doğal `<h2>` başlığı + altında **2 adet uzun, detaylı `<p>` paragrafı** (her biri 55-65 kelime).
  3. Konuya özel **Sıkça Sorulan Sorular** `<h2>` başlığı + altında vatandaşların Google'da en çok aradığı **3 adet `<h3>Soru?</h3>`** ve her birinin altında **3-4 cümlelik doyurucu `<p>Cevap...</p>`** paragrafı.

Sadece saf HTML (`<h2>`, `<h3>`, `<p>`, `<strong>`) döndür, tüm cümleleri eksiksiz tamamla:
"""
    raw_p2 = _call_ai_text(prompt_p2, system_msg)
    part2_html = re.sub(r"^```html\s*|\s*```$", "", raw_p2, flags=re.MULTILINE).strip()
    part2_html = _clean_cutoff_html(part2_html)

    full_article_html = part1_html + "\n" + part2_html
    table_html = _build_adsense_table_html(table_block, category["name"])
    enriched_body_html = _inject_toc_and_table_for_adsense(full_article_html, table_html)

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

    # Video senaryosu segmentlerini oluştur
    script_segments: List[Dict[str, Any]] = []
    if reels_hook:
        script_segments.append(
            {
                "spoken": reels_hook,
                "subtitle": reels_hook,
                "is_cta": False,
            }
        )
    for line in reels_body_raw.splitlines():
        cleaned_line = re.sub(r"^[-*•]\s*|^\d+[.)]\s+", "", line.strip())
        sent = _strip_html(cleaned_line).strip().strip('"\'“”')
        if not sent or len(sent) < 10:
            continue
        if "habermat" in sent.lower() or "ilk siteye" in sent.lower():
            continue
        script_segments.append(
            {
                "spoken": sent,
                "subtitle": sent,
                "is_cta": False,
            }
        )

    # Eğer herhangi bir nedenle gelişme cümleleri boş geldiyse spot metninden 3 cümle üret
    if len(script_segments) < 2 and spot_text:
        for s in re.split(r"(?<=[.!?])\s+", spot_text)[:3]:
            if len(s.strip()) > 12:
                script_segments.append(
                    {
                        "spoken": s.strip(),
                        "subtitle": s.strip(),
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
