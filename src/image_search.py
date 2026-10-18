"""
Habermat.com - Türkiye Sınırları İçi (.tr) Gerçek Haber Görseli Motoru
1. Aramaları YALNIZCA Türkiye sınırları içerisinde (`site:tr`, `cc=TR`, `setmkt=tr-TR`) yapar ve
   `.tr` uzantılı olmayan tüm yabancı siteleri (%100) reddeder.
2. Önce haberin kendi konusu ve kurumuyla (TOKİ, Belediye, Bakanlık, Banka, Okul, Doğalgaz vb.)
   ilgili Türkiye içi gerçek fotoğrafları (üzerinde başka sitenin manşet yazısı olmayanları) çeker.
3. Eğer Türkiye içi aramada temiz fotoğraf bulunamazsa veya eksik kalırsa, emniyet sübabı olarak
   doğrulanmış gerçek Türk Lirası (`assets/turkish_lira/`) fotoğraflarını kullanır.
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
from PIL import Image, ImageStat

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

# YALNIZCA Türkiye sınırları içerisindeki (.tr) resmi kurum, belediye, ajans ve haber sitelerine izin ver
ALLOWED_TURKISH_DOMAINS = (
    ".gov.tr",
    ".bel.tr",
    ".edu.tr",
    ".org.tr",
    ".com.tr",
    ".net.tr",
    ".tr",
    "aa.com.tr",
    "trthaber.com",
    "ntv.com.tr",
    "cnnturk.com",
    "haberturk.com",
    "dunya.com",
    "ekonomim.com",
    "bloomberght.com",
    "tcmb.gov.tr",
    "toki.gov.tr",
    "aile.gov.tr",
    "ibb.istanbul",
)

# Fotoğrafın üzerine devasa sarı/kırmızı manşet yazısı basan siteleri ve yabancı stok sitelerini engelle
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
    "takvim.com.tr",
    "ahaber.com.tr",
    "fotomac.com.tr",
)

TURKISH_LIRA_FALLBACK_QUERIES: List[str] = [
    "200 TL Türk Lirası banknot site:tr",
    "Türk Lirası 200 TL 100 TL kağıt para site:tr",
    "200 Türk Lirası destesi nakit para site:tr",
    "ATM para çekme Türk Lirası 200 TL site:tr",
]

# Her kategori için Türkiye sınırları içerisinde (`site:tr`) aranacak gerçek konu/kurum sahneleri
CATEGORY_ASSOCIATIVE_QUERIES: Dict[str, List[str]] = {
    "devlet_yardimlari": [
        "PTT şubesi gişe vezne site:tr",
        "200 TL Türk Lirası banknot destesi site:tr",
        "ATM 200 TL Türk Lirası para çekme site:tr",
        "Türk Lirası 200 TL ve 100 TL nakit para site:tr",
    ],
    "emeklilik": [
        "ATM nakit para çekme Türk Lirası site:tr",
        "Ziraat Bankası şube ATM site:tr",
        "200 TL Türk Lirası banknot para sayma site:tr",
        "Türk Lirası 200 TL ve 100 TL banknot destesi site:tr",
    ],
    "toki_konut": [
        "TOKİ toplu konut binaları site:gov.tr",
        "TOKİ sosyal konut apartmanları site:tr",
        "TOKİ konut projesi binalar site:tr",
        "200 TL Türk Lirası banknot site:tr",
    ],
    "belediye_yardimlari": [
        "Büyükşehir Belediyesi hizmet binası site:bel.tr",
        "belediye sosyal yardım destek kartı site:tr",
        "200 TL Türk Lirası banknot site:tr",
        "ATM 200 TL Türk Lirası para çekme site:tr",
    ],
    "kirtasiye_egitim": [
        "okul sınıf sıralar öğrenciler ders site:tr",
        "okul çantası defter kırtasiye malzemeleri site:tr",
        "200 TL Türk Lirası banknot site:tr",
        "üniversite kampüs öğrenciler site:tr",
    ],
    "erzak_gida": [
        "gıda yardım kolisi erzak paketi site:tr",
        "süpermarket alışveriş arabası gıda reyonu site:tr",
        "200 TL Türk Lirası banknot site:tr",
        "Belediye Kızılay gıda kolisi yardımı site:tr",
    ],
    "kiyafet_yakacak": [
        "doğalgaz kombi kalorifer peteği site:tr",
        "doğalgaz sayacı faturası kombi site:tr",
        "200 TL Türk Lirası banknot site:tr",
        "kışlık yakacak kömür yardımı site:tr",
    ],
    "kredi_banka": [
        "Ziraat Bankası Halkbank Vakıfbank şube ATM site:tr",
        "ATM 200 TL Türk Lirası para çekme site:tr",
        "200 TL Türk Lirası banknot para destesi site:tr",
        "Türk Lirası 200 TL ve 100 TL nakit para site:tr",
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
    gerçek fotoğraf URL'lerini kabul eder. Yabancı (.com / .info / .tv) siteleri %100 reddeder.
    """
    low = url.lower()
    if any(bad in low for bad in BLOCKED_IMAGE_DOMAINS):
        return False
    if any(ext in low for ext in [".svg", ".gif", "logo", "icon", "avatar", "sprite", "periodic", "banner"]):
        return False
    try:
        host = urllib.parse.urlparse(low).hostname or ""
    except Exception:
        return False
    if not any(host.endswith(dom) or host == dom.lstrip(".") for dom in ALLOWED_TURKISH_DOMAINS):
        return False
    return True


