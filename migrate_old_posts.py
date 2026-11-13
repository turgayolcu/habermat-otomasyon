"""
Habermat.com - Eski Haberleri 3 Altın Kurala Göre Toplu Güncelleme Aracı
1) Kalan 14 Büyükşehir için de kalıcı /<sehir>-buyuksehir-belediyesi-yardim-basvurusu/ Ana Rehberlerini yayınlar (Toplam 30/30 Büyükşehir).
2) Sitedeki tüm eski personel / işçi / İŞKUR ilanlarını tarayıp "Google İş İlanları Kutusu (JobPosting Schema)" alanlarını otomatik doldurur.
3) Eski haberlerdeki yazılı/logolu afiş kapak görsellerini (featured_image*.jpg) 1200x675 WebP tamamen yazısız gerçek haber fotoğraflarıyla değiştirir ve yazı sonlarına ilgili Büyükşehir Ana Rehberi iç bağlantısını ekler.
"""

import argparse
import html
import json
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

from publish_pillar_guides import _build_pillar_package
from src.categories import CATEGORIES
from src.image_search import fetch_news_images
from src.media_generator import generate_wp_featured_image
from src.wp_publisher import WordPressPublisher

MIGRATION_STATE_FILE = BASE_DIR / "data" / "migrated_posts.json"
HISTORY_FILE = BASE_DIR / "data" / "published_history.json"
WORK_DIR = BASE_DIR / "output" / "migrate_work"

