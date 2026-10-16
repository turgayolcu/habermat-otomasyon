"""
Habermat.com - Instagram Reels Otomatik Yayınlayıcı
Token gerektirmeden doğrudan Instagram Kullanıcı Adı (haberoku34) ve Şifresi ile
(veya varsa Graph API ile) Reels videosunu paylaşır.
"""

import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from src.wp_publisher import WordPressPublisher

SESSION_FILE = Path(__file__).resolve().parent.parent / "data" / "ig_session.json"


class InstagramReelsPublisher:
    def __init__(self) -> None:
        self.ig_username = (
            os.environ.get("IG_USERNAME", "").strip()
            or os.environ.get("IG_USER_ID", "").strip()
        )
        self.ig_password = os.environ.get("IG_PASSWORD", "").strip()
        self.ig_user_id = os.environ.get("IG_USER_ID", "").strip()
        self.access_token = os.environ.get("IG_ACCESS_TOKEN", "").strip()

    def is_configured(self) -> bool:
        has_login = bool(self.ig_username and self.ig_password)
        has_graph = bool(self.ig_user_id and self.access_token)
        return has_login or has_graph

    def _publish_via_instagrapi(self, video_path: Path, caption: str) -> Dict[str, Any]:
        """Doğrudan Instagram kullanıcı adı (haberoku34) ve şifresi ile Reels yükler."""
        from instagrapi import Client

        cl = Client()
        cl.delay_range = [2, 5]

        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        logged_in = False

        if SESSION_FILE.exists():
            try:
                cl.load_settings(SESSION_FILE)
                cl.login(self.ig_username, self.ig_password)
                logged_in = True
            except Exception:
                logged_in = False

        if not logged_in:
            cl.login(self.ig_username, self.ig_password)
            cl.dump_settings(SESSION_FILE)

        media = cl.clip_upload(path=video_path, caption=caption)
        cl.dump_settings(SESSION_FILE)
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
            raise RuntimeError("Instagram kullanıcı adı (haberoku34) ve şifresi eksik!")

        # Eğer normal Instagram kullanıcı adı ve şifresi girildiyse doğrudan yükle
        if self.ig_username and self.ig_password:
            print(f"[BİLGİ] @{self.ig_username} hesabına doğrudan Reels yükleniyor...")
            return self._publish_via_instagrapi(video_path, caption)

        # Yedek: Graph API Token varsa
        raise RuntimeError("Instagram şifresi (IG_PASSWORD) tanımlanmamış!")
