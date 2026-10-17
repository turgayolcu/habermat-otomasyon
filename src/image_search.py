"""
Habermat.com - Gerçek Haber ve Çağrışım Görselleri Arama Motoru
Chrome/Edge Headless tarayıcı üzerinden gerçek zamanlı görsel araması yaparak:
- WordPress Kapak Görseli (1200x675) için 1 adet üzerinde yazı olmayan gerçek haber/konu fotoğrafı
- Instagram Reels Videosu (1080x1920) için en az 4 adet birbirinden farklı sahneye sahip gerçek fotoğraf
indirir ve doğrular.
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

import requests
from PIL import Image

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

# Filigranlı stok siteleri, yabancı stok siteleri (Pexels/Unsplash) ve fotoğrafın üzerine kendi manşet yazısını basan siteleri engelle
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
    "biblicallifelessons",
    "wallpaperaccess",
    "craiggoodwinphoto",
    "devletodemeleri.com",
    "kamugundemi.com",
    "emlak365.com",
    "sikayetvar.com",
    "tavsanlihaber.com",
    "sabirgazetesi",
)

# Sorun yaşandığında veya ek sahne gerektiğinde her zaman gerçek Türk Parası (200 TL / 100 TL) kullanan garantili sorgular
TURKISH_LIRA_FALLBACK_QUERIES: List[str] = [
    "200 TL Türk Lirası banknot para destesi",
    "Türk Lirası 200 TL ve 100 TL nakit para",
    "200 Türk Lirası banknot yakın çekim",
    "banka ATM 200 TL Türk Lirası para çekme",
]

# Her kategoride alakasız stok görsel çıkmasını önleyen, doğrudan konu veya Türk Lirası odaklı gerçek fotoğraf sorguları
CATEGORY_ASSOCIATIVE_QUERIES: Dict[str, List[str]] = {
    "devlet_yardimlari": [
        "200 TL Türk Lirası banknot nakit para destesi",
        "PTT şubesi gişe vezne Türkiye",
        "Türk Lirası 200 TL ve 100 TL banknot para",
        "banka ATM 200 TL Türk Lirası para çeken el",
    ],
    "emeklilik": [
        "200 TL Türk Lirası banknot para sayma",
        "banka ATM nakit para çeken el Türk Lirası",
        "Türk Lirası 200 TL ve 100 TL banknot destesi",
        "Ziraat Bankası Halkbank Vakıfbank ATM Türk Lirası",
    ],
    "toki_konut": [
        "TOKİ toplu konut apartman binaları Türkiye",
        "TOKİ sosyal konut projesi binalar",
        "200 TL Türk Lirası banknot para destesi",
        "Türk Lirası 200 TL ve 100 TL nakit para",
    ],
    "belediye_yardimlari": [
        "200 TL Türk Lirası banknot nakit para destesi",
        "Türk Lirası 200 TL ve 100 TL banknot para",
        "banka ATM 200 TL Türk Lirası para çekme",
        "PTT şubesi vezne Türkiye",
    ],
    "kirtasiye_egitim": [
        "200 TL Türk Lirası banknot nakit para destesi",
        "okul sıralarında ders çalışan öğrenciler Türkiye",
        "Türk Lirası 200 TL ve 100 TL banknot para",
        "banka ATM 200 TL Türk Lirası para çekme",
    ],
    "erzak_gida": [
        "gıda yardım kolisi erzak paketi Türkiye",
        "200 TL Türk Lirası banknot nakit para destesi",
        "süpermarket alışveriş arabası gıda reyonu Türkiye",
        "Türk Lirası 200 TL ve 100 TL banknot para",
    ],
    "kiyafet_yakacak": [
        "200 TL Türk Lirası banknot nakit para destesi",
        "doğalgaz kombi ve kalorifer peteği",
        "Türk Lirası 200 TL ve 100 TL banknot para",
        "PTT şubesi gişe vezne Türkiye",
    ],
    "kredi_banka": [
        "200 TL Türk Lirası banknot para destesi",
        "Türk Lirası 200 TL ve 100 TL nakit para",
        "banka ATM 200 TL Türk Lirası para çekme işlemi",
        "200 Türk Lirası banknot para sayma",
    ],
}


def _find_headless_browser() -> Optional[str]:
    """Windows ve Linux (GitHub Actions) üzerinde kurulu Chrome veya Edge tarayıcısını bulur."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("chromium-browser"),
        shutil.which("chromium"),
        shutil.which("microsoft-edge"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def _is_clean_url(url: str) -> bool:
    low = url.lower()
    if any(bad in low for bad in BLOCKED_IMAGE_DOMAINS):
        return False
    if any(ext in low for ext in [".svg", ".gif", "logo", "icon", "avatar", "sprite"]):
        return False
    return True


def _search_images_via_headless_browser(query: str, max_results: int = 15) -> List[str]:
    """
    Gerçek Chrome/Edge Headless tarayıcısı ile görsel araması yaparak
    tam çözünürlüklü, temiz gerçek fotoğrafları çeker.
    """
    browser = _find_headless_browser()
    if not browser:
        return []

    encoded = urllib.parse.quote(query)
    url = f"https://www.bing.com/images/search?q={encoded}&qft=+filterui:photo-photo&FORM=IRFLTR"

    try:
        res = subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--virtual-time-budget=3200",
                f"--user-agent={HEADERS['User-Agent']}",
                "--dump-dom",
                url,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=14,
        )
        dom = res.stdout
        m_attrs = re.findall(r'\bm="(\{[^"]+\})"', dom)
        urls: List[str] = []
        for m_raw in m_attrs:
            try:
                data = json.loads(html.unescape(m_raw))
                murl = data.get("murl", "")
                if murl and _is_clean_url(murl) and murl not in urls:
                    urls.append(murl)
                if len(urls) >= max_results:
                    break
            except Exception:
                continue
        return urls
    except Exception as exc:
        print(f"[UYARI] Headless tarayıcı görsel arama zaman aşımı ({query[:30]}): {exc}")
        return []