REMAINING_14_PILLARS: List[Dict[str, str]] = [
    {
        "city": "Ankara",
        "cat_id": "ankara_belediye",
        "slug": "ankara-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Ankara Başkent Kart (ABB Sosyal Yardım Kartı)",
        "portal": "sosyalhizmetler.ankara.bel.tr, Başkent Mobil ve ALO 153 Mavi Masa",
        "official_domain": "ankara.bel.tr",
        "call_center": "ALO 153 Başkent Mavi Masa",
        "districts": "Çankaya, Keçiören, Yenimahalle, Mamak, Etimesgut, Sincan, Altındağ, Pursaklar, Gölbaşı, Polatlı, Çubuk ve 25 ilçe",
        "special_programs": "Başkent Kart Gıda, Et, Doğalgaz ve Kırtasiye Desteği, Emekli Başkent Kart Pazar ve Nakit Yardımı, Öğrenci Abonman ve Kantin Desteği, Süt ve Bebek Paketi, Su Faturası İndirimi",
        "photo_query": "Ankara Büyükşehir Belediyesi Başkent Kart sosyal yardım",
    },
    {
        "city": "Şanlıurfa",
        "cat_id": "sanliurfa_belediye",
        "slug": "sanliurfa-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Şanlıurfa Büyükşehir Sosyal Yardım Kartı ve Bereket Kart",
        "portal": "sanliurfa.bel.tr Sosyal Hizmetler Başvuru Ekranı ve ALO 153",
        "official_domain": "sanliurfa.bel.tr",
        "call_center": "ALO 153 Şanlıurfa Büyükşehir İletişim Merkezi",
        "districts": "Haliliye, Eyyübiye, Karaköprü, Siverek, Viranşehir, Suruç, Akçakale, Birecik, Ceylanpınar, Harran, Bozova ve 13 ilçe",
        "special_programs": "Sosyal Yardım Kartı ve Gıda Kolisi Desteği, Öğrenci Kırtasiye ve Burs Yardımı, Çölyak Gıda Paketi, Sıcak Yemek (Aşevi) ve Kışlık Yakacak Yardımı",
        "photo_query": "Şanlıurfa Büyükşehir Belediyesi sosyal yardım dağıtımı",
    },
    {
        "city": "Aydın",
        "cat_id": "aydin_belediye",
        "slug": "aydin-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Aydın Büyükşehir Sosyal Destek Kartı ve Halk Ege Et Desteği",
        "portal": "aydin.bel.tr Sosyal Hizmetler Dairesi ve 444 40 09 Hızlı Çözüm Merkezi",
        "official_domain": "aydin.bel.tr",
        "call_center": "ALO 153 / 444 40 09 Aydın Hızlı Çözüm",
        "districts": "Efeler, Nazilli, Söke, Kuşadası, Didim, Çine, İncirliova, Germencik, Bozdoğan, Köşk ve 17 ilçe",
        "special_programs": "Sosyal Destek ve Gıda Kolisi Yardımı, Emekli Kart ve Nakit Desteği, Öğrenci Eğitim-Kırtasiye Yardımı, Anne-Bebek Süt Desteği ve Kışlık Yakacak Yardımı",
        "photo_query": "Aydın Büyükşehir Belediyesi sosyal yardım",
    },
    {
        "city": "Balıkesir",
        "cat_id": "balikesir_belediye",
        "slug": "balikesir-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Balıkesir Yakın Kart (Büyükşehir Sosyal Destek Kartı)",
        "portal": "balikesir.bel.tr Yakın Çözüm Başvuru Ekranı ve 444 40 10",
        "official_domain": "balikesir.bel.tr",
        "call_center": "444 40 10 Yakın Çözüm Çağrı Merkezi",
        "districts": "Karesi, Altıeylül, Bandırma, Edremit, Gönen, Ayvalık, Burhaniye, Bigadiç, Susurluk, Dursunbey ve 20 ilçe",
        "special_programs": "Yakın Kart Aylık Market, Gıda ve Yakacak Bakiyesi, Emekli Pazar ve Fatura Desteği, İlköğretim-Üniversite Eğitim Bursu, Yenidoğan Bebek Paketi ve Kent Lokantası",
        "photo_query": "Balıkesir Büyükşehir Belediyesi Yakın Kart sosyal yardım",
    },
    {
        "city": "Erzurum",
        "cat_id": "erzurum_belediye",
        "slug": "erzurum-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Erzurum Büyükşehir Sosyal Market ve Kışlık Yakacak Destek Kartı",
        "portal": "erzurum.bel.tr Sosyal Hizmetler Dairesi ve ALO 153 Çağrı Merkezi",
        "official_domain": "erzurum.bel.tr",
        "call_center": "ALO 153 Erzurum Büyükşehir Çağrı Merkezi",
        "districts": "Yakutiye, Palandöken, Aziziye, Horasan, Oltu, Pasinler, Karayazı, Hınıs, Tekman, Aşkale ve 20 ilçe",
        "special_programs": "Sosyal Market Gıda ve Giyim Kartı, Kışlık Doğalgaz ve Kömür/Yakacak Desteği, Öğrenci Kırtasiye ve Eğitim Yardımı, Halk Pazarı ve Sıcak Yemek Hizmeti",
        "photo_query": "Erzurum Büyükşehir Belediyesi sosyal yardım",
    },
    {
        "city": "Eskişehir",
        "cat_id": "eskisehir_belediye",
        "slug": "eskisehir-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Eskişehir Büyükşehir Sosyal Destek Kartı ve Aşevi Hizmeti",
        "portal": "eskisehir.bel.tr Sosyal Hizmetler Dairesi Online Başvuru ve ALO 153",
        "official_domain": "eskisehir.bel.tr",
        "call_center": "ALO 153 Eskişehir Büyükşehir İletişim Merkezi",
        "districts": "Odunpazarı, Tepebaşı, Sivrihisar, Çifteler, Seyitgazi, Alpu, Mihalıççık, Mahmudiye, İnönü ve 14 ilçe",
        "special_programs": "Sosyal Destek Kartı ve Gıda Kolisi Yardımı, Halk Süt ve Halk Ekmek Desteği, Emekli Pazar ve Su Faturası Desteği, Kırtasiye Yardımı ve Kent Lokantası",
        "photo_query": "Eskişehir Büyükşehir Belediyesi sosyal yardım",
    },
    {
        "city": "Kahramanmaraş",
        "cat_id": "kahramanmaras_belediye",
        "slug": "kahramanmaras-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Kahramanmaraş Büyükşehir Dermankart (Sosyal Destek Kartı)",
        "portal": "kahramanmaras.bel.tr Dermankart Online Başvuru Ekranı ve ALO 153",
        "official_domain": "kahramanmaras.bel.tr",
        "call_center": "ALO 153 Kahramanmaraş Büyükşehir Çağrı Merkezi",
        "districts": "Onikişubat, Dulkadiroğlu, Elbistan, Afşin, Türkoğlu, Pazarcık, Göksun, Andırın, Çağlayancerit, Nurhak, Ekinözü (11 ilçe)",
        "special_programs": "Dermankart Aylık Gıda ve Alışveriş Limiti, Emekli Pazar ve Su Faturası Desteği, Öğrenci Kırtasiye ve Burs Yardımı, Medikal ve Engelli Destek Hizmetleri",
        "photo_query": "Kahramanmaraş Büyükşehir Belediyesi Dermankart sosyal yardım",
    },
    {
        "city": "Malatya",
        "cat_id": "malatya_belediye",
        "slug": "malatya-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Malatya Büyükşehir Esenlik Sosyal Kart ve Gıda Bankası",
        "portal": "malatya.bel.tr Sağlık ve Sosyal Hizmetler Dairesi ve 444 51 44 Çağrı Merkezi",
        "official_domain": "malatya.bel.tr",
        "call_center": "444 51 44 / ALO 153 Malatya Tek Adımda Çözüm",
        "districts": "Yeşilyurt, Battalgazi, Doğanşehir, Akçadağ, Darende, Hekimhan, Pütürge, Yazıhan, Arapgir ve 13 ilçe",
        "special_programs": "Sosyal Kart Gıda ve Market Alışveriş Desteği, Öğrenci Kırtasiye ve Akademik Eğitim Yardımı, Ekmek ve Sıcak Yemek Desteği, Kışlık Yakacak ve Ev Eşyası Yardımı",
        "photo_query": "Malatya Büyükşehir Belediyesi sosyal yardım",
    },
    {
        "city": "Mardin",
        "cat_id": "mardin_belediye",
        "slug": "mardin-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Mardin Büyükşehir Sosyal Destek Kartı ve Gıda Yardımı",
        "portal": "mardin.bel.tr Sosyal Hizmetler Daire Başkanlığı ve ALO 153",
        "official_domain": "mardin.bel.tr",
        "call_center": "ALO 153 Mardin Büyükşehir İletişim Merkezi",
        "districts": "Artuklu, Kızıltepe, Midyat, Nusaybin, Derik, Mazıdağı, Dargeçit, Savur, Yeşilli, Ömerli (10 ilçe)",
        "special_programs": "Sosyal Destek Kartı ve Erzak Kolisi Yardımı, Üniversite Öğrencilerine Eğitim Bursu, İlköğretim Kırtasiye Seti, Glütensiz Gıda Kolisi ve Yenidoğan Bebek Paketi",
        "photo_query": "Mardin Büyükşehir Belediyesi sosyal yardım",
    },
    {
        "city": "Muğla",
        "cat_id": "mugla_belediye",
        "slug": "mugla-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Muğla Büyükşehir Halk Kart (Sosyal Yardım Kartı)",
        "portal": "mugla.bel.tr Halk Kart Başvuru Ekranı ve 444 48 01 Çağrı Merkezi",
        "official_domain": "mugla.bel.tr",
        "call_center": "444 48 01 Muğla Büyükşehir Çağrı Merkezi",
        "districts": "Menteşe, Bodrum, Fethiye, Milas, Marmaris, Seydikemer, Ortaca, Yatağan, Dalaman, Köyceğiz, Datça, Ula, Kavaklıdere (13 ilçe)",
        "special_programs": "Muğla Halk Kart Aylık Market ve Gıda Desteği, Emekli Nakit ve Fatura Yardımı, Öğrenci Kırtasiye, Beslenme ve Ulaşım Desteği, Halk Süt ve Kışlık Yakacak Yardımı",
        "photo_query": "Muğla Büyükşehir Belediyesi Halk Kart sosyal yardım",
    },
    {
        "city": "Ordu",
        "cat_id": "ordu_belediye",
        "slug": "ordu-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Ordu Büyükşehir Sosyal Market ve Yardım Kartı",
        "portal": "ordu.bel.tr Online Sosyal Yardım Başvuru Ekranı ve ALO 153",
        "official_domain": "ordu.bel.tr",
        "call_center": "ALO 153 / 444 10 52 Ordu Büyükşehir Çağrı Merkezi",
        "districts": "Altınordu, Ünye, Fatsa, Perşembe, Kumru, Korgan, Gölköy, Ulubey, Mesudiye, Akkuş, Aybastı ve 19 ilçe",
        "special_programs": "Sosyal Market Gıda ve Giyim Kartı, Doğalgaz ve Kömür/Yakacak Desteği, Günlük Sıcak Yemek Hizmeti, Öğrenci Kırtasiye Desteği ve Hoş Geldin Bebek Paketi",
        "photo_query": "Ordu Büyükşehir Belediyesi Sosyal Market yardım",
    },
    {
        "city": "Sakarya",
        "cat_id": "sakarya_belediye",
        "slug": "sakarya-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Sakarya Büyükşehir Kart54 Sosyal Destek ve Gıda Bankası",
        "portal": "sakarya.bel.tr Sosyal Hizmetler Dairesi Başvuru Ekranı ve ALO 153 Çözüm Masası",
        "official_domain": "sakarya.bel.tr",
        "call_center": "ALO 153 Sakarya Çözüm Masası",
        "districts": "Adapazarı, Serdivan, Erenler, Akyazı, Hendek, Karasu, Geyve, Arifiye, Sapanca, Pamukova, Ferizli, Kaynarca ve 16 ilçe",
        "special_programs": "Kart54 Sosyal Destek ve Gıda Bankası Alışveriş Yardımı, Emekli Su ve Doğalgaz Fatura Desteği, Kampüs Öğrenci ve Kırtasiye Yardımı, Yaşlı ve Engelli Evde Bakım Hizmeti",
        "photo_query": "Sakarya Büyükşehir Belediyesi sosyal yardım",
    },
    {
        "city": "Trabzon",
        "cat_id": "trabzon_belediye",
        "slug": "trabzon-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Trabzon Büyükşehir Sosyal Destek Kartı",
        "portal": "trabzon.bel.tr Sosyal Hizmetler Başvuru Ekranı ve ALO 153 TİKOM",
        "official_domain": "trabzon.bel.tr",
        "call_center": "ALO 153 TİKOM (Trabzon İletişim ve Koordinasyon Merkezi)",
        "districts": "Ortahisar, Akçaabat, Araklı, Of, Yomra, Arsin, Vakfıkebir, Sürmene, Maçka, Beşikdüzü, Çarşıbaşı ve 18 ilçe",
        "special_programs": "Sosyal Destek Kartı Gıda ve Market Bakiyesi, Öğrenci Eğitim ve Kırtasiye Desteği, Kışlık Yakacak ve Doğalgaz Yardımı, Emekli Destek Paketi ve Sıcak Yemek Hizmeti",
        "photo_query": "Trabzon Büyükşehir Belediyesi sosyal yardım",
    },
    {
        "city": "Van",
        "cat_id": "van_belediye",
        "slug": "van-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Van Büyükşehir Sosyal Destek Kartı ve Halk Market",
        "portal": "van.bel.tr Sosyal Hizmetler Daire Başkanlığı ve ALO 153",
        "official_domain": "van.bel.tr",
        "call_center": "ALO 153 Van Büyükşehir İletişim Merkezi",
        "districts": "İpekyolu, Tuşba, Edremit, Erciş, Özalp, Çaldıran, Başkale, Muradiye, Gürpınar, Gevaş, Çatak, Bahçesaray, Saray (13 ilçe)",
        "special_programs": "Sosyal Destek Kartı ve Gıda Kolisi Desteği, Kışlık Yakacak Desteği, Öğrenci Kırtasiye ve Eğitim Yardımı, Glütensiz Gıda Paketi ve Engelli/Yaşlı Destek Hizmetleri",
        "photo_query": "Van Büyükşehir Belediyesi sosyal yardım",
    },
]

