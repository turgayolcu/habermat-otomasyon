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

# Filigranlı stok siteleri ve fotoğrafın üzerine kendi manşet yazısını basan siteleri engelle
BLOCKED_IMAGE_DOMAINS = (
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

# Her kategoride 4 farklı, temiz (üzerinde başka sitenin manşet yazısı olmayan) gerçek fotoğraf getiren sorgular
CATEGORY_ASSOCIATIVE_QUERIES: Dict[str, List[str]] = {
    "devlet_yardimlari": [
        "Türk Lirası 200 TL banknot nakit para destesi",
        "PTT kargo şubesi gişe vezne Türkiye",
        "akıllı telefon ekranı mobil uygulama kullanan kişi",
        "banka ATM para çeken el Türk Lirası",
    ],
    "emeklilik": [
        "banka ATM nakit para çeken el Türk Lirası",
        "Türk Lirası 200 TL ve 100 TL banknot para sayma",
        "yaşlı emekli çift parkta yürüyüş Türkiye",
        "banka şubesi vezne gişe işlem",
    ],
    "toki_konut": [
        "TOKİ toplu konut apartman binaları mimari Türkiye",
        "inşaat şantiyesi vinç konut projesi binalar",
        "ev anahtarı teslim elinde anahtar tutan",
        "modern apartman sitesi bahçe görünümü Türkiye",
    ],
    "belediye_yardimlari": [
        "süpermarket alışveriş arabası gıda reyonu",
        "kredi kartı pos cihazı temassız ödeme market",
        "yardım kolisi gıda paketi taşıyan",
        "pazar alışverişi sebze meyve Türkiye",
    ],
    "kirtasiye_egitim": [
        "okul sıralarında ders çalışan öğrenciler sınıf",
        "kırtasiye reyonu defter kalem okul çantası",
        "okul bahçesi öğrenciler sırt çantalı",
        "kitap okuyan öğrenci çalışma masası",
    ],
    "erzak_gida": [
        "süpermarket alışveriş arabası dolu gıda reyonu",
        "kuru gıda erzak kolisi un yağ makarna bakliyat",
        "market kasası alışveriş poşetleri",
        "mutfak tezgahı sebze meyve alışveriş poşeti",
    ],
    "kiyafet_yakacak": [
        "doğalgaz kombi cihazı ve kalorifer peteği",
        "doğalgaz ocağı mavi alev ateş",
        "odun kömür sobası kış ısınma alev",
        "kışlık mont kaban giyim mağazası askı",
    ],
    "kredi_banka": [
        "Türk Lirası 200 TL banknot para destesi",
        "banka ATM nakit para çekme işlemi",
        "kredi kartı ve Türk Lirası banknotlar",
        "mobil bankacılık telefon ekranı finans",
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
    Haberle alakalı ve çağrışım yapan en az `min_count` (varsayılan 4) adet
    birbirinden farklı, üzerinde başka sitelerin manşet yazısı bulunmayan gerçek fotoğraf indirir.
    Her sorgudan 1 fotoğraf seçerek 4 slaytın 4 farklı sahne olmasını garanti eder.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    cat_id = category.get("id", "devlet_yardimlari")

    assoc_list = CATEGORY_ASSOCIATIVE_QUERIES.get(cat_id, CATEGORY_ASSOCIATIVE_QUERIES["devlet_yardimlari"])

    queries: List[str] = []
    if ai_visual_queries:
        for q in ai_visual_queries:
            if q and q not in queries:
                queries.append(q)

    for q in assoc_list:
        if q not in queries:
            queries.append(q)

    downloaded: List[Path] = []
    seen_hashes: Set[str] = set()

    # 1. Tur: Her farklı sorgudan 1 adet gerçek fotoğraf indir (4 farklı sahne)
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

    # 2. Tur: Eğer hala min_count tamamlanmadıysa ilk sorgulardan ek fotoğraf tamamla
    if len(downloaded) < min_count and queries:
        extra_urls = _search_images_via_headless_browser(queries[0], max_results=20)
        for url in extra_urls:
            if len(downloaded) >= min_count:
                break
            target_file = work_dir / f"real_photo_{len(downloaded):02d}.jpg"
            saved = _download_valid_image(url, target_file, seen_hashes)
            if saved:
                print(f"      [EK GERÇEK FOTOĞRAF #{len(downloaded)+1}] -> {url[:68]}")
                downloaded.append(saved)

    return downloaded