def _download_valid_image(
    url: str,
    save_path: Path,
    seen_hashes: Set[str],
    min_width: int = 500,
    min_height: int = 340,
) -> Optional[Path]:
    """Görseli indirir, boyutunu ve benzersizliğini doğrulayıp RGB JPEG olarak kaydeder."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200 or len(resp.content) < 16000:
            return None

        img = Image.open(io.BytesIO(resp.content))
        w, h = img.size
        if w < min_width or h < min_height:
            return None

        thumb = img.convert("L").resize((16, 16))
        img_hash = hashlib.md5(thumb.tobytes()).hexdigest()
        if img_hash in seen_hashes:
            return None

        rgb_img = img.convert("RGB")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        rgb_img.save(save_path, format="JPEG", quality=92)
        seen_hashes.add(img_hash)
        return save_path
    except Exception:
        return None


def fetch_news_images(
    news_title: str,
    category: dict,
    ai_visual_queries: Optional[List[str]],
    work_dir: Path,
    min_count: int = 4,
) -> List[Path]:
    """
    Haberle doğrudan alakalı fotoğrafları indirir; eğer alakasız sorgu üretilirse veya
    herhangi bir sahnede görsel bulunamazsa doğrudan gerçek Türk Lirası (200 TL / 100 TL)
    banknot fotoğraflarını kullanır.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    cat_id = category.get("id", "devlet_yardimlari")

    assoc_list = CATEGORY_ASSOCIATIVE_QUERIES.get(cat_id, CATEGORY_ASSOCIATIVE_QUERIES["devlet_yardimlari"])

    # Alakasız stok fotoğraf getirebilen jenerik kelimeleri engelle
    vague_terms = ("telefon", "ekran", "mobil", "insan", "aile", "çift", "park", "yürüyüş", "mutlu", "evde", "masa")

    queries: List[str] = []
    if news_title and len(news_title.strip()) > 12:
        queries.append(f"{news_title.strip()[:55]} Türkiye")

    if ai_visual_queries:
        for q in ai_visual_queries:
            q_clean = (q or "").strip()
            if q_clean and not any(vt in q_clean.lower() for vt in vague_terms):
                if "türkiye" not in q_clean.lower() and "tl" not in q_clean.lower() and "lira" not in q_clean.lower():
                    q_clean = f"{q_clean} Türkiye"
                if q_clean not in queries:
                    queries.append(q_clean)

    for q in assoc_list:
        if q not in queries:
            queries.append(q)

    for q in TURKISH_LIRA_FALLBACK_QUERIES:
        if q not in queries:
            queries.append(q)

    downloaded: List[Path] = []
    seen_hashes: Set[str] = set()

    # 1. Tur: Her farklı sorgudan 1 adet gerçek fotoğraf indir
    for q in queries:
        if len(downloaded) >= min_count:
            break

        candidate_urls = _search_images_via_headless_browser(q, max_results=14)
        for url in candidate_urls:
            target_file = work_dir / f"real_photo_{len(downloaded):02d}.jpg"
            saved = _download_valid_image(url, target_file, seen_hashes)
            if saved:
                print(f"      [GERÇEK FOTOĞRAF #{len(downloaded)+1}] Sahne: '{q[:42]}' -> {url[:68]}")
                downloaded.append(saved)
                break

    # 2. Tur: Eksik kalırsa doğrudan gerçek Türk Parası (200 TL / 100 TL banknot) fotoğraflarıyla tamamla
    if len(downloaded) < min_count:
        for tl_q in TURKISH_LIRA_FALLBACK_QUERIES:
            if len(downloaded) >= min_count:
                break
            extra_urls = _search_images_via_headless_browser(tl_q, max_results=20)
            for url in extra_urls:
                if len(downloaded) >= min_count:
                    break
                target_file = work_dir / f"real_photo_{len(downloaded):02d}.jpg"
                saved = _download_valid_image(url, target_file, seen_hashes)
                if saved:
                    print(f"      [TÜRK PARASI YEDEK FOTOĞRAF #{len(downloaded)+1}] -> {url[:68]}")
                    downloaded.append(saved)

    return downloaded
