"""
Habermat.com - Saatlik Otomatik WordPress SEO Haber + Instagram Reels Üretim ve Paylaşım Botu
Çalışma Saatleri: Her gün 07:00 - 24:00 (00:00) arası her saat başı (Toplam 18 Haber + 18 Reels/gün)
"""

import argparse
import json
import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

from src.ai_writer import (
    MANDATORY_CTA_DISPLAY,
    MANDATORY_CTA_SPOKEN,
    generate_news_and_reels_package,
    slugify_tr,
)
from src.categories import get_category_for_current_hour
from src.ig_publisher import InstagramReelsPublisher
from src.image_search import fetch_news_images
from src.media_generator import generate_reels_video, generate_wp_featured_image
from src.news_fetcher import fetch_fresh_news_for_category, save_to_history
from src.tiktok_publisher import TikTokPublisher
from src.wp_publisher import WordPressPublisher

TR_TZ = timezone(timedelta(hours=3))
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
WORK_DIR = BASE_DIR / "output" / "temp_work"


def _build_demo_package(news_item: dict, category: dict) -> dict:
    """GEMINI_API_KEY olmadan yerel test (--dry-run) yapıldığında örnek paket üretir."""
    raw_title = news_item.get("raw_title") or "e-Devlet'ten Yeni Destek Ödemesi Başladı! Kimler Başvurabilir?"
    seo_title = raw_title if len(raw_title) <= 72 else "e-Devlet'ten Yeni Destek Ödemesi Başladı! Kimler Başvurabilir?"
    spot = (
        f"{category['name']} kapsamında dar gelirli hanelere ve vatandaşlara yönelik "
        "yeni destek ödemesi başvuruları e-Devlet kapısı üzerinden erişime açıldı."
    )
    html_content = f"""
<p class="habermat-spot"><strong>{spot}</strong></p>
<h2>Yeni Sosyal Destek Ödemesi Detayları ve Kapsamı</h2>
<p>Vatandaşların ekonomik olarak desteklenmesi amacıyla hayata geçirilen yeni sosyal yardım paketi kapsamında, şartları sağlayan hanelere PTT ve banka hesapları üzerinden düzenli destek ödemesi gerçekleştirilecek.</p>
<h2>Başvuru Şartları Nelerdir? Kimler Faydalanabilir?</h2>
<ul>
  <li>Türkiye Cumhuriyeti vatandaşı olmak ve başvuru sahibi hanede ikamet etmek,</li>
  <li>Hane içinde kişi başına düşen aylık gelirin belirlenen sınırın altında olması,</li>
  <li>Sosyal Yardımlaşma ve Dayanışma Vakfı (SYDV) kriterlerini taşımak.</li>
</ul>
<h2>e-Devlet Sosyal Yardım Başvurusu Nasıl Yapılır?</h2>
<p>Başvurular T.C. kimlik numarası ve şifresi ile doğrudan e-Devlet Kapısı üzerinden <strong>Sosyal Yardım Başvuru Hizmeti</strong> ekranından ücretsiz olarak yapılabilmektedir.</p>
<div style="background:#0B132B;color:#FFFFFF;padding:18px 22px;border-left:6px solid #D90429;border-radius:8px;margin-top:24px;">
<p style="margin:0;font-size:16px;line-height:1.5;">📢 <strong>Önemli Hatırlatma:</strong> Başvuru şartları ve detayları için Google'a <strong>habermat.com</strong> yaz, çıkan ilk siteye tıklayın!</p>
</div>
"""
    script_segments = [
        {
            "spoken": "e-Devlet üzerinden yeni destek ödemesi başladı! Peki kimler başvurabilir, şartlar neler?",
            "subtitle": "e-Devlet üzerinden yeni destek ödemesi başladı! Peki kimler başvurabilir, şartlar neler?",
            "is_cta": False,
        },
        {
            "spoken": "Bakanlık tarafından dar gelirli ailelere yönelik başlatılan yeni nakdi destek paketinde başvurular e-Devlet ekranından açıldı.",
            "subtitle": "Bakanlık tarafından dar gelirli ailelere yönelik başlatılan yeni nakdi destek paketinde başvurular e-Devlet ekranından açıldı.",
            "is_cta": False,
        },
        {
            "spoken": "Onaylanan ödemeler hak sahiplerinin doğrudan PTT kartlarına veya banka hesaplarına yatırılıyor.",
            "subtitle": "Onaylanan ödemeler hak sahiplerinin doğrudan PTT kartlarına veya banka hesaplarına yatırılıyor.",
            "is_cta": False,
        },
        {
            "spoken": MANDATORY_CTA_SPOKEN,
            "subtitle": MANDATORY_CTA_DISPLAY,
            "is_cta": True,
        },
    ]

    return {
        "seo_title": seo_title,
        "slug": slugify_tr(seo_title),
        "meta_description": spot[:155],
        "spot": spot,
        "wp_html_content": html_content,
        "tags": [category["name"], "e-Devlet", "Sosyal Yardım", "Destek Ödemesi"],
        "reels_headline": "E-DEVLET'TEN YENİ DESTEK ÖDEMESİ BAŞLADI!",
        "reels_badge": category.get("badge", "SON DAKİKA • DEVLET YARDIMI"),
        "script_segments": script_segments,
        "visual_queries": [],
        "instagram_caption": (
            f"🚨 E-DEVLET'TEN YENİ DESTEK ÖDEMESİ BAŞLADI!\n\n"
            f"{spot}\n\n"
            f"👉 Başvuru şartları ve detayları için Google'a \"habermat.com\" yaz, çıkan ilk siteye tıklayın!\n\n"
            f"#devletyardımı #sosyalyardım #edevlet #emekli #toki #habermat"
        ),
    }


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()

    parser = argparse.ArgumentParser(description="Habermat.com WordPress + Instagram Reels Otomasyonu")
    parser.add_argument("--category", type=str, default=None, help="Belirli bir kategori ID ile çalıştır (örn: emeklilik, toki_konut)")
    parser.add_argument("--dry-run", action="store_true", help="WordPress ve Instagram'a yüklemeden sadece görsel, makale ve Reels videosunu üret")
    parser.add_argument("--skip-wp", action="store_true", help="WordPress yayınlamasını atla")
    parser.add_argument("--skip-ig", action="store_true", help="Instagram Reels yayınlamasını atla")
    args = parser.parse_args()

    now_tr = datetime.now(TR_TZ)
    print("============================================================")
    print(f"[HABERMAT BOT] Çalışma Zamanı (TR): {now_tr.strftime('%d.%m.%Y %H:%M:%S')}")

    # 1. Saatin kategorisini belirle
    category = get_category_for_current_hour(args.category or os.environ.get("FORCE_CATEGORY"))
    print(f"[1/6] Seçilen Kategori: {category['name']} ({category['id']})")

    # 2. Güncel haberi çek
    news_item = fetch_fresh_news_for_category(category)
    print(f"[2/6] Bulunan Haber Konusu: {news_item['raw_title']}")
    print(f"      -> Orijinal Kaynak Linki: {news_item.get('source_link', 'Rehber/Arşiv')}")

    # 3. Gemini AI ile WordPress SEO Makalesi + Reels Senaryosu üret
    if args.dry_run and not os.environ.get("GEMINI_API_KEY"):
        print("[3/6] GEMINI_API_KEY bulunamadı, --dry-run demo paketi kullanılıyor...")
        package = _build_demo_package(news_item, category)
    else:
        print("[3/6] Gemini AI ile SEO makalesi ve Reels senaryosu üretiliyor...")
        package = generate_news_and_reels_package(news_item, category)

    print(f"      -> SEO Başlık : {package['seo_title']}")
    print(f"      -> Reels Manşet: {package['reels_headline']}")

    # Çıktı klasörünü hazırla
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR, ignore_errors=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    # 4. Google ve Türk haber kaynaklarından gerçek fotoğrafları indir (Kapak + en az 3-4 Reels slayt fotoğrafı)
    print("[4/6] Google Görseller'den haberle alakalı gerçek fotoğraflar indiriliyor...")
    real_photos = fetch_news_images(
        news_title=news_item["raw_title"],
        category=category,
        ai_visual_queries=package.get("visual_queries"),
        work_dir=WORK_DIR / "photos",
        min_count=4,
    )
    print(f"      -> Toplam {len(real_photos)} adet gerçek haber/çağrışım fotoğrafı hazırlandı.")

    featured_img_path = OUTPUT_DIR / "featured_image.jpg"
    reels_mp4_path = OUTPUT_DIR / "reels_video.mp4"
    article_json_path = OUTPUT_DIR / "latest_package.json"

    with open(article_json_path, "w", encoding="utf-8") as f:
        json.dump(package, f, ensure_ascii=False, indent=2)

    # 5. Gerçek Fotoğraflı Kapak Görseli ve Çoklu Slaytlı Reels Videosu Üretimi
    print("[5/6] Gerçek fotoğraflı WordPress kapak görseli (1200x675) ve kadın spikerli Reels videosu (1080x1920) hazırlanıyor...")
    generate_wp_featured_image(package, category, featured_img_path, real_photos=real_photos)
    generate_reels_video(package, category, WORK_DIR, reels_mp4_path, real_photos=real_photos)
    print(f"      -> Kapak Görseli Hazır: {featured_img_path}")
    print(f"      -> Reels Videosu Hazır: {reels_mp4_path}")

    if args.dry_run:
        print("[TAMAMLANDI] --dry-run modu aktif olduğu için yayınlama adımı atlandı.")
        return

    # 6. WordPress ve TikTok (veya Instagram) Yayınlama
    wp_pub = WordPressPublisher()
    tiktok_pub = TikTokPublisher()
    ig_pub = InstagramReelsPublisher()

    wp_post_url = ""
    social_id = ""

    if not args.skip_wp and wp_pub.is_configured():
        print("[6A/6] WordPress (habermat.com) üzerine haber yayınlanıyor...")
        wp_res = wp_pub.publish_article(package, category, featured_img_path)
        wp_post_url = wp_res.get("link", "")
        print(f"       -> WordPress Yayınlandı: {wp_post_url}")

    if not args.skip_ig:
        if tiktok_pub.is_configured():
            print("[6B/6] TikTok hesabına video yükleniyor ve paylaşılıyor...")
            tt_res = tiktok_pub.publish_tiktok(reels_mp4_path, package["instagram_caption"])
            social_id = tt_res.get("status", "tiktok_ok")
            print("       -> TikTok Videosu Yayınlandı!")
        elif ig_pub.is_configured():
            print("[6B/6] Instagram Reels videosu yayınlanıyor...")
            ig_res = ig_pub.publish_reels(reels_mp4_path, package["instagram_caption"], wp_publisher=wp_pub)
            social_id = ig_res.get("media_id", "")
            print(f"       -> Instagram Reels Yayınlandı! Media ID: {social_id}")
        else:
            print("[UYARI] TikTok oturumu (python login_tiktok.py) veya Instagram şifresi henüz tanımlanmadı.")

    # Geçmişe kaydet (Aynı haber tekrar yazılmasın ve kaynak linki saklansın)
    save_to_history(
        title=news_item["raw_title"],
        category_id=category["id"],
        wp_url=wp_post_url,
        ig_id=social_id,
        source_url=news_item.get("source_link", ""),
    )
    # Depolama alanı dolmaması için geçici slayt ve ses parçalarını temizle
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR, ignore_errors=True)

    print("============================================================")
    print("[BAŞARILI] Saatlik Habermat.com haber ve video akışı tamamlandı!")


if __name__ == "__main__":
    main()
