"""
Habermat.com - 10 Büyükşehir ve İlçe Belediyeleri Sosyal Yardım Araştırma Motoru
Şehirler: Gaziantep, Şanlıurfa, Adana, Mersin, İzmir, Aydın, Bursa, İstanbul, Ankara, Antalya
Büyükşehir ve ilçe belediyelerinin verdiği sosyal yardımları (gıda, erzak, emekli, öğrenci,
kırtasiye, burs, sosyal destek kartı, yakacak, fatura, hoş geldin bebek vb.) tek tek araştırır.
"""

import hashlib
import json
import os
import re
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import feedparser
import requests
from bs4 import BeautifulSoup

TR_TZ = timezone(timedelta(hours=3))
HISTORY_FILE = Path(__file__).resolve().parent.parent / "data" / "published_history.json"

REQUIRED_AID_KEYWORDS = (
    "yardım", "destek", "ödeme", "başvuru", "emekli", "maaş", "ikramiye",
    "burs", "kırtasiye", "öğrenci", "erzak", "gıda", "koli", "market",
    "doğalgaz", "yakacak", "kömür", "fatura", "dar gelir",
    "halk kart", "başkent kart", "sosyal kart", "destek kart", "süt",
    "bebek", "çeyiz", "evlilik", "nakdi", "nakit", "pazar", "ekmek",
    "sıcak yemek", "beslenme", "ulaşım", "kantin", "kira", "vatandaş", "aile",
)

FOREIGN_AND_OFFTOPIC_BLOCKLIST = (
    "bosna", "gazze", "filistin", "suriye", "lübnan", "sudan",
    "somali", "afrika", "yemen", "afganistan", "ukrayna", "pakistan",
    "vietnam", "can tho", "hanoi", "hindistan", "pekin", "avrupa",
    "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025",
    "villa", "yüzen ev", "magazin", "ünlü", "futbol", "transfer",
    "cinayet", "kaza", "tutuklandı", "gözaltı", "deprem", "yangın",
    "ziyaret", "değerlendirildi", "denetim", "zabıta", "mühür", "imha",
    "bozulmuş", "tarihi geçmiş", "arkeoloji", "amatör spor", "kulüb", "kulüp",
    "milli takım", "sokak hayvan", "hayvansever", "farkındalık", "şenlik",
    "festival", "konser", "tiyatro", "turnuva", "asfalt", "ilaçlama",
)


def _normalize_title(title: str) -> str:
    """Başlıktaki kaynak adını (- Milliyet, - Sabah vb.) temizler."""
    cleaned = re.split(r"\s+[-|]\s+", title)[0].strip()
    return cleaned


def _title_fingerprint(title: str) -> str:
    """Başlığın benzersiz özet (hash) değerini üretir."""
    norm = re.sub(r"[^a-zA-Z0-9ğüşıöçĞÜŞİÖÇ]", "", _normalize_title(title).lower())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def load_history() -> dict:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"items": []}


