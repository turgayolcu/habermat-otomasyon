"""
Habermat.com - Gerçek Haber ve Türk Lirası Görsel Motoru
- Yabancı alan adlarını (.com ABD/İngiltere siteleri: pcmag, periodic table, gannett vb.) %100 engeller.
- Doğrulanmış yerel Gerçek Türk Lirası (200 TL / 100 TL banknot) fotoğraflarını (`assets/turkish_lira/`)
  ve yalnızca güvenilir Türkiye (.tr) kaynaklı gerçek fotoğrafları kullanır.
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
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

import requests
from PIL import Image

TR_TZ = timezone(timedelta(hours=3))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_TL_DIR = PROJECT_ROOT / "assets" / "turkish_lira"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

# Yalnızca Türkiye (.tr) uzantılı veya resmi Türk kurum/haber CDN'lerinden görsel kabul et
# Böylece GitHub Actions (ABD sunucusu) üzerinden Bing araması yapıldığında pcmag (Amazon Prime),
# periodic.png (Periyodik Tablo) veya gannett (Prens Harry) gibi yabancı görseller ASLA giremez.
ALLOWED_TURKISH_DOMAINS = (
    ".gov.tr",
    ".bel.tr",
    ".edu.tr",
    ".org.tr",
    ".com.tr",
    ".net.tr",
    "aa.com.tr",
    "trthaber.com",
    "tcmb.gov.tr",
    "toki.gov.tr",
    "aile.gov.tr",
    "ziraatbank.com.tr",
    "halkbank.com.tr",
    "vakifbank.com.tr",
    "ptt.gov.tr",
)

# Fotoğrafın üzerine devasa manşet yazısı/logo basan veya stok filigranlı siteleri engelle
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
    "devletodemeleri.com",
    "kamugundemi.com",
    "emlak365.com",
    "sikayetvar.com",
    "tavsanlihaber.com",
    "sabirgazetesi",
)

TURKISH_LIRA_FALLBACK_QUERIES: List[str] = [
    "200 TL Türk Lirası banknot site:tr",
    "Türk Lirası 200 TL 100 TL kağıt para site:tr",
    "200 Türk Lirası destesi nakit para site:tr",
    "ATM para çekme Türk Lirası 200 TL site:tr",
]

CATEGORY_ASSOCIATIVE_QUERIES: Dict[str, List[str]] = {
    "devlet_yardimlari": [
        "200 TL Türk Lirası banknot site:tr",
        "Türk Lirası 200 TL ve 100 TL nakit para site:tr",
        "PTT şubesi gişe vezne site:tr",
        "ATM 200 TL Türk Lirası para çekme site:tr",
    ],
    "emeklilik": [
        "200 TL Türk Lirası banknot para sayma site:tr",
        "ATM nakit para çekme Türk Lirası site:tr",
        "Türk Lirası 200 TL ve 100 TL banknot destesi site:tr",
        "Ziraat Bankası ATM Türk Lirası site:tr",
    ],
    "toki_konut": [
        "TOKİ toplu konut binaları site:tr",
        "TOKİ sosyal konut şantiye binalar site:tr",
        "200 TL Türk Lirası banknot site:tr",
        "Türk Lirası 200 TL ve 100 TL nakit para site:tr",
    ],
    "belediye_yardimlari": [
        "200 TL Türk Lirası banknot site:tr",
        "Türk Lirası 200 TL ve 100 TL nakit para site:tr",
        "ATM 200 TL Türk Lirası para çekme site:tr",
        "PTT şubesi vezne site:tr",
    ],
    "kirtasiye_egitim": [
        "200 TL Türk Lirası banknot site:tr",
        "Türk Lirası 200 TL ve 100 TL nakit para site:tr",
        "okul sınıf sıralar öğrenciler site:tr",
        "ATM 200 TL Türk Lirası para çekme site:tr",
    ],
    "erzak_gida": [
        "200 TL Türk Lirası banknot site:tr",
        "gıda yardım kolisi erzak paketi site:tr",
        "Türk Lirası 200 TL ve 100 TL nakit para site:tr",
        "süpermarket gıda reyonu site:tr",
    ],
    "kiyafet_yakacak": [
        "200 TL Türk Lirası banknot site:tr",
        "doğalgaz kombi kalorifer peteği site:tr",
        "Türk Lirası 200 TL ve 100 TL nakit para site:tr",
        "PTT şubesi gişe site:tr",
    ],
    "kredi_banka": [
        "200 TL Türk Lirası banknot site:tr",
        "Türk Lirası 200 TL ve 100 TL nakit para site:tr",
        "ATM 200 TL Türk Lirası para çekme site:tr",
        "200 Türk Lirası banknot para sayma site:tr",
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
    """
    Yalnızca Türkiye (.tr) uzantılı alan adlarından gelen ve yasaklı listede olmayan
    gerçek fotoğraf URL'lerini kabul eder. Yabancı (.com / .info / .tv) siteleri reddeder.
    """
    low = url.lower()
    if any(bad in low for bad in BLOCKED_IMAGE_DOMAINS):
        return False
    if any(ext in low for ext in [".svg", ".gif", "logo", "icon", "avatar", "sprite", "periodic"]):
        return False
    try:
        host = urllib.parse.urlparse(low).hostname or ""
    except Exception:
        return False
    if not any(host.endswith(dom) or dom in host for dom in ALLOWED_TURKISH_DOMAINS):
        return False
    return True


def _search_images_via_headless_browser(query: str, max_results: int = 15) -> List[str]:
    """
    Gerçek Chrome/Edge Headless tarayıcısı ile Türkiye pazarında (setmkt=tr-TR)
    görsel araması yaparak yalnızca doğrulanmış Türkiye (.tr) fotoğraflarını çeker.
    """
    browser = _find_headless_browser()
    if not browser:
        return []

    encoded = urllib.parse.quote(query)
    url = (
        f"https://www.bing.com/images/search?q={encoded}"
        f"&qft=+filterui:photo-photo&setmkt=tr-TR&setlang=tr&cc=TR&FORM=IRFLTR"
    )

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


def _load_verified_local_turkish_lira_photos(
    work_dir: Path,
    seen_hashes: Set[str],
    start_index: int,
    needed: int,
    seed_text: str = "",
) -> List[Path]:
    """
    Depo içindeki `assets/turkish_lira/` klasöründe bulunan, bizzat doğrulanmış
    gerçek 200 TL ve 100 TL Türk Parası fotoğraflarını sırayla seçip çalışma klasörüne kopyalar.
    """
    results: List[Path] = []
    if not LOCAL_TL_DIR.exists():
        return results

    local_files = sorted(LOCAL_TL_DIR.glob("tl_*.jpg"))
    if not local_files:
        return results

    now_tr = datetime.now(TR_TZ)
    seed_val = sum(ord(c) for c in (seed_text or "")) + now_tr.day * 24 + now_tr.hour
    offset = seed_val % len(local_files)
    rotated = local_files[offset:] + local_files[:offset]

    for lf in rotated:
        if len(results) >= needed:
            break
        try:
            img = Image.open(lf)
            thumb = img.convert("L").resize((16, 16))
            img_hash = hashlib.md5(thumb.tobytes()).hexdigest()
            if img_hash in seen_hashes:
                continue
            target_file = work_dir / f"real_photo_{start_index + len(results):02d}.jpg"
            rgb_img = img.convert("RGB")
            target_file.parent.mkdir(parents=True, exist_ok=True)
            rgb_img.save(target_file, format="JPEG", quality=92)
            seen_hashes.add(img_hash)
            results.append(target_file)
            print(f"      [DOĞRULANMIŞ TÜRK PARASI FOTOĞRAFI #{start_index + len(results)}] -> {lf.name}")
        except Exception:
            continue

    return results


def fetch_news_images(
    news_title: str,
    category: dict,
    ai_visual_queries: Optional[List[str]],
    work_dir: Path,
    min_count: int = 4,
) -> List[Path]:
    """
    1. Kapak fotoğrafı (#1) ve ana sahneler için doğrudan doğrulanmış gerçek Türk Lirası
       (200 TL / 100 TL banknot) fotoğraflarını (`assets/turkish_lira/`) ve yalnızca `.tr`
       uzantılı güvenilir Türkiye görsellerini kullanır.
    2. Yabancı sitelerden (pcmag, periodic table, gannett vb.) alakasız görsel gelmesini %100 engeller.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    cat_id = category.get("id", "devlet_yardimlari")
    downloaded: List[Path] = []
    seen_hashes: Set[str] = set()

    # 1. ÖNCE KAPAK GÖRSELİ (FOTOĞRAF #1) İÇİN DOĞRUDAN DOĞRULANMIŞ GERÇEK TÜRK PARASI (200 TL / 100 TL) KULLAN
    # (Yalnızca TOKİ konut kategorisinde önce .tr uzantılı gerçek TOKİ konut fotoğrafı aranır, bulunamazsa yine Türk Parası kullanılır)
    if cat_id == "toki_konut":
        toki_urls = _search_images_via_headless_browser("TOKİ toplu konut binaları site:tr", max_results=12)
        for url in toki_urls:
            target_file = work_dir / f"real_photo_{len(downloaded):02d}.jpg"
            saved = _download_valid_image(url, target_file, seen_hashes)
            if saved:
                print(f"      [GERÇEK TOKİ FOTOĞRAFI #1] -> {url[:68]}")
                downloaded.append(saved)
                break

    # Kapak görseli ve ana sahneleri doğrulanmış yerel Türk Parası (200 TL / 100 TL) havuzundan doldur
    local_tl_photos = _load_verified_local_turkish_lira_photos(
        work_dir=work_dir,
        seen_hashes=seen_hashes,
        start_index=len(downloaded),
        needed=min_count - len(downloaded),
        seed_text=news_title,
    )
    downloaded.extend(local_tl_photos)

    # Eğer hala eksik kalırsa yalnızca .tr uzantılı Türk Lirası sorgularıyla tamamla
    if len(downloaded) < min_count:
        for tl_q in TURKISH_LIRA_FALLBACK_QUERIES:
            if len(downloaded) >= min_count:
                break
            extra_urls = _search_images_via_headless_browser(tl_q, max_results=15)
            for url in extra_urls:
                if len(downloaded) >= min_count:
                    break
                target_file = work_dir / f"real_photo_{len(downloaded):02d}.jpg"
                saved = _download_valid_image(url, target_file, seen_hashes)
                if saved:
                    print(f"      [TÜRK PARASI EK FOTOĞRAF #{len(downloaded)+1}] -> {url[:68]}")
                    downloaded.append(saved)

    return downloaded
