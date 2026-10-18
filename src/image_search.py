"""
Habermat.com - Türkiye İçi Konu ve Anahtar Kelime Odaklı Haber Görseli Motoru
- "Türk Parası" kuralı tamamen kaldırılmıştır.
- Haberin başlığından ve konusundan anahtar kelimeleri çıkarır.
- Yalnızca Türkiye sınırları içerisindeki (`setmkt=tr-TR&setlang=tr` ve `site:tr`) gerçek haber kaynaklarından
  (`source_link` makalesi, Türkiye haber ajansları ve Türkiye siteleri) konuyla birebir örtüşen
  en az 4 farklı gerçek haber fotoğrafı indirir.
"""

import hashlib
import html
import io
import json
import os
import re
import shutil
import subprocess
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
        "Ankara Büyükşehir Belediyesi Başkent Kart yardım",
        "Çankaya Keçiören Yenimahalle Belediyesi sosyal yardım",
        "Mamak Sincan Etimesgut Altındağ Belediyesi destek",
        "Ankara belediye sosyal yardım paketi",
    ],
    "antalya_belediye": [
        "Antalya Büyükşehir Belediyesi sosyal yardım",
        "Kepez Muratpaşa Konyaaltı Belediyesi sosyal destek",
        "Alanya Manavgat Serik Belediyesi yardım",
        "Antalya belediye gıda eğitim desteği",
    ],
}


def _is_clean_url(url: str) -> bool:
    """Yasaklı yabancı/stok siteleri ve ikon/logo uzantılarını reddeder."""
    if not url or not url.startswith("http"):
        return False
    low = url.lower()
    if any(bad in low for bad in BLOCKED_IMAGE_DOMAINS):
        return False
    if any(ext in low for ext in [".svg", ".gif", "logo", "icon", "avatar", "sprite", "periodic", "1x1", "pixel"]):
        return False
    return True


def _extract_topic_keyword_queries(news_title: str, category: dict) -> List[str]:
    """
    Haberin başlığından anahtar kelimeleri seçerek Türkiye haber kaynaklarında
    aranacak 3-4 farklı konu sorgusu üretir.
    """
    cat_id = category.get("id", "devlet_yardimlari")
    cat_name = category.get("name", "")
    queries: List[str] = []

    if news_title:
        # 1. Tam haber başlığı (kaynak adı temizlenmiş)
        clean_full = re.split(r"\s+[-|]\s+", news_title)[0].strip()
        if len(clean_full) > 10:
            queries.append(clean_full[:70])

        # 2. Rakam ve noktalama işaretlerinden arındırılmış saf konu anahtar kelimeleri
        no_nums = re.sub(r"\b\d+[\d.,]*\b", " ", clean_full)
        no_nums = re.sub(r"\b(TL|lira|bin|milyon|milyar|kaç|nasıl|nedir|ne zaman|kimler)\b", " ", no_nums, flags=re.IGNORECASE)
        no_nums = re.sub(r"[^\w\sğüşıöçĞÜŞİÖÇ]", " ", no_nums)
        words = [w for w in no_nums.split() if len(w) >= 3]

        if len(words) >= 2:
            kw_short = " ".join(words[:4])
            if kw_short not in queries:
                queries.append(kw_short)
        if len(words) >= 4:
            kw_mid = " ".join(words[1:5])
            if kw_mid not in queries:
                queries.append(kw_mid)

    # 3. Kategoriye ait Türkiye içi konu sorguları
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
    Yan sütundaki 'Önerilen Haberler' küçük resimlerini asla almaz.
    """
    found: List[str] = []
    if not article_url or not article_url.startswith("http"):
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
            link = entry.get("link", "")
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
            real_article_url = qs.get("url", [link])[0]
            article_imgs = _extract_images_from_turkish_article(real_article_url, max_imgs=2)
            for u in article_imgs:
                if u not in img_urls:
                    img_urls.append(u)
                if len(img_urls) >= max_results:
                    return img_urls
    except Exception:
        pass

    return img_urls


def _search_turkish_web_images(query: str, max_results: int = 10) -> List[str]:
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
    seen_hashes: Set[str],
    min_width: int = 500,
    min_height: int = 320,
) -> Optional[Path]:
    """Görseli indirir, boyutunu, gerçek fotoğraf dokusunu ve benzersizliğini doğrulayıp kaydeder."""
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
        seen_hashes.add(img_hash)
        return save_path
    except Exception:
        return None


def fetch_news_images(
    news_title: str,
    category: dict,
    ai_visual_queries: Optional[List[str]] = None,
    work_dir: Path = Path("work/photos"),
    min_count: int = 4,
    source_link: str = "",
) -> List[Path]:
    """
    Haberin konusuna göre anahtar kelimeleri seçer ve YALNIZCA Türkiye'deki haber/kurum
    kaynaklarından (`source_link`, Bing News Türkiye `setmkt=tr-TR` ve `site:tr`)
    konuyla doğrudan alakalı gerçek fotoğrafları indirir.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    downloaded: List[Path] = []
    seen_hashes: Set[str] = set()

    # 1. ADIM: Haberin alındığı orijinal Türkiye haber kaynağındaki (`source_link`) gerçek fotoğrafı çek
    if source_link:
        src_imgs = _extract_images_from_turkish_article(source_link, max_imgs=2)
        for u in src_imgs:
            target_file = work_dir / f"real_photo_{len(downloaded):02d}.jpg"
            saved = _download_valid_image(u, target_file, seen_hashes)
            if saved:
                print(f"      [ORİJİNAL HABER FOTOĞRAFI #{len(downloaded)+1}] -> {u[:72]}")
                downloaded.append(saved)
                break

    # 2. ADIM: Haberin konusuna göre çıkarılan anahtar kelimelerle Türkiye Haber Kaynaklarından (`setmkt=tr-TR`) fotoğraf çek
    keyword_queries = _extract_topic_keyword_queries(news_title, category)
    for kw_q in keyword_queries:
        if len(downloaded) >= min_count:
            break
        tr_news_imgs = _search_turkish_news_images(kw_q, max_results=8)
        for u in tr_news_imgs:
            if len(downloaded) >= min_count:
                break
            target_file = work_dir / f"real_photo_{len(downloaded):02d}.jpg"
            saved = _download_valid_image(u, target_file, seen_hashes)
            if saved:
                print(f"      [TÜRKİYE HABER GÖRSELİ #{len(downloaded)+1}] Anahtar Kelime: '{kw_q[:40]}' -> {u[:68]}")
                downloaded.append(saved)

    # 3. ADIM: Hala eksik slayt varsa kategori konu sorgularıyla `.tr` uzantılı Türkiye sitelerinden (`site:tr`) tamamla
    if len(downloaded) < min_count:
        cat_queries = CATEGORY_TOPIC_QUERIES.get(category.get("id", "devlet_yardimlari"), [])
        for kw_q in cat_queries:
            if len(downloaded) >= min_count:
                break
            tr_web_imgs = _search_turkish_web_images(kw_q, max_results=10)
            for u in tr_web_imgs:
                if len(downloaded) >= min_count:
                    break
                target_file = work_dir / f"real_photo_{len(downloaded):02d}.jpg"
                saved = _download_valid_image(u, target_file, seen_hashes)
                if saved:
                    print(f"      [TÜRKİYE (.tr) GÖRSELİ #{len(downloaded)+1}] Anahtar Kelime: '{kw_q[:40]}' -> {u[:68]}")
                    downloaded.append(saved)

    return downloaded
