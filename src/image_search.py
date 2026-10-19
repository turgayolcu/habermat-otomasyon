"""
Habermat.com - Türkiye İçi Konu ve Anahtar Kelime Odaklı Haber Görseli Motoru
- "Türk Parası" kuralı tamamen kaldırılmıştır.
- Haberin başlığından ve konusundan anahtar kelimeleri çıkarır.
- Yalnızca Türkiye sınırları içerisindeki (`setmkt=tr-TR&setlang=tr` ve `site:tr`) gerçek haber kaynaklarından
  konuyla birebir örtüşen benzersiz haber kapak fotoğrafını indirir.
- Daha önce herhangi bir haberde/Reels'te kullanılmış görsel URL'lerini ve görüntü özetlerini (hash)
  `data/published_history.json` üzerinden kontrol ederek ASLA aynı kapak görselini tekrar kullanmaz.
"""

import hashlib
import html
import io
import json
import os
import re
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Set

import feedparser
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageStat

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

HISTORY_FILE = Path(__file__).resolve().parent.parent / "data" / "published_history.json"

# Yabancı stok siteleri, ABD/Avrupa teknoloji siteleri ve fotoğrafın üstüne dev manşet basan siteler engellenir
BLOCKED_IMAGE_DOMAINS = (
    "pexels.com",
    "unsplash.com",
    "pixabay.com",
    "rawpixel.com",
    "ftcdn.net",
    "shutterstock.com",
    "istockphoto.com",
    "depositphotos.com",
    "dreamstime.com",
    "123rf.com",
    "alamy.com",
    "vecteezy.com",
    "freepik.com",
    "pngtree.com",
    "flaticon.com",
    "logowik.com",
    "freelogovectors.net",
    "logovector.net",
    "pcmag.com",
    "ncag.info",
    "gannett-cdn.com",
    "radiologykey.com",
    "plex.tv",
    "windows10spotlight.com",
    "carthagemagazine.com",
    "tenorshare.ai",
    "devletodemeleri.com",
    "kamugundemi.com",
    "emlak365.com",
    "sikayetvar.com",
    "tavsanlihaber.com",
    "sabirgazetesi",
    "takvim.com.tr",
    "ahaber.com.tr",
    "fotomac.com.tr",
    "googleusercontent.com",
    "gstatic.com",
)

# Görsel URL'sinde geçmemesi gereken alakasız/varsayılan/ödül kelimeleri
BLOCKED_IMAGE_URL_KEYWORDS = (
    ".svg",
    ".gif",
    "logo",
    "icon",
    "avatar",
    "sprite",
    "periodic",
    "1x1",
    "pixel",
    "share-img",
    "default",
    "placeholder",
    "sardis",
    "odul",
    "ödül",
    "20261007aw804478",
    "sincan-da-colyak-hastalarina",
)

