"""
Habermat.com - WordPress Otomatik Haber Yayınlayıcı
Ekstra token veya uygulama şifresi gerektirmeden doğrudan normal WordPress
kullanıcı adı (editor) ve şifresi ile (Cookie Nonce / XML-RPC / Basic Auth) haber yayınlar!
"""

import base64
import os
import re
import xmlrpc.client
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


class WordPressPublisher:
    def __init__(self) -> None:
        raw_url = os.environ.get("WP_URL", "https://habermat.com").strip().rstrip("/")
        self.base_url = raw_url
        self.api_base = f"{self.base_url}/wp-json/wp/v2"
        self.username = os.environ.get("WP_USERNAME", "").strip()
        self.password = (
            os.environ.get("WP_PASSWORD", "").strip()
            or os.environ.get("WP_APP_PASSWORD", "").strip()
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                )
            }
        )
        self._rest_nonce: Optional[str] = None
        self._authenticated_cookie = False

    def is_configured(self) -> bool:
        return bool(self.base_url and self.username and self.password)

    def _ensure_session_or_auth(self) -> Dict[str, str]:
        """
        Hem normal WordPress kullanıcı şifresi (wp-login.php üzerinden Cookie + Nonce)
        hem de Application Password (Basic Auth) ile otomatik giriş sağlar.
        """
        if self._rest_nonce:
            return {"X-WP-Nonce": self._rest_nonce}

        # 1. Önce wp-login.php üzerinden normal kullanıcı adı ve şifre ile oturum açmayı dene (3 deneme)
        import time
        for attempt in range(3):
            try:
                login_url = f"{self.base_url}/wp-login.php"
                self.session.get(login_url, timeout=15)
                login_data = {
                    "log": self.username,
                    "pwd": self.password,
                    "wp-submit": "Giriş",
                    "redirect_to": f"{self.base_url}/wp-admin/",
                    "testcookie": "1",
                }
                self.session.post(
                    login_url,
                    data=login_data,
                    cookies={"wordpress_test_cookie": "WP Cookie check"},
                    timeout=20,
                    allow_redirects=True,
                )
                if any("wordpress_logged_in" in c.name for c in self.session.cookies):
                    self._authenticated_cookie = True
                    admin_resp = self.session.get(f"{self.base_url}/wp-admin/post-new.php", timeout=20)
                    m = re.search(r'wpApiSettings\s*=\s*\{[^}]*"nonce"\s*:\s*"([a-zA-Z0-9]+)"', admin_resp.text)
                    if m:
                        self._rest_nonce = m.group(1)
                        return {"X-WP-Nonce": self._rest_nonce}
            except Exception as exc:
                print(f"[BİLGİ] WP Cookie girişi denemesi ({attempt+1}/3): {exc}")
                time.sleep(2)

        # 2. Basic Auth (Application Password veya Basic Auth eklentisi varsa)
        token = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("utf-8")
        return {"Authorization": f"Basic {token}"}

    def _publish_via_xmlrpc(
        self,
        package: Dict[str, Any],
        category: dict,
        featured_image_path: Path,
    ) -> Dict[str, Any]:
        """
        REST API yerine WordPress'in yerleşik XML-RPC arayüzü (normal kullanıcı adı + şifre)
        üzerinden görseli ve haberi yayınlar.
        """
        rpc_url = f"{self.base_url}/xmlrpc.php"
        server = xmlrpc.client.ServerProxy(rpc_url)

        # 1. Kapak görselini yükle
        with open(featured_image_path, "rb") as f:
            img_bits = xmlrpc.client.Binary(f.read())

        media_struct = {
            "name": f"{package['slug']}.jpg",
            "type": "image/jpeg",
            "bits": img_bits,
            "overwrite": True,
        }
        media_res = server.wp.uploadFile(1, self.username, self.password, media_struct)
        attachment_id = media_res.get("id") or media_res.get("attachment_id")

        # 2. Kategorinin var olduğundan emin ol
        try:
            existing_cats = server.wp.getTerms(1, self.username, self.password, "category")
            cat_exists = any(
                c.get("name", "").lower() == category["name"].lower() or c.get("slug") == category["wp_slug"]
                for c in existing_cats
            )
            if not cat_exists:
                server.wp.newTerm(
                    1,
                    self.username,
                    self.password,
                    {"name": category["name"], "taxonomy": "category", "slug": category["wp_slug"]},
                )
        except Exception:
            pass

        # 3. Haberi yayınla
        content_struct: Dict[str, Any] = {
            "post_type": "post",
            "post_status": "publish",
            "post_title": package["seo_title"],
            "post_name": package["slug"],
            "post_excerpt": package["meta_description"],
            "post_content": package["wp_html_content"],
            "terms_names": {
                "category": [category["name"]],
                "post_tag": package.get("tags", [])[:6],
            },
        }
        if attachment_id:
            content_struct["post_thumbnail"] = int(attachment_id)

        post_id = server.wp.newPost(1, self.username, self.password, content_struct)
        return {
            "post_id": post_id,
            "link": f"{self.base_url}/?p={post_id}",
            "featured_media_id": attachment_id,
        }

    def get_or_create_category(self, name: str, slug: str) -> Optional[int]:
        headers = self._ensure_session_or_auth()
        try:
            resp = self.session.get(
                f"{self.api_base}/categories",
                params={"search": name, "per_page": 20},
                headers=headers,
                timeout=20,
            )
            if resp.status_code == 200:
                for item in resp.json():
                    if item.get("slug") == slug or item.get("name", "").lower() == name.lower():
                        return int(item["id"])

            create_resp = self.session.post(
                f"{self.api_base}/categories",
                json={"name": name, "slug": slug},
                headers=headers,
                timeout=20,
            )
            if create_resp.status_code in (200, 201):
                return int(create_resp.json()["id"])
        except Exception as exc:
            print(f"[UYARI] WordPress kategori eşleştirme hatası: {exc}")
        return None

    def get_or_create_tags(self, tag_names: List[str]) -> List[int]:
        headers = self._ensure_session_or_auth()
        tag_ids: List[int] = []
        for tag in tag_names[:6]:
            try:
                resp = self.session.get(
                    f"{self.api_base}/tags",
                    params={"search": tag, "per_page": 5},
                    headers=headers,
                    timeout=15,
                )
                found_id = None
                if resp.status_code == 200:
                    for item in resp.json():
                        if item.get("name", "").lower() == tag.lower():
                            found_id = int(item["id"])
                            break
                if not found_id:
                    c_resp = self.session.post(
                        f"{self.api_base}/tags",
                        json={"name": tag},
                        headers=headers,
                        timeout=15,
                    )
                    if c_resp.status_code in (200, 201):
                        found_id = int(c_resp.json()["id"])
                if found_id:
                    tag_ids.append(found_id)
            except Exception:
                continue
        return tag_ids

    def upload_media(self, file_path: Path, alt_text: str = "", title: str = "") -> Dict[str, Any]:
        ext = file_path.suffix.lower()
        mime_type = "video/mp4" if ext == ".mp4" else "image/jpeg"
        filename = file_path.name

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        headers = self._ensure_session_or_auth().copy()
        headers.update(
            {
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": mime_type,
            }
        )
        resp = self.session.post(
            f"{self.api_base}/media",
            data=file_bytes,
            headers=headers,
            timeout=90,
        )
        resp.raise_for_status()
        media_data = resp.json()
        media_id = media_data["id"]

        if mime_type.startswith("image/") and (alt_text or title):
            try:
                self.session.post(
                    f"{self.api_base}/media/{media_id}",
                    json={"alt_text": alt_text, "title": title, "caption": alt_text},
                    headers=self._ensure_session_or_auth(),
                    timeout=20,
                )
            except Exception:
                pass

        return {
            "id": media_id,
            "source_url": media_data.get("source_url", ""),
        }

    def delete_media(self, media_id: int) -> None:
        try:
            self.session.delete(
                f"{self.api_base}/media/{media_id}",
                params={"force": "true"},
                headers=self._ensure_session_or_auth(),
                timeout=20,
            )
        except Exception:
            pass

    def publish_article(
        self,
        package: Dict[str, Any],
        category: dict,
        featured_image_path: Path,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("WordPress kullanıcı adı ve şifresi eksik!")

        # Önce REST API (Cookie Nonce / Basic Auth) ile dene, olmazsa otomatik XML-RPC ile yayınla
        try:
            media_info = self.upload_media(
                featured_image_path,
                alt_text=package["seo_title"],
                title=package["seo_title"],
            )
            featured_media_id = media_info["id"]
            cat_id = self.get_or_create_category(category["name"], category["wp_slug"])
            tag_ids = self.get_or_create_tags(package.get("tags", []))

            post_payload: Dict[str, Any] = {
                "title": package["seo_title"],
                "slug": package["slug"],
                "status": "publish",
                "content": package["wp_html_content"],
                "excerpt": package["meta_description"],
                "featured_media": featured_media_id,
            }
            if cat_id:
                post_payload["categories"] = [cat_id]
            if tag_ids:
                post_payload["tags"] = tag_ids

            resp = self.session.post(
                f"{self.api_base}/posts",
                json=post_payload,
                headers=self._ensure_session_or_auth(),
                timeout=30,
            )
            resp.raise_for_status()
            post_data = resp.json()
            return {
                "post_id": post_data.get("id"),
                "link": post_data.get("link", f"{self.base_url}/{package['slug']}"),
                "featured_media_id": featured_media_id,
            }
        except Exception as rest_err:
            print(f"[BİLGİ] REST API yerine doğrudan WordPress XML-RPC ile yayınlanıyor ({rest_err})...")
            return self._publish_via_xmlrpc(package, category, featured_image_path)