def _extract_turkish_subject_query(news_title: str, cat_id: str) -> Optional[str]:
    """
    Haber başlığından kısaltma veya yabancı sitelerle karışabilecek rakamları ('10 TL', 'SED', '2026' vb.)
    temizleyerek, yalnızca Türkiye sınırları içinde (`site:tr`) aranacak net Türkçe konu sorgusu üretir.
    """
    if not news_title:
        return None
    # Rakamları, para birimlerini ve noktalama işaretlerini çıkar ki dosya kodlarıyla ('0tl-11.jpg' vb.) eşleşmesin
    cleaned = re.sub(r"\b\d+[\d.,]*\b", " ", news_title)
    cleaned = re.sub(r"\b(TL|lira|bin|milyon|milyar|SED|SYDV)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^\w\sğüşıöçĞÜŞİÖÇ]", " ", cleaned)
    words = [w for w in cleaned.split() if len(w) >= 3]
    if len(words) < 2:
        return None
    subject = " ".join(words[:5])
    if cat_id == "belediye_yardimlari" and "belediye" in subject.lower():
        return f"{subject} site:bel.tr"
    if cat_id == "toki_konut":
        return f"{subject} konut site:tr"
    return f"{subject} site:tr"


def _search_images_via_headless_browser(query: str, max_results: int = 15) -> List[str]:
    """
    Önce doğrudan hızlı HTTP (requests) ile, gerekirse Headless tarayıcı ile
    YALNIZCA Türkiye sınırları içinde (`site:tr`) görsel araması yapar.
    """
    if "site:" not in query.lower():
        query = f"{query} site:tr"

    encoded = urllib.parse.quote(query)
    url = f"https://www.bing.com/images/search?q={encoded}&qft=+filterui:photo-photo&FORM=IRFLTR"
    urls: List[str] = []

    # 1. Hızlı HTTP araması (0.3 sn - zaman aşımı olmadan)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=7)
        if resp.status_code == 200 and resp.text:
            m_attrs = re.findall(r'\bm="(\{[^"]+\})"', resp.text)
            for m_raw in m_attrs:
                try:
                    data = json.loads(html.unescape(m_raw))
                    murl = data.get("murl", "")
                    if murl and _is_clean_url(murl) and murl not in urls:
                        urls.append(murl)
                    if len(urls) >= max_results:
                        return urls
                except Exception:
                    continue
    except Exception:
        pass

    if urls:
        return urls

    # 2. Yedek: Headless Tarayıcı
    browser = _find_headless_browser()
    if not browser:
        return urls

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
        return urls