# 10 Şehir Büyükşehir ve İlçe Belediyeleri için Türkiye içi konu anahtar kelime sorguları
CATEGORY_TOPIC_QUERIES: Dict[str, List[str]] = {
    "gaziantep_belediye": [
        "Gaziantep Büyükşehir Belediyesi sosyal yardım",
        "Şahinbey Belediyesi sosyal destek yardımı",
        "Şehitkamil Belediyesi gıda yardımı",
        "Gaziantep belediye sosyal market destek",
    ],
    "sanliurfa_belediye": [
        "Şanlıurfa Büyükşehir Belediyesi sosyal yardım",
        "Haliliye Belediyesi gıda erzak yardımı",
        "Eyyübiye Karaköprü Belediyesi sosyal destek",
        "Şanlıurfa belediye yardım dağıtımı",
    ],
    "adana_belediye": [
        "Adana Büyükşehir Belediyesi sosyal yardım",
        "Seyhan Belediyesi Yüreğir Belediyesi yardım",
        "Çukurova Sarıçam Belediyesi sosyal destek",
        "Adana belediye gıda kolisi halk kart",
    ],
    "mersin_belediye": [
        "Mersin Büyükşehir Belediyesi Halk Kart yardım",
        "Tarsus Akdeniz Toroslar Belediyesi sosyal yardım",
        "Yenişehir Mezitli Belediyesi sosyal destek",
        "Mersin belediye gıda eğitim yardımı",
    ],
    "izmir_belediye": [
        "İzmir Büyükşehir Belediyesi sosyal yardım",
        "Buca Karabağlar Bornova Belediyesi yardım",
        "Konak Karşıyaka Bayraklı Belediyesi sosyal destek",
        "İzmir belediye dayanışma gıda yardımı",
    ],
    "aydin_belediye": [
        "Aydın Büyükşehir Belediyesi sosyal yardım",
        "Efeler Nazilli Söke Belediyesi sosyal destek",
        "Kuşadası Didim Belediyesi yardım paketi",
        "Aydın belediye gıda emekli desteği",
    ],
    "bursa_belediye": [
        "Bursa Büyükşehir Belediyesi sosyal yardım",
        "Osmangazi Yıldırım Nilüfer Belediyesi yardım",
        "İnegöl Gemlik Belediyesi sosyal destek",
        "Bursa belediye erzak emekli öğrenci desteği",
    ],
    "istanbul_belediye": [
        "İstanbul Büyükşehir Belediyesi İBB sosyal yardım",
        "Üsküdar Ümraniye Pendik Esenyurt Belediyesi yardım",
        "Bağcılar Küçükçekmece Fatih Belediyesi sosyal destek",
        "İstanbul belediye sosyal destek kartı",
    ],
    "ankara_belediye": [
        "Çankaya Keçiören Yenimahalle Belediyesi sosyal yardım",
        "Mamak Sincan Etimesgut Altındağ Belediyesi destek",
        "Ankara Büyükşehir Belediyesi sosyal yardım kolisi",
        "Ankara belediye sosyal destek yardımı",
    ],
    "antalya_belediye": [
        "Antalya Büyükşehir Belediyesi sosyal yardım",
        "Kepez Muratpaşa Konyaaltı Belediyesi sosyal destek",
        "Alanya Manavgat Serik Belediyesi yardım",
        "Antalya belediye gıda eğitim desteği",
    ],
}


def _load_used_image_history() -> tuple[Set[str], Set[str]]:
    """Daha önce kullanılmış görsel URL'lerini ve hash'lerini yükler."""
    used_urls: Set[str] = set()
    used_hashes: Set[str] = set()
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for u in data.get("used_image_urls", []):
                used_urls.add(str(u))
            for h in data.get("used_image_hashes", []):
                used_hashes.add(str(h))
        except Exception:
            pass
    return used_urls, used_hashes


def _save_used_image_history(used_urls: Set[str], used_hashes: Set[str]) -> None:
    """Yeni kullanılan görsel URL ve hash'ini geçmiş dosyasına kaydeder."""
    try:
        data = {"items": []}
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["used_image_urls"] = list(used_urls)[-400:]
        data["used_image_hashes"] = list(used_hashes)[-400:]
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _is_clean_url(url: str) -> bool:
    """Yasaklı yabancı/stok siteleri ve ikon/logo/ödül uzantılarını reddeder."""
    if not url or not url.startswith("http"):
        return False
    low = url.lower()
    if any(bad in low for bad in BLOCKED_IMAGE_DOMAINS):
        return False
    if any(ext in low for ext in BLOCKED_IMAGE_URL_KEYWORDS):
        return False
    return True


def _extract_topic_keyword_queries(news_title: str, category: dict) -> List[str]:
    """
    Haberin başlığından anahtar kelimeleri seçerek Türkiye haber kaynaklarında
    aranacak konu sorgularını üretir.
    """
    cat_id = category.get("id", "devlet_yardimlari")
    cat_name = category.get("name", "")
    queries: List[str] = []

    if news_title:
        clean_full = re.split(r"\s+[-|]\s+", news_title)[0].strip()
        if len(clean_full) > 10:
            queries.append(clean_full[:70])

        no_nums = re.sub(r"\b\d+[\d.,]*\b", " ", clean_full)
        no_nums = re.sub(
            r"\b(TL|lira|bin|milyon|milyar|kaç|nasıl|nedir|ne zaman|kimler|için|gün|sayıyor|belli|oldu)\b",
            " ",
            no_nums,
            flags=re.IGNORECASE,
        )
        no_nums = re.sub(r"[^\w\sğüşıöçĞÜŞİÖÇ]", " ", no_nums)
        words = [w for w in no_nums.split() if len(w) >= 3]

        if len(words) >= 2:
            kw_short = " ".join(words[:4])
            if kw_short not in queries:
                queries.append(kw_short)
        if len(words) >= 3:
            kw_belediye = " ".join(words[:3]) + " belediye yardım"
            if kw_belediye not in queries:
                queries.append(kw_belediye)
        if len(words) >= 4:
            kw_mid = " ".join(words[1:5])
            if kw_mid not in queries:
                queries.append(kw_mid)

    for cq in CATEGORY_TOPIC_QUERIES.get(cat_id, []):
        if cq not in queries:
            queries.append(cq)

    if cat_name and cat_name not in queries:
        queries.append(cat_name)

    return queries


