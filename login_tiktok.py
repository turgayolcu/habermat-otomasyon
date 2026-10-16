"""
Habermat.com - TikTok 1 Kez Giriş ve Oturum Kaydetme Aracı
Bu betiği çalıştırdığınızda ekranda bir tarayıcı penceresi açılır.
TikTok hesabınıza (QR Kod, Telefon, E-posta veya Kullanıcı Adı/Şifre ile) 1 kez giriş yapmanız yeterlidir.
Giriş tamamlandığında oturumunuz otomatik olarak `data/tiktok_cookies.json` dosyasına kaydedilir!
"""

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

COOKIE_FILE = Path(__file__).resolve().parent / "data" / "tiktok_cookies.json"


def main() -> None:
    print("============================================================")
    print("[TİKTOK GİRİŞ ARACI] Tarayıcı açılıyor...")
    print("Lütfen açılan pencerede TikTok hesabınıza giriş yapın.")
    print("Giriş yaptığınızda oturumunuz otomatik kaydedilecek ve pencere kapanacaktır.")
    print("============================================================")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception:
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
        context = browser.new_context(
            viewport={"width": 1200, "height": 850},
            locale="tr-TR",
        )
        page = context.new_page()
        page.goto("https://www.tiktok.com/login", timeout=60000)

        # Kullanıcı giriş yapana kadar (`sessionid` çerezi oluşana kadar) bekle
        for _ in range(180):
            time.sleep(2)
            cookies = context.cookies()
            has_session = any(c.get("name") in ("sessionid", "sessionid_ss", "sid_tt") for c in cookies)
            if has_session:
                print("\n[BAŞARILI] TikTok girişi algılandı! Oturum kaydediliyor...")
                time.sleep(3)
                cookies = context.cookies()
                COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(COOKIE_FILE, "w", encoding="utf-8") as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                print(f"[KAYDEDİLDİ] TikTok oturumu şuraya kaydedildi: {COOKIE_FILE}")
                browser.close()
                return

        print("[ZAMAN AŞIMI] 6 dakika içinde giriş tamamlanmadı.")
        browser.close()


if __name__ == "__main__":
    main()