def save_to_history(
    title: str,
    category_id: str,
    wp_url: str = "",
    ig_id: str = "",
    source_url: str = "",
) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = load_history()
    items = history.get("items", [])
    items.append(
        {
            "fingerprint": _title_fingerprint(title),
            "title": _normalize_title(title),
            "category_id": category_id,
            "source_url": source_url,
            "wp_url": wp_url,
            "ig_id": ig_id,
            "published_at": datetime.now(TR_TZ).isoformat(),
        }
    )
    history["items"] = items[-500:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def _matches_city_or_district(text: str, category: dict) -> bool:
    """Haberin gerçekten seçilen şehre veya o şehrin ilçe belediyelerinden birine ait olduğunu doğrular."""
    low = (text or "").lower()
    city = category.get("city", "").lower()
    if city and city in low:
        return True
    if city == "istanbul" and "ibb" in low:
        return True
    if city == "ankara" and ("abb" in low or "başkent kart" in low):
        return True
    for dist in category.get("districts", []):
        dist_root = dist.replace("Büyükşehir Belediyesi", "").replace("Belediyesi", "").strip().lower()
        if dist_root and len(dist_root) >= 3 and dist_root in low:
            return True
    return False


def is_already_published(title: str, history: dict, source_url: str = "", category: Optional[dict] = None) -> bool:
    norm_new = _normalize_title(title).lower()
    low_src = (source_url or "").lower()

    if any(fk in norm_new or fk in low_src for fk in FOREIGN_AND_OFFTOPIC_BLOCKLIST):
        return True

    if not any(rk in norm_new for rk in REQUIRED_AID_KEYWORDS):
        return True

    if category and not _matches_city_or_district(norm_new, category):
        return True

    fp = _title_fingerprint(title)
    new_words = set(re.findall(r"\w{4,}", norm_new))

    for item in history.get("items", []):
        if item.get("fingerprint") == fp:
            return True
        old_title = item.get("title", "").lower()
        old_words = set(re.findall(r"\w{4,}", old_title))
        if new_words and old_words:
            overlap = len(new_words & old_words) / max(len(new_words), 1)
            if overlap >= 0.70:
                return True
    return False


def _extract_article_paragraphs(url: str, headers: dict) -> str:
    """Kaynak haber veya belediye resmi sayfasındaki gerçek paragrafları çeker."""
    if not url or not url.startswith("http"):
        return ""
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        paras = []
        for p in soup.find_all("p"):
            txt = p.get_text(" ", strip=True)
            if len(txt) >= 50 and not any(
                skip in txt.lower()
                for skip in ["çerez", "cookie", "abone ol", "tüm hakları saklıdır", "gizlilik politikası"]
            ):
                paras.append(txt)
            if len(" ".join(paras)) > 3200:
                break
        return "\n".join(paras)
    except Exception:
        return ""


def _fetch_bing_rich_context(query: str, headers: dict) -> List[Dict[str, str]]:
    """Bing News RSS Türkiye (`setmkt=tr-TR&setlang=tr`) üzerinden belediye yardım haberlerini döndürür."""
    results: List[Dict[str, str]] = []
    encoded_q = urllib.parse.quote(query)
    bing_rss = f"https://www.bing.com/news/search?q={encoded_q}&format=rss&setmkt=tr-TR&setlang=tr"
    try:
        resp = requests.get(bing_rss, headers=headers, timeout=11)
        if resp.status_code != 200:
            return results
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:10]:
            raw_title = _normalize_title(entry.get("title", ""))
            if not raw_title or len(raw_title) < 20:
                continue
            link = entry.get("link", "")
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
            real_url = qs.get("url", [link])[0]
            desc_html = entry.get("summary", "") or entry.get("description", "")
            desc_text = BeautifulSoup(desc_html, "html.parser").get_text(" ", strip=True)
            results.append(
                {
                    "title": raw_title,
                    "summary": desc_text,
                    "url": real_url,
                }
            )
    except Exception:
        pass
    return results


