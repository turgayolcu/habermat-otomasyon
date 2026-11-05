"""
Habermat.com - Saatlik Otomatik WordPress SEO Haber Üretim ve Yayınlama Botu
Çalışma Saatleri: Her gün 07:00 - 24:00 (00:00) arası her saat başı (Toplam 18 Haber/gün - Sadece habermat.com)
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
from src.image_search import fetch_news_images
from src.media_generator import generate_wp_featured_image
from src.news_fetcher import fetch_fresh_news_for_category, save_to_history
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
        "reels_headline": seo_title,
        "reels_badge": category.get("badge", "SON DAKİKA • DEVLET YARDIMI"),
        "script_segments": script_segments,
        "visual_queries": [],
        "instagram_caption": "",
    }


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()

    parser = argparse.ArgumentParser(description="Habermat.com Saatlik WordPress SEO Haber Otomasyonu")
    parser.add_argument("--category", type=str, default=None, help="Belirli bir kategori ID ile çalıştır (örn: emeklilik, toki_konut)")
    parser.add_argument("--dry-run", action="store_true", help="WordPress'e yüklemeden sadece kapak görseli ve makaleyi üret")
    parser.add_argument("--skip-wp", action="store_true", help="WordPress yayınlamasını atla")
    args = parser.parse_args()

    now_tr = datetime.now(TR_TZ)
    print("============================================================")
    print(f"[HABERMAT BOT] Çalışma Zamanı (TR): {now_tr.strftime('%d.%m.%Y %H:%M:%S')}")

    forced_cat = (args.category or os.environ.get("FORCE_CATEGORY") or "").strip()
    if not forced_cat and not args.dry_run:
        if 1 <= now_tr.hour < 7:
            print("[BİLGİ] Gece 01:00 - 06:59 arası yayın dışı saat dilimi (Paylaşımlar 07:00 - 24:00 arası yapılır).")
            return
        from src.news_fetcher import load_history
        hour_prefix = now_tr.strftime("%Y-%m-%dT%H:")
        hist_items = load_history().get("items", [])
        if any(str(it.get("published_at", "")).startswith(hour_prefix) for it in hist_items):
            print(f"[BİLGİ] Bu saat dilimi ({hour_prefix}00) için haber zaten yayınlanmış. Mükerrer paylaşım atlandı.")
            return

    # 1. Saatin kategorisini belirle
    category = get_category_for_current_hour(forced_cat or None)
    print(f"[1/5] Seçilen Kategori: {category['name']} ({category['id']})")

    # 2. Güncel haberi çek
    news_item = fetch_fresh_news_for_category(category)
    print(f"[2/5] Bulunan Haber Konusu: {news_item['raw_title']}")
    print(f"      -> Orijinal Kaynak Linki: {news_item.get('source_link', 'Rehber/Arşiv')}")

    # 3. SEO Makalesi üret
    if args.dry_run and not os.environ.get("GEMINI_API_KEY"):
        print("[3/5] GEMINI_API_KEY bulunamadı, --dry-run demo paketi kullanılıyor...")
        package = _build_demo_package(news_item, category)
    else:
        print("[3/5] SEO makalesi üretiliyor...")
        package = generate_news_and_reels_package(news_item, category)

    print(f"      -> SEO Başlık : {package['seo_title']}")

    # Çıktı klasörünü hazırla
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR, ignore_errors=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    # 4. Türkiye haber kaynaklarından konu anahtar kelimelerine göre gerçek kapak fotoğrafını indir ve üret
    print("[4/5] Türkiye haber kaynaklarından konuyla alakalı gerçek kapak fotoğrafı hazırlanıyor...")
    real_photos = fetch_news_images(
        news_title=news_item["raw_title"],
        category=category,
        ai_visual_queries=package.get("visual_queries"),
        work_dir=WORK_DIR / "photos",
        min_count=1,
        source_link=news_item.get("source_link", ""),
    )

    featured_img_path = OUTPUT_DIR / "featured_image.jpg"
    article_json_path = OUTPUT_DIR / "latest_package.json"

    with open(article_json_path, "w", encoding="utf-8") as f:
        json.dump(package, f, ensure_ascii=False, indent=2)

    generate_wp_featured_image(package, category, featured_img_path, real_photos=real_photos)
    print(f"      -> Kapak Görseli Hazır: {featured_img_path}")

    if args.dry_run:
        print("[TAMAMLANDI] --dry-run modu aktif olduğu için yayınlama adımı atlandı.")
        return

    # 5. Sadece WordPress (habermat.com) üzerine haber yayınlama (Sosyal medya paylaşımı devre dışı)
    wp_pub = WordPressPublisher()
    wp_post_url = ""

    if not args.skip_wp and wp_pub.is_configured():
        print("[5/5] WordPress (habermat.com) üzerine haber yayınlanıyor...")
        wp_res = wp_pub.publish_article(package, category, featured_img_path)
        wp_post_url = wp_res.get("link", "")
        print(f"       -> WordPress Yayınlandı: {wp_post_url}")

    # Geçmişe kaydet (Aynı haber tekrar yazılmasın ve kaynak linki saklansın)
    save_to_history(
        title=news_item["raw_title"],
        category_id=category["id"],
        wp_url=wp_post_url,
        ig_id="wp_only",
        source_url=news_item.get("source_link", ""),
    )

    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR, ignore_errors=True)

    print("============================================================")
    print("[BAŞARILI] Saatlik Habermat.com haber akışı tamamlandı! (Sosyal medya paylaşımı kapalı)")


if __name__ == "__main__":
    main()
