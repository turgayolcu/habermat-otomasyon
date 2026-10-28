"""
Habermat.com - Instagram Reels Otomatik Yayınlayıcı
Token gerektirmeden doğrudan Instagram Kullanıcı Adı (haberoku34), Şifresi ve
kayıtlı oturum anahtarı (IG_SESSION_JSON / data/ig_session.json) ile Reels videosunu paylaşır.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from src.wp_publisher import WordPressPublisher

SESSION_FILE = Path(__file__).resolve().parent.parent / "data" / "ig_session.json"


class InstagramReelsPublisher:
    def __init__(self) -> None:
        self.ig_username = (
            os.environ.get("IG_USERNAME", "haberoku34").strip()
            or os.environ.get("IG_USER_ID", "").strip()
        )
        self.ig_password = os.environ.get("IG_PASSWORD", "").strip()
        self.ig_session_env = os.environ.get("IG_SESSION_JSON", "").strip()
        self.ig_user_id = os.environ.get("IG_USER_ID", "").strip()
        self.access_token = os.environ.get("IG_ACCESS_TOKEN", "").strip()

    def is_configured(self) -> bool:
        has_session = bool(self.ig_session_env or (SESSION_FILE.exists() and SESSION_FILE.stat().st_size > 20))
        has_login = bool(self.ig_username and self.ig_password)
        has_graph = bool(self.ig_user_id and self.access_token)
        return has_session or has_login or has_graph

    def _publish_via_instagrapi(self, video_path: Path, caption: str) -> Dict[str, Any]:
        """Doğrudan Instagram oturumu (data/ig_session.json) ve kullanıcı bilgileri ile Reels yükler."""
        import subprocess
        from instagrapi import Client

        thumb_path = video_path.with_suffix(".thumb.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(video_path), "-frames:v", "1", "-q:v", "2", str(thumb_path)],
            check=True,
            capture_output=True,
        )

        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        if self.ig_session_env:
            try:
                SESSION_FILE.write_text(self.ig_session_env, encoding="utf-8")
            except Exception:
                pass

        def _create_client(force_fresh_login: bool = False) -> Client:
            cl = Client()
            cl.delay_range = [2, 5]
            logged_in = False

            if not force_fresh_login and SESSION_FILE.exists():
                try:
                    settings = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
                    cl.set_settings(settings)
                    sessionid = settings.get("authorization_data", {}).get("sessionid", "")
                    if sessionid:
                        cl.login_by_sessionid(sessionid)
                        logged_in = True
                    elif self.ig_username and self.ig_password:
                        cl.login(self.ig_username, self.ig_password)
                        logged_in = True
                except Exception:
                    logged_in = False

            if not logged_in:
                if not (self.ig_username and self.ig_password):
                    raise RuntimeError("Instagram kullanıcı adı ve şifresi eksik!")
                cl = Client()
                cl.delay_range = [2, 5]
                cl.login(self.ig_username, self.ig_password)
                try:
                    cl.dump_settings(SESSION_FILE)
                except Exception:
                    pass
            return cl

        try:
            cl = _create_client(force_fresh_login=False)
            media = cl.clip_upload(path=video_path, caption=caption, thumbnail=thumb_path)
        except Exception as first_err:
            if self.ig_username and self.ig_password:
                print(f"[BİLGİ] Kayıtlı Instagram oturumu yenileniyor ({first_err})...")
                cl = _create_client(force_fresh_login=True)
                media = cl.clip_upload(path=video_path, caption=caption, thumbnail=thumb_path)
            else:
                raise

        try:
            cl.dump_settings(SESSION_FILE)
        except Exception:
            pass
        return {
            "media_id": str(getattr(media, "pk", "") or getattr(media, "id", "")),
            "code": str(getattr(media, "code", "")),
        }

    def publish_reels(
        self,
        video_path: Path,
        caption: str,
        wp_publisher: Optional[WordPressPublisher] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("Instagram oturumu veya şifresi eksik!")

        print(f"[BİLGİ] @{self.ig_username} Instagram hesabına Reels yükleniyor...")
        return self._publish_via_instagrapi(video_path, caption)
