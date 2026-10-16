"""
Habermat.com - TikTok Otomatik Video Yayınlayıcı
TIKTOK_USERNAME (habermat5) ve TIKTOK_PASSWORD veya kayıtlı oturum çerezleriyle
(data/tiktok_cookies.json) 1080x1920 haber videolarını TikTok Studio'ya yükler ve paylaşır.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict

COOKIE_FILE = Path(__file__).resolve().parent.parent / "data" / "tiktok_cookies.json"


class TikTokPublisher:
    def __init__(self) -> None:
        self.username = os.environ.get("TIKTOK_USERNAME", "habermat5").strip()
        self.password = os.environ.get("TIKTOK_PASSWORD", "").strip()
        self.cookies_env = os.environ.get("TIKTOK_COOKIES_JSON", "").strip()

    def is_configured(self) -> bool:
        if self.cookies_env:
            return True
        if COOKIE_FILE.exists() and COOKIE_FILE.stat().st_size > 20:
            return True
        return bool(self.username and self.password)

    def _login_and_get_cookies(self, page, context) -> None:
        """
        TikTok giriş ekranını açar. Kullanıcı 'QR kodu kullanın' veya
        'Kullanıcı telefonu / e-posta / kullanıcı adı' seçeneğine tıkladığında
        kullanıcı adı (habermat5) ve şifreyi otomatik doldurur; giriş tamamlandığında
        oturumu `data/tiktok_cookies.json` içine kaydeder.
        """
        print(f"[BİLGİ] TikTok hesabına (@{self.username}) giriş ekranı açılıyor...")
        page.goto("https://www.tiktok.com/login", timeout=60000)
        filled_once = False

        # Oturum açılana kadar (sessionid oluşana kadar) bekle (maksimum 6 dakika)
        for _ in range(180):
            time.sleep(2)
            cookies = context.cookies()
            has_session = any(c.get("name") in ("sessionid", "sessionid_ss", "sid_tt") for c in cookies)
            if has_session:
                print("[BAŞARILI] TikTok girişi onaylandı! Oturum kaydediliyor...")
                time.sleep(3)
                cookies = context.cookies()
                COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(COOKIE_FILE, "w", encoding="utf-8") as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                return

            # Eğer kullanıcı e-posta/kullanıcı adı sekmesine geçtiyse bilgileri otomatik doldur
            if not filled_once:
                try:
                    user_input = page.locator('input[name="username"]').first
                    pass_input = page.locator('input[type="password"]').first
                    if user_input.is_visible(timeout=500) and pass_input.is_visible(timeout=500):
                        user_input.click()
                        user_input.fill(self.username)
                        time.sleep(0.3)
                        pass_input.click()
                        pass_input.fill(self.password)
                        filled_once = True
                        print("[BİLGİ] Kullanıcı adı ve şifre kutucuklara otomatik yazıldı, 'Giriş yap' butonuna basabilirsiniz.")
                except Exception:
                    pass

        raise RuntimeError("TikTok girişi zaman aşımına uğradı veya doğrulama tamamlanmadı.")

    def publish_tiktok(self, video_path: Path, caption: str) -> Dict[str, Any]:
        """
        TikTok Studio'yu açar, oturum yoksa otomatik giriş yapar,
        MP4 videosunu yükler, açıklamayı yazar ve 'Gönder / Paylaş' butonuna basar.
        """
        from playwright.sync_api import sync_playwright

        clean_caption = caption[:2000]
        has_saved_cookies = bool(self.cookies_env or (COOKIE_FILE.exists() and COOKIE_FILE.stat().st_size > 20))
        is_ci = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
        run_headless = True if (has_saved_cookies or is_ci) else False

        with sync_playwright() as p:
            launch_kwargs = {
                "headless": run_headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            }
            try:
                browser = p.chromium.launch(channel="chrome", **launch_kwargs)
            except Exception:
                browser = p.chromium.launch(**launch_kwargs)

            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
                locale="tr-TR",
            )
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )

            if self.cookies_env:
                context.add_cookies(json.loads(self.cookies_env))
            elif COOKIE_FILE.exists() and COOKIE_FILE.stat().st_size > 20:
                with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                    context.add_cookies(json.load(f))

            page = context.new_page()

            if not has_saved_cookies:
                if is_ci:
                    browser.close()
                    raise RuntimeError("GitHub Actions üzerinde TIKTOK_COOKIES_JSON tanımlanmamış!")
                self._login_and_get_cookies(page, context)

            print("[BİLGİ] TikTok Studio yükleme sayfası açılıyor...")
            page.goto("https://www.tiktok.com/tiktokstudio/upload?lang=tr-TR", timeout=60000)
            time.sleep(5)

            # Eğer giriş sayfasına yönlendirdiyse otomatik giriş yap
            if "login" in page.url.lower():
                if is_ci:
                    browser.close()
                    raise RuntimeError("GitHub Actions üzerinde TIKTOK_COOKIES_JSON geçersiz veya süresi dolmuş!")
                self._login_and_get_cookies(page, context)
                page.goto("https://www.tiktok.com/tiktokstudio/upload?lang=tr-TR", timeout=60000)
                time.sleep(5)

            # 1. Dosya yükleme input alanını bul ve MP4 dosyasını gönder
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(str(video_path.resolve()), timeout=45000)
            print("[BİLGİ] Video dosyası TikTok'a aktarılıyor, işlenmesi bekleniyor...")

            # 2. Açıklama (Caption) alanının yüklenmesini bekle
            caption_editor = page.locator('div[contenteditable="true"]').first
            caption_editor.wait_for(state="visible", timeout=60000)
            time.sleep(5)

            def _dismiss_popups() -> None:
                # "Otomatik içerik kontrolleri açılsın mı?" -> "İptal" ve "Anladım" balonlarını kapat
                for sel in [
                    'button:has-text("İptal")',
                    'button:has-text("Anladım")',
                    'button:has-text("Got it")',
                    'button:has-text("Şimdi değil")',
                    'button:has-text("Kabul et")',
                ]:
                    try:
                        loc = page.locator(sel)
                        count = loc.count()
                        for idx in range(count):
                            btn = loc.nth(idx)
                            if btn.is_visible(timeout=500):
                                btn.click(force=True)
                                time.sleep(0.6)
                    except Exception:
                        pass

            _dismiss_popups()
            time.sleep(1)
            _dismiss_popups()

            # 3. Açıklama metnini gir
            caption_editor.click(force=True)
            time.sleep(0.4)
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            time.sleep(0.4)
            page.keyboard.insert_text(clean_caption)
            time.sleep(1.5)
            page.keyboard.press("Escape")

            # 4. Videonun yükleme işleminin tamamlanmasını bekle
            print("[BİLGİ] Videonun TikTok sunucusunda işlenmesi bekleniyor (18 sn)...")
            time.sleep(18)
            _dismiss_popups()

            # 5. "Paylaş" / "Gönder" (Post) butonuna tıkla
            post_btn = page.locator(
                'button[data-e2e="post_video_button"], '
                'button:has-text("Paylaş")'
            ).first
            post_btn.scroll_into_view_if_needed()
            time.sleep(1)
            post_btn.click(force=True)
            print("[BİLGİ] TikTok 'Paylaş' butonuna tıklandı, onay bekleniyor...")
            time.sleep(5)

            # Olası ikinci onay penceresi ("Şimdi paylaş" / "Şimdi gönder" / "Post now") çıkarsa tıkla
            for confirm_sel in [
                'button:has-text("Şimdi paylaş")',
                'button:has-text("Şimdi gönder")',
                'button:has-text("Yayınla")',
                'button:has-text("Post now")',
                'button:has-text("Devam et")',
            ]:
                try:
                    cbtn = page.locator(confirm_sel).first
                    if cbtn.is_visible(timeout=1500):
                        cbtn.click(force=True)
                except Exception:
                    pass

            time.sleep(8)
            print(f"[BİLGİ] Son TikTok URL: {page.url}")

            # Güncel çerezleri kaydet
            updated_cookies = context.cookies()
            COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(COOKIE_FILE, "w", encoding="utf-8") as f:
                json.dump(updated_cookies, f, ensure_ascii=False, indent=2)

            browser.close()
            return {"status": "published", "platform": "tiktok"}