def _extract_images_from_turkish_article(article_url: str, max_imgs: int = 1) -> List[str]:
    """
    Türkiye'deki bir haber makalesinin (`source_link` veya Bing News TR sonucu)
    yalnızca ana kapak fotoğrafını (`og:image` / `twitter:image`) çeker.
    """
    found: List[str] = []
    if not article_url or not article_url.startswith("http"):
        return found
    if "news.google.com" in article_url.lower():
        return found
    if any(bad in article_url.lower() for bad in BLOCKED_IMAGE_DOMAINS):
        return found

    try:
        resp = requests.get(article_url, headers=HEADERS, timeout=7)
        if resp.status_code != 200:
            return found
        soup = BeautifulSoup(resp.content, "html.parser")

        for meta in [
            soup.find("meta", property="og:image"),
            soup.find("meta", attrs={"name": "twitter:image"}),
            soup.find("meta", attrs={"property": "twitter:image"}),
        ]:
            if meta and meta.get("content"):
                img_u = urllib.parse.urljoin(article_url, meta["content"].strip())
                if _is_clean_url(img_u) and img_u not in found:
                    found.append(img_u)
                    if len(found) >= max_imgs:
                        break
    except Exception:
        pass

    return found


def _search_turkish_news_images(query: str, max_results: int = 8) -> List[str]:
    """
    Bing News Türkiye (`setmkt=tr-TR&setlang=tr`) üzerinden yalnızca Türkiye'deki
    haber sitelerinde yayınlanmış ilgili haberleri bulur ve gerçek haber fotoğraflarını döndürür.
    """
    img_urls: List[str] = []
    encoded_q = urllib.parse.quote(query)
    rss_url = f"https://www.bing.com/news/search?q={encoded_q}&format=rss&setmkt=tr-TR&setlang=tr"

    try:
        resp = requests.get(rss_url, headers=HEADERS, timeout=9)
        if resp.status_code != 200:
            return img_urls
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:8]:
            title_low = (entry.get("title", "") or "").lower()
            if any(b in title_low for b in ("sardis", "ödül", "odul", "yarışma", "tören")):
                continue
            link = entry.get("link", "")
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
            real_article_url = qs.get("url", [link])[0]
            article_imgs = _extract_images_from_turkish_article(real_article_url, max_imgs=1)
            for u in article_imgs:
                if u not in img_urls:
                    img_urls.append(u)
                if len(img_urls) >= max_results:
                    return img_urls
    except Exception:
        pass

    return img_urls


def _search_turkish_web_images(query: str, max_results: int = 12) -> List[str]:
    """
    Yalnızca `.tr` uzantılı Türkiye sitelerinde (`site:tr`) doğrudan görsel araması yapar.
    """
    q_tr = query if "site:" in query.lower() else f"{query} site:tr"
    encoded = urllib.parse.quote(q_tr)
    url = f"https://www.bing.com/images/search?q={encoded}&qft=+filterui:photo-photo&FORM=IRFLTR"
    urls: List[str] = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=7)
        if resp.status_code == 200 and resp.text:
            m_attrs = re.findall(r'\bm="(\{[^"]+\})"', resp.text)
            for m_raw in m_attrs:
                try:
                    data = json.loads(html.unescape(m_raw))
                    murl = data.get("murl", "")
                    if murl and _is_clean_url(murl) and murl not in urls:
                        host = urllib.parse.urlparse(murl.lower()).hostname or ""
                        if host.endswith(".tr") or ".tr." in host:
                            urls.append(murl)
                    if len(urls) >= max_results:
                        break
                except Exception:
                    continue
    except Exception:
        pass

    return urls