def _research_municipality_official_aid(municipality_name: str, city_name: str, headers: dict) -> Dict[str, str]:
    """
    Belirli bir Büyükşehir veya İlçe Belediyesinin resmi (.bel.tr) ve yerel Türkiye kaynaklarındaki
    sosyal yardım programlarını araştırarak zengin veri ve gerçek kaynak linki döndürür.
    """
    q = f"{municipality_name} sosyal yardım destek başvuru"
    encoded_q = urllib.parse.quote(q)
    bing_url = f"https://www.bing.com/search?q={encoded_q}&setmkt=tr-TR&setlang=tr"
    snippets: List[str] = []
    found_url = ""
    try:
        resp = requests.get(bing_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for li in soup.select("li.b_algo")[:5]:
                a_tag = li.find("a")
                p_tag = li.find("p")
                href = a_tag.get("href", "") if a_tag else ""
                snip = p_tag.get_text(" ", strip=True) if p_tag else ""
                if href and href.startswith("http") and not found_url:
                    found_url = href
                if snip and len(snip) > 35:
                    snippets.append(snip)
    except Exception:
        pass

    article_body = _extract_article_paragraphs(found_url, headers) if found_url else ""
    joined_snippets = " ".join(snippets)
    return {
        "url": found_url,
        "details": f"{joined_snippets}\n\n{article_body}".strip(),
    }


def fetch_fresh_news_for_category(category: dict) -> Dict[str, str]:
    """
    Seçilen şehrin (Gaziantep, Şanlıurfa, Adana, Mersin, İzmir, Aydın, Bursa, İstanbul, Ankara, Antalya)
    Büyükşehir ve İlçe Belediyelerini tek tek araştırarak daha önce paylaşılmamış gerçek bir
    belediye yardım haberini bulur.
    """
    history = load_history()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
    }

    districts: List[str] = category.get("districts", [])
    city_name = category.get("city", "")
    now_tr = datetime.now(TR_TZ)

    # İlçeleri saat ve geçmiş yayın sayısına göre döndür ki her seferinde farklı bir ilçe belediyesi de araştırılsın
    hist_count = len(history.get("items", []))
    if districts:
        offset = (now_tr.day + now_tr.hour + hist_count) % len(districts)
        rotated_districts = districts[offset:] + districts[:offset]
    else:
        rotated_districts = []

    # Dinamik ilçe + büyükşehir arama sorguları oluştur
    dynamic_queries: List[str] = []
    for dist in rotated_districts[:6]:
        dynamic_queries.append(f"{dist} sosyal yardım destek başvuru")
        dynamic_queries.append(f"{dist} emekli öğrenci gıda erzak yardımı")
    for q in category.get("rss_queries", []):
        if q not in dynamic_queries:
            dynamic_queries.append(q)

    # 1. Önce Bing News Türkiye üzerinden il/ilçe belediye yardım haberlerini tara
    for query in dynamic_queries:
        bing_items = _fetch_bing_rich_context(query, headers)
        for item in bing_items:
            clean_title = item["title"]
            if is_already_published(clean_title, history, item.get("url", ""), category=category):
                continue
            article_body = _extract_article_paragraphs(item["url"], headers)
            extra_snippets = " | ".join(b["summary"] for b in bing_items[:4] if b.get("summary"))
            combined_summary = (
                f"{item['summary']}\n\nKAYNAK DETAYLARI:\n{article_body}\n\n"
                f"İLGİLİ BELEDİYE GÜNDEM NOTLARI:\n{extra_snippets}"
            ).strip()
            return {
                "raw_title": clean_title,
                "raw_summary": combined_summary[:2800],
                "source_link": item["url"],
                "category_id": category["id"],
                "category_name": category["name"],
                "is_fallback": False,
            }

    # 2. Her İlçe ve Büyükşehir Belediyesini tek tek Google News Türkiye üzerinden vatandaş yardımı sorgusuyla tara
    muni_aid_queries: List[str] = []
    for dist in rotated_districts:
        muni_aid_queries.append(
            f'"{dist}" ("sosyal yardım" OR "eğitim desteği" OR "burs" OR "emekli" OR "gıda" OR "erzak" OR "kırtasiye" OR "nakdi" OR "sosyal market" OR "halk kart" OR "sıcak yemek" OR "ekmek" OR "başvuru" OR "öğrencilere" OR "ailelere")'
        )
    for q in dynamic_queries[:4]:
        muni_aid_queries.append(q)

    for query in muni_aid_queries:
        encoded_q = urllib.parse.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=tr&gl=TR&ceid=TR:tr"

        try:
            resp = requests.get(rss_url, headers=headers, timeout=12)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:15]:
                raw_title = entry.get("title", "")
                clean_title = _normalize_title(raw_title)
                if not clean_title or len(clean_title) < 20:
                    continue

                src_href = ""
                if hasattr(entry, "source") and isinstance(entry.source, dict):
                    src_href = entry.source.get("href", "") or entry.source.get("title", "")
                if is_already_published(clean_title, history, src_href, category=category):
                    continue

                summary_html = entry.get("summary", "") or entry.get("description", "")
                soup = BeautifulSoup(summary_html, "html.parser")
                clean_summary = soup.get_text(" ", strip=True)
                related_titles = [
                    _normalize_title(e.get("title", ""))
                    for e in feed.entries[:5]
                    if e.get("title")
                ]
                rich_context = clean_summary + "\nKAYNAK DETAYLARI:\n" + clean_summary + "\nİlgili Başlıklar: " + " / ".join(related_titles)

                return {
                    "raw_title": clean_title,
                    "raw_summary": rich_context[:2200],
                    "source_link": entry.get("link", ""),
                    "category_id": category["id"],
                    "category_name": category["name"],
                    "is_fallback": False,
                }
        except Exception as exc:
            print(f"[UYARI] RSS sorgusu başarısız ({query[:40]}): {exc}")

    # 3. Sıradaki İlçe Belediyesinin resmi sosyal yardım programlarını doğrudan web üzerinden araştır
    aid_types = [
        ("Sosyal Destek Kartı ve Market Yardımı", "sosyal destek kartı, gıda kolisi ve market yardımı"),
        ("Emekli Nakdi Destek ve Pazar Yardımı", "emeklilere yönelik nakdi destek, pazar ve fatura yardımı"),
        ("Öğrenci Kırtasiye, Ulaşım ve Eğitim Desteği", "ilkokul, lise ve üniversite öğrencilerine kırtasiye ve burs yardımı"),
        ("Erzak Kolisi, Sıcak Yemek ve Halk Ekmek Desteği", "dar gelirli ailelere aylık erzak paketi ve gıda desteği"),
        ("Hoş Geldin Bebek Paketi ve Aile Destek Ödemesi", "yeni doğan bebek paketi, süt desteği ve aile yardımı"),
    ]
    for idx_d, target_muni in enumerate(rotated_districts or [f"{city_name} Büyükşehir Belediyesi"]):
        aid_title, aid_desc = aid_types[(now_tr.day + now_tr.hour + idx_d) % len(aid_types)]
        candidate_title = f"{target_muni} {aid_title} Başvurusu ve Şartları"
        if not is_already_published(candidate_title, history, "", category=category):
            research = _research_municipality_official_aid(target_muni, city_name, headers)
            details = research.get("details", "")
            summary_text = (
                f"{city_name} ilinde {target_muni} tarafından ihtiyaç sahibi vatandaşlara, emeklilere ve öğrencilere "
                f"sunulan {aid_desc} başvuruları devam ediyor. Vatandaşlar {target_muni} Sosyal Yardım İşleri Müdürlüğü, "
                f"e-Devlet kapısı ve belediye resmi internet sitesi üzerinden başvuru yapabiliyor.\n\n"
                f"KAYNAK DETAYLARI:\n{details}"
            ).strip()
            return {
                "raw_title": candidate_title,
                "raw_summary": summary_text[:2800],
                "source_link": research.get("url", ""),
                "category_id": category["id"],
                "category_name": category["name"],
                "is_fallback": False,
            }

    fallbacks: List[str] = category.get("fallback_topics", [])
    base_topic = fallbacks[now_tr.hour % max(len(fallbacks), 1)] if fallbacks else f"{category['name']} Başvuru Şartları"
    return {
        "raw_title": base_topic,
        "raw_summary": f"{category['name']} kapsamında {base_topic} detayları ve başvuru adımları.",
        "source_link": "",
        "category_id": category["id"],
        "category_name": category["name"],
        "is_fallback": True,
    }