CITY_TO_SLUG = {
    "Adana": "adana", "Ankara": "ankara", "Antalya": "antalya", "Aydın": "aydin",
    "Balıkesir": "balikesir", "Bursa": "bursa", "Denizli": "denizli", "Diyarbakır": "diyarbakir",
    "Erzurum": "erzurum", "Eskişehir": "eskisehir", "Gaziantep": "gaziantep", "Hatay": "hatay",
    "İstanbul": "istanbul", "İzmir": "izmir", "Kahramanmaraş": "kahramanmaras", "Kayseri": "kayseri",
    "Kocaeli": "kocaeli", "Konya": "konya", "Malatya": "malatya", "Manisa": "manisa",
    "Mardin": "mardin", "Mersin": "mersin", "Muğla": "mugla", "Ordu": "ordu",
    "Sakarya": "sakarya", "Samsun": "samsun", "Şanlıurfa": "sanliurfa", "Tekirdağ": "tekirdag",
    "Trabzon": "trabzon", "Van": "van",
}


def _load_migrated_state() -> Dict[str, List[int]]:
    if MIGRATION_STATE_FILE.exists():
        try:
            return json.loads(MIGRATION_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"cover_updated_ids": [], "job_updated_ids": []}


def _save_migrated_state(cover_ids: Set[int], job_ids: Set[int]) -> None:
    MIGRATION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    MIGRATION_STATE_FILE.write_text(
        json.dumps(
            {
                "cover_updated_ids": sorted(cover_ids),
                "job_updated_ids": sorted(job_ids),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _detect_city_and_cat(title: str) -> tuple[Optional[str], dict]:
    title_l = title.lower()
    cat_map = {c["id"]: c for c in CATEGORIES}
    for city_name, c_slug in CITY_TO_SLUG.items():
        if re.search(rf"\b{re.escape(city_name.lower())}", title_l) or re.search(rf"\b{re.escape(c_slug)}", title_l):
            return city_name, cat_map.get(f"{c_slug}_belediye", CATEGORIES[0])
    return None, {"id": "iskur_kamu", "name": "Sosyal Yardım & Kamu Rehberi", "wp_slug": "sosyal-yardim"}


def _upgrade_article_html(raw_html: str, city_name: Optional[str]) -> Optional[str]:
    """Eski sosyal medya ('Google'a habermat.com yaz') kutusunu temiz SEO iç bağlantı kutusuyla değiştirir."""
    if not raw_html:
        return None

    if city_name and city_name in CITY_TO_SLUG:
        c_slug = CITY_TO_SLUG[city_name]
        pillar_url = f"https://www.habermat.com/{c_slug}-buyuksehir-belediyesi-yardim-basvurusu/"
        new_box = (
            '\n<div style="background:#F8FAFC;color:#0F172A;padding:18px 22px;'
            'border:1px solid #CBD5E1;border-left:6px solid #EA580C;border-radius:8px;margin-top:28px;margin-bottom:18px;">'
            '<p style="margin:0;font-size:15px;line-height:1.6;">'
            f'📌 <strong>İlginizi Çekebilir ({city_name} Ana Rehber):</strong> İlinizdeki tüm sosyal kart, nakdi destek, erzak ve başvuru ekranları için '
            f'<a href="{pillar_url}"><strong>{city_name} Büyükşehir Belediyesi Yardım Başvurusu ve Sosyal Kart Rehberi</strong></a> '
            'sayfamızı inceleyebilir veya <a href="https://www.habermat.com/devlet-ve-belediye-yardimi-sorgulama-robotu/"><strong>2026 Yardım Hak Sahipliği Sorgulama Robotu</strong></a> ile uygunluğunuzu hesaplayabilirsiniz.'
            '</p></div>'
        )
    else:
        new_box = (
            '\n<div style="background:#F8FAFC;color:#0F172A;padding:18px 22px;'
            'border:1px solid #CBD5E1;border-left:6px solid #EA580C;border-radius:8px;margin-top:28px;margin-bottom:18px;">'
            '<p style="margin:0;font-size:15px;line-height:1.6;">'
            '📌 <strong>Ücretsiz Hak Sahipliği Hesaplama:</strong> Hane geliriniz ve kişi sayınıza göre alabileceğiniz tüm Bakanlık ve Büyükşehir desteklerini '
            '<a href="https://www.habermat.com/devlet-ve-belediye-yardimi-sorgulama-robotu/"><strong>2026 Devlet ve Belediye Yardımı Sorgulama Robotu</strong></a> '
            'üzerinden hemen sorgulayabilirsiniz.'
            '</p></div>'
        )

    # Eski lacivert/kırmızı 'Google'a habermat.com yaz' kutusunu bul ve değiştir
    pattern = r'<div[^>]*#0B132B[^>]*>.*?habermat\.com.*?</div>'
    if re.search(pattern, raw_html, flags=re.IGNORECASE | re.DOTALL):
        return re.sub(pattern, new_box, raw_html, flags=re.IGNORECASE | re.DOTALL)

    if city_name and city_name in CITY_TO_SLUG:
        pillar_slug = f"{CITY_TO_SLUG[city_name]}-buyuksehir-belediyesi-yardim-basvurusu"
        if pillar_slug not in raw_html:
            return raw_html.rstrip() + "\n" + new_box
    return None


def publish_remaining_14_pillars(wp: WordPressPublisher) -> None:
    headers = wp._ensure_session_or_auth()
    cat_map = {c["id"]: c for c in CATEGORIES}
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    for info in REMAINING_14_PILLARS:
        city = info["city"]
        slug = info["slug"]
        cat = cat_map.get(info["cat_id"], CATEGORIES[0])

        check = wp.session.get(f"{wp.api_base}/posts", params={"slug": slug}, headers=headers, timeout=20)
        if check.status_code == 200 and check.json():
            print(f"[ANA REHBER MEVCUT] {city} -> {check.json()[0].get('link')}")
            continue

        package = _build_pillar_package(info, cat)
        pdir = WORK_DIR / slug
        photos = fetch_news_images(news_title=info["photo_query"], category=cat, work_dir=pdir, min_count=1)
        webp_path = WORK_DIR / f"{slug}.webp"
        generate_wp_featured_image(package, cat, webp_path, real_photos=photos)
        res = wp.publish_article(package, cat, webp_path)
        print(f"[ANA REHBER YAYINLANDI] {city} -> {res.get('link')}")


def fetch_all_posts_lightweight(wp: WordPressPublisher) -> List[Dict[str, Any]]:
    headers = wp._ensure_session_or_auth()
    all_posts: List[Dict[str, Any]] = []
    page = 1
    while True:
        resp = None
        for attempt in range(3):
            try:
                resp = wp.session.get(
                    f"{wp.api_base}/posts",
                    params={
                        "per_page": 50,
                        "page": page,
                        "_fields": "id,date,slug,title,featured_media,link",
                    },
                    headers=headers,
                    timeout=25,
                )
                if resp.status_code == 200:
                    break
            except Exception as exc:
                print(f"[BİLGİ] Sayfa {page} okunurken tekrar deneniyor ({attempt+1}/3): {exc}")
                time.sleep(3)
        if not resp or resp.status_code != 200 or not resp.json():
            break
        batch = resp.json()
        all_posts.extend(batch)
        total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1
    return all_posts


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Eski haberleri 3 Altın Kurala göre toplu güncelle")
    parser.add_argument("--max-covers", type=int, default=500, help="Bu çalışmada güncellenecek maksimum kapak görseli sayısı")
    parser.add_argument("--pillars-and-jobs-only", action="store_true", help="Sadece 30 Büyükşehir Ana Rehberlerini ve JobPosting Schema kutularını tamamla")
    args = parser.parse_args()

    wp = WordPressPublisher()
    headers = wp._ensure_session_or_auth()

    print("=== ADIM 1: Kalan 14 Büyükşehir Ana Rehberi Tamamlanıyor (Toplam 30/30 Büyükşehir) ===")
    publish_remaining_14_pillars(wp)

    print("\n=== ADIM 2: Sitedeki Tüm Haberler Taranıyor ===")
    all_posts = fetch_all_posts_lightweight(wp)
    print(f"[BİLGİ] Toplam {len(all_posts)} yayınlanmış yazı bulundu.")

    state = _load_migrated_state()
    cover_done: Set[int] = set(state.get("cover_updated_ids", []))
    job_done: Set[int] = set(state.get("job_updated_ids", []))

    # History'den URL -> source_url haritası çıkar
    url_to_source: Dict[str, str] = {}
    if HISTORY_FILE.exists():
        try:
            hdata = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            for it in hdata.get("items", []):
                wurl = (it.get("wp_url") or "").strip().rstrip("/")
                surl = (it.get("source_url") or "").strip()
                if wurl:
                    url_to_source[wurl] = surl
        except Exception:
            pass

    # ADIM 2B: Tüm eski personel / işçi / İŞKUR ilanlarına JobPosting Schema uygula
    job_keywords_extra = (
        "personel", "işçi alımı", "memur alımı", "işkur", "iş ilanı",
        "zabıta", "itfaiye", "şoför alımı", "güvenlik görevlisi",
        "typ ", "iüp ", "işgücü uyum", "kpss", "alacak", "istihdam",
    )
    job_updated_now = 0
    for p in all_posts:
        pid = int(p["id"])
        if pid in job_done:
            continue
        raw_title = html.unescape(p.get("title", {}).get("rendered", ""))
        tl = raw_title.lower()
        is_job = any(k in tl for k in job_keywords_extra) and any(
            w in tl for w in ("alım", "ilan", "personel", "işçi", "memur", "işkur", "istihdam", "başvuru")
        )
        # Tarım/fidan/yardım haberlerini yanlışlıkla iş ilanı saymamak için net filtre
        if any(neg in tl for neg in ("yardım", "koli", "kırtasiye", "fidan", "gübre", "burs", "kart", "süt", "bebek")) and not any(
            pos in tl for pos in ("personel", "işçi", "memur", "işkur", "zabıta", "itfaiye")
        ):
            is_job = False

        if is_job:
            city_name, cat = _detect_city_and_cat(raw_title)
            wp._maybe_populate_job_posting_box(
                pid,
                {"seo_title": raw_title, "is_job_posting": True, "job_city": city_name or ""},
                cat,
            )
            job_done.add(pid)
            job_updated_now += 1
            if job_updated_now % 10 == 0:
                _save_migrated_state(cover_done, job_done)

    _save_migrated_state(cover_done, job_done)
    print(f"[TAMAMLANDI] Toplam {len(job_done)} iş/personel ilanında JobPosting Schema aktif (Bu çalışmada +{job_updated_now}).")

    if args.pillars_and_jobs_only:
        return

    # ADIM 3: Eski afiş kapaklı haberleri (Ekim-Kasım 2026 bot haberleri) 1200x675 WebP yazısız gerçek fotoğraflarla + Ana Rehber iç linkiyle güncelle
    print("\n=== ADIM 3: Eski Yazılı/Logolu Kapak Görselleri 1200x675 WebP Yazısız Gerçek Fotoğraflarla Güncelleniyor ===")
    updated_covers_now = 0

    for p in all_posts:
        if updated_covers_now >= args.max_covers:
            break
        pid = int(p["id"])
        slug = p.get("slug", "")
        if pid in cover_done or slug.endswith("-buyuksehir-belediyesi-yardim-basvurusu"):
            continue

        # Bot tarafından Ekim-Kasım 2026'da girilen yazılı afiş kapaklı haberler (date >= 2026-10-15)
        p_date = p.get("date", "")
        p_link = (p.get("link") or "").strip().rstrip("/")
        if p_date < "2026-10-15" and p_link not in url_to_source:
            continue

        old_media_id = p.get("featured_media") or 0
        # Mevcut medya zaten .webp ise sadece iç link kontrolü yap, görseli tekrar indirme
        already_webp = False
        if old_media_id:
            try:
                mr = wp.session.get(f"{wp.api_base}/media/{old_media_id}", params={"_fields": "id,mime_type,source_url"}, headers=headers, timeout=15)
                if mr.status_code == 200:
                    mjson = mr.json()
                    if mjson.get("mime_type") == "image/webp":
                        already_webp = True
            except Exception:
                pass

        raw_title = html.unescape(p.get("title", {}).get("rendered", ""))
        city_name, cat = _detect_city_and_cat(raw_title)

        try:
            new_media_id = old_media_id
            if not already_webp:
                src_link = url_to_source.get(p_link, "")
                clean_search_title = re.sub(r"\s*Başvuru Şartları ve Formu 2026\s*$", "", raw_title, flags=re.IGNORECASE).strip()
                pdir = WORK_DIR / f"post_{pid}"
                photos = fetch_news_images(
                    news_title=clean_search_title,
                    category=cat,
                    work_dir=pdir,
                    min_count=1,
                    source_link=src_link,
                )
                webp_path = WORK_DIR / f"{slug[:60]}-{pid}.webp"
                generate_wp_featured_image({"seo_title": raw_title}, cat, webp_path, real_photos=photos)
                media_info = wp.upload_media(webp_path, alt_text=raw_title, title=raw_title)
                new_media_id = media_info["id"]
                if pdir.exists():
                    shutil.rmtree(pdir, ignore_errors=True)
                if webp_path.exists():
                    webp_path.unlink(missing_ok=True)

            # İçeriği çekip eski 'Google'a habermat.com yaz' kutusunu Büyükşehir Ana Rehberi iç linkiyle değiştir
            update_payload: Dict[str, Any] = {}
            if new_media_id and new_media_id != old_media_id:
                update_payload["featured_media"] = new_media_id

            pr = wp.session.get(f"{wp.api_base}/posts/{pid}", params={"context": "edit", "_fields": "content"}, headers=headers, timeout=20)
            if pr.status_code == 200:
                raw_content = pr.json().get("content", {}).get("raw", "")
                upgraded_html = _upgrade_article_html(raw_content, city_name)
                if upgraded_html:
                    update_payload["content"] = upgraded_html

            if update_payload:
                up_resp = wp.session.post(f"{wp.api_base}/posts/{pid}", json=update_payload, headers=headers, timeout=25)
                up_resp.raise_for_status()

            # Eski yazılı afiş görselini (.jpg) medya kütüphanesinden temizle
            if old_media_id and new_media_id != old_media_id:
                wp.delete_media(int(old_media_id))

            cover_done.add(pid)
            updated_covers_now += 1
            print(f"[{updated_covers_now}] Güncellendi ID={pid} | {raw_title[:62]} -> WebP media={new_media_id}")
            if updated_covers_now % 5 == 0:
                _save_migrated_state(cover_done, job_done)
        except Exception as exc:
            print(f"[UYARI] ID={pid} güncellenirken hata (sonraki çalışmada tekrar denenecek): {exc}")

    _save_migrated_state(cover_done, job_done)
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR, ignore_errors=True)
    print(f"\n=== GÜNCELLEME ÖZETİ: Bu çalışmada {updated_covers_now} eski haber yenilendi (Toplam tamamlanan: {len(cover_done)}) ===")


if __name__ == "__main__":
    main()