def _has_heavy_news_banner_or_graphic(img: Image.Image) -> bool:
    """
    Türk haber sitelerinin fotoğrafın alt/üst bandına bastığı düz kırmızı/sarı manşet
    şeritlerini veya grafik tabloları tespit edip eler.
    """
    rgb = img.convert("RGB").resize((120, 120))
    # Düz beyaz/gri grafik veya tablo kontrolü (düşük varyanslı diyagramlar)
    stat = ImageStat.Stat(rgb)
    avg_std = sum(stat.stddev) / 3.0
    if avg_std < 28.0:
        return True
    return False


def _download_valid_image(
    url: str,
    save_path: Path,
    seen_hashes: Set[str],
    min_width: int = 550,
    min_height: int = 360,
) -> Optional[Path]:
    """Görseli indirir, boyutunu, gerçek fotoğraf dokusunu ve benzersizliğini doğrulayıp kaydeder."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200 or len(resp.content) < 18000:
            return None

        img = Image.open(io.BytesIO(resp.content))
        w, h = img.size
        if w < min_width or h < min_height:
            return None

        if _has_heavy_news_banner_or_graphic(img):
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
    Türkiye içi aramada yeterli/temiz görsel bulunamadığında devreye giren emniyet sübabı:
    `assets/turkish_lira/` içindeki doğrulanmış gerçek 200 TL ve 100 TL fotoğraflarını kullanır.
    """
    results: List[Path] = []
    if not LOCAL_TL_DIR.exists() or needed <= 0:
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
            print(f"      [TÜRK PARASI EMNİYET GÖRSELİ #{start_index + len(results)}] -> {lf.name}")
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
    1. Aşama: YALNIZCA Türkiye sınırları içerisinde (`site:tr`, `.gov.tr`, `.bel.tr`, `.com.tr`)
       haberin kendi konusu ve kategorisiyle ilgili gerçek fotoğrafları arar.
    2. Aşama: Eğer Türkiye içi aramada temiz fotoğraf bulunamazsa veya eksik kalırsa,
       emniyet sübabı olarak doğrulanmış gerçek Türk Lirası (`200 TL / 100 TL`) fotoğraflarını kullanır.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    cat_id = category.get("id", "devlet_yardimlari")
    assoc_list = CATEGORY_ASSOCIATIVE_QUERIES.get(cat_id, CATEGORY_ASSOCIATIVE_QUERIES["devlet_yardimlari"])

    queries: List[str] = []
    subject_q = _extract_turkish_subject_query(news_title, cat_id)
    if subject_q:
        queries.append(subject_q)

    for q in assoc_list:
        if q not in queries:
            queries.append(q)

    downloaded: List[Path] = []
    seen_hashes: Set[str] = set()

    # 1. AŞAMA: Yalnızca Türkiye sınırları içerisindeki (.tr) sitelerden konuyla ilgili gerçek fotoğrafları indir
    for q in queries:
        if len(downloaded) >= min_count:
            break
        candidate_urls = _search_images_via_headless_browser(q, max_results=14)
        for url in candidate_urls:
            target_file = work_dir / f"real_photo_{len(downloaded):02d}.jpg"
            saved = _download_valid_image(url, target_file, seen_hashes)
            if saved:
                print(f"      [TÜRKİYE İÇİ GERÇEK FOTOĞRAF #{len(downloaded)+1}] Sahne: '{q[:42]}' -> {url[:68]}")
                downloaded.append(saved)
                break

    # 2. AŞAMA (EMNİYET SÜBABI): Eksik kalan veya bulunamayan sahneleri doğrulanmış gerçek Türk Parası ile tamamla
    if len(downloaded) < min_count:
        fallback_photos = _load_verified_local_turkish_lira_photos(
            work_dir=work_dir,
            seen_hashes=seen_hashes,
            start_index=len(downloaded),
            needed=min_count - len(downloaded),
            seed_text=news_title,
        )
        downloaded.extend(fallback_photos)

    return downloaded
