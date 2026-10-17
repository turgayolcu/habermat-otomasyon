"""
Habermat.com - Güncel Haber Tarayıcı (Google News RSS + Tekrar Önleme Sistemi)
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


def _normalize_title(title: str) -> str:
    """Başlıktaki kaynak adını (- Milliyet, - Sabah vb.) temizler ve küçük harfe çevirir."""
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
    # Son 500 haberi tut
    history["items"] = items[-500:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def is_already_published(title: str, history: dict) -> bool:
    norm_new = _normalize_title(title).lower()
    # Yurt dışı insani yardım haberlerini atla (Sadece Türkiye içi vatandaş başvuruları seçilsin)
    foreign_keywords = [
        "bosna", "gazze", "filistin", "suriye", "lübnan", "sudan",
        "somali", "afrika", "yemen", "afganistan", "ukrayna", "pakistan",
    ]
    if any(fk in norm_new for fk in foreign_keywords):
        return True

    fp = _title_fingerprint(title)
    new_words = set(re.findall(r"\w{4,}", norm_new))

    for item in history.get("items", []):
        if item.get("fingerprint") == fp:
            return True
        old_title = item.get("title", "").lower()
        old_words = set(re.findall(r"\w{4,}", old_title))
        # Kelime benzerliği %70'in üzerindeyse aynı haber kabul et
        if new_words and old_words:
            overlap = len(new_words & old_words) / max(len(new_words), 1)
            if overlap >= 0.70:
                return True
    return False


def _extract_article_paragraphs(url: str, headers: dict) -> str:
    """Kaynak haber URL'sindeki gerçek paragrafları çekerek AI için zengin bilgi havuzu oluşturur."""
    if not url:
        return ""
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        paras = []
        for p in soup.find_all("p"):
            txt = p.get_text(" ", strip=True)
            if len(txt) >= 55 and not any(
                skip in txt.lower()
                for skip in ["çerez", "cookie", "abone ol", "tüm hakları saklıdır", "gizlilik politikası"]
            ):
                paras.append(txt)
            if len(" ".join(paras)) > 2400:
                break
        return "\n".join(paras)
    except Exception:
        return ""


def _fetch_bing_rich_context(query: str, headers: dict) -> List[Dict[str, str]]:
    """Bing News RSS üzerinden hem gerçek makale linklerini hem de detaylı özetleri döndürür."""
    results: List[Dict[str, str]] = []
    encoded_q = urllib.parse.quote(query)
    bing_rss = f"https://www.bing.com/news/search?q={encoded_q}&format=rss&setmkt=tr-TR&setlang=tr"
    try:
        resp = requests.get(bing_rss, headers=headers, timeout=12)
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


def fetch_fresh_news_for_category(category: dict) -> Dict[str, str]:
    """
    Seçilen kategori için son gündemdeki en güncel ve daha önce paylaşılmamış haberi bulur,
    kaynak haberin içerik paragraflarını çekerek SEO yazar motoruna zengin veri sağlar.
    """
    history = load_history()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
    }

    # 1. Önce Bing News RSS üzerinden tam metin erişimli güncel haberleri tara
    for query in category.get("rss_queries", []):
        bing_items = _fetch_bing_rich_context(query, headers)
        for item in bing_items:
            clean_title = item["title"]
            if is_already_published(clean_title, history):
                continue
            article_body = _extract_article_paragraphs(item["url"], headers)
            extra_Snippets = " | ".join(b["summary"] for b in bing_items[:4] if b.get("summary"))
            combined_summary = f"{item['summary']}\n\nKAYNAK DETAYLARI:\n{article_body}\n\nİLGİLİ GÜNDEM NOTLARI:\n{extra_Snippets}".strip()
            return {
                "raw_title": clean_title,
                "raw_summary": combined_summary[:2800],
                "source_link": item["url"],
                "category_id": category["id"],
                "category_name": category["name"],
                "is_fallback": False,
            }

    # 2. Yedek olarak Google News RSS üzerinden tara
    for query in category.get("rss_queries", []):
        encoded_q = urllib.parse.quote(f"{query} when:3d")
        rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=tr&gl=TR&ceid=TR:tr"

        try:
            resp = requests.get(rss_url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:12]:
                raw_title = entry.get("title", "")
                clean_title = _normalize_title(raw_title)
                if not clean_title or len(clean_title) < 20:
                    continue

                if is_already_published(clean_title, history):
                    continue

                summary_html = entry.get("summary", "") or entry.get("description", "")
                soup = BeautifulSoup(summary_html, "html.parser")
                clean_summary = soup.get_text(" ", strip=True)
                related_titles = [
                    _normalize_title(e.get("title", ""))
                    for e in feed.entries[:6]
                    if e.get("title")
                ]
                rich_context = clean_summary + "\nİlgili Başlıklar: " + " / ".join(related_titles)

                return {
                    "raw_title": clean_title,
                    "raw_summary": rich_context[:1800],
                    "source_link": entry.get("link", ""),
                    "category_id": category["id"],
                    "category_name": category["name"],
                    "is_fallback": False,
                }
        except Exception as exc:
            print(f"[UYARI] RSS sorgusu başarısız ({query}): {exc}")

    # Eğer RSS'teki tüm haberler kullanıldıysa veya bağlantı hatası varsa fallback konu seç
    now_tr = datetime.now(TR_TZ)
    Turkish_months = [
        "", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
    ]
    month_name = Turkish_months[now_tr.month]
    fallbacks: List[str] = category.get("fallback_topics", [])
    idx = (now_tr.day + now_tr.hour) % max(len(fallbacks), 1)
    base_topic = fallbacks[idx] if fallbacks else f"{category['name']} Güncel Başvuru Şartları"
    dated_topic = f"{now_tr.year} {month_name} {base_topic}"

    return {
        "raw_title": dated_topic,
        "raw_summary": (
            f"{category['name']} kapsamında vatandaşların merakla beklediği {dated_topic} "
            f"detayları, başvuru şartları ve e-Devlet sorgulama adımları."
        ),
        "source_link": "",
        "category_id": category["id"],
        "category_name": category["name"],
        "is_fallback": True,
    }