def _download_valid_image(
    url: str,
    save_path: Path,
    seen_urls: Set[str],
    seen_hashes: Set[str],
    min_width: int = 500,
    min_height: int = 320,
) -> Optional[Path]:
    """Görseli indirir, boyutunu, gerçek fotoğraf dokusunu ve daha önce hiç kullanılmamış olduğunu doğrulayıp kaydeder."""
    if not _is_clean_url(url) or url in seen_urls:
        return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200 or len(resp.content) < 15000:
            return None

        img = Image.open(io.BytesIO(resp.content))
        w, h = img.size
        if w < min_width or h < min_height:
            return None

        rgb = img.convert("RGB")
        stat = ImageStat.Stat(rgb.resize((120, 120)))
        if (sum(stat.stddev) / 3.0) < 22.0:
            return None

        thumb = img.convert("L").resize((16, 16))
        img_hash = hashlib.md5(thumb.tobytes()).hexdigest()
        if img_hash in seen_hashes:
            return None

        save_path.parent.mkdir(parents=True, exist_ok=True)
        rgb.save(save_path, format="JPEG", quality=92)
        seen_urls.add(url)
        seen_hashes.add(img_hash)
        return save_path
    except Exception:
        return None


def fetch_news_images(
    news_title: str,
    category: dict,
    ai_visual_queries: Optional[List[str]] = None,
    work_dir: Path = Path("work/photos"),
    min_count: int = 1,
    source_link: str = "",
) -> List[Path]:
    """
    Haberin konusuna göre anahtar kelimeleri seçer ve YALNIZCA Türkiye'deki haber/kurum
    kaynaklarından (`source_link`, Bing News Türkiye `setmkt=tr-TR` ve `site:tr`)
    konuyla doğrudan alakalı, daha önce hiçbir haberde kullanılmamış benzersiz kapak fotoğrafını indirir.
    Hem haber sitesi (habermat.com) hem de Reels videosu bu benzersiz kapak görselini kullanır.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    downloaded: List[Path] = []
    seen_urls, seen_hashes = _load_used_image_history()

    # 1. ADIM: Haberin alındığı orijinal Türkiye haber kaynağındaki (`source_link`) gerçek fotoğrafı çek
    if source_link:
        src_imgs = _extract_images_from_turkish_article(source_link, max_imgs=2)
        for u in src_imgs:
            target_file = work_dir / f"real_photo_{len(downloaded):02d}.jpg"
            saved = _download_valid_image(u, target_file, seen_urls, seen_hashes)
            if saved:
                print(f"      [ORİJİNAL HABER FOTOĞRAFI] -> {u[:72]}")
                downloaded.append(saved)
                break

    # 2. ADIM: Haberin konusuna göre çıkarılan anahtar kelimelerle önce Türkiye (.tr) görsellerinden ve Türkiye Haberlerinden ara
    keyword_queries = _extract_topic_keyword_queries(news_title, category)
    for kw_q in keyword_queries:
        if len(downloaded) >= min_count:
            break
        # Önce doğrudan konuyla ilgili Türkiye (.tr) haber/kurum fotoğraflarına bak
        tr_web_imgs = _search_turkish_web_images(kw_q, max_results=10)
        for u in tr_web_imgs:
            if len(downloaded) >= min_count:
                break
            target_file = work_dir / f"real_photo_{len(downloaded):02d}.jpg"
            saved = _download_valid_image(u, target_file, seen_urls, seen_hashes)
            if saved:
                print(f"      [TÜRKİYE (.tr) KAPAK GÖRSELİ] Anahtar Kelime: '{kw_q[:45]}' -> {u[:68]}")
                downloaded.append(saved)
                break

        if len(downloaded) >= min_count:
            break

        # Ardından Bing News Türkiye haber makalelerinin kapak fotoğraflarına bak
        tr_news_imgs = _search_turkish_news_images(kw_q, max_results=8)
        for u in tr_news_imgs:
            if len(downloaded) >= min_count:
                break
            target_file = work_dir / f"real_photo_{len(downloaded):02d}.jpg"
            saved = _download_valid_image(u, target_file, seen_urls, seen_hashes)
            if saved:
                print(f"      [TÜRKİYE HABER KAPAK GÖRSELİ] Anahtar Kelime: '{kw_q[:45]}' -> {u[:68]}")
                downloaded.append(saved)
                break

    _save_used_image_history(seen_urls, seen_hashes)
    return downloaded
