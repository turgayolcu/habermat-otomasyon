"""
Habermat.com - Gerçek Fotoğraflı Kapak Görseli (1200x675) ve Çoklu Slaytlı Reels Video (1080x1920) Motoru
- Kapak Görseli: Google/Türk haber kaynaklarından alınan gerçek fotoğraf + üzerinde Manşet ve HABERMAT.COM logosu
- Reels Videosu: Haberle alakalı ve çağrışım yapan en az 3-4 gerçek dikey fotoğraf slaytı
- Seslendirme: Doğal insan hızında (+0%) erkek haber spikeri (en-US-AndrewMultilingualNeural / BrianMultilingualNeural)
- Altyazı: Spikerin kelime okuma hızına (WordBoundary milisaniye zamanlamasına) birebir duyarlı senkronize altyazı
"""

import asyncio
import math
import os
import struct
import subprocess
import textwrap
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import edge_tts
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

# iddaaliyiz.tv'de kullanılan %100 Doğal Erkek Türkçe Spiker Sesi (tr-TR-AhmetNeural)
PRIMARY_TR_VOICE = os.environ.get("TTS_VOICE", "tr-TR-AhmetNeural")
VOICE_RATE = os.environ.get("TTS_RATE", "+0%")  # Tam doğal spiker konuşma hızı

# Renk Paleti (Kırmızı - Beyaz - Koyu Lacivert Haber TV Teması)
COLOR_NAVY_DARK = (11, 19, 43)       # #0B132B
COLOR_NAVY_MID = (28, 37, 65)        # #1C2541
COLOR_RED = (217, 4, 41)             # #D90429
COLOR_RED_BRIGHT = (239, 35, 60)     # #EF233C
COLOR_WHITE = (255, 255, 255)        # #FFFFFF
COLOR_GOLD = (255, 195, 0)           # #FFC300


def tr_upper(text: str) -> str:
    """Türkçe karakter kurallarına uygun büyük harfe çevirme (i -> İ, ı -> I)."""
    return text.replace("i", "İ").replace("ı", "I").upper()


def _get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Windows ve Ubuntu (GitHub Actions) üzerinde Türkçe karakter destekli font yükler."""
    candidates = (
        [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]
        if bold
        else [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
    )
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _fit_and_crop_photo(
    photo_path: Optional[Path],
    target_w: int,
    target_h: int,
    zoom: float = 1.0,
) -> Image.Image:
    """
    Gerçek haber fotoğrafını hedef en-boy oranına (1200x675 yatay veya 1080x1920 dikey)
    sündürmeden (aspect-fill / center-crop) yerleştirir ve hafif zoom uygular.
    """
    if photo_path and photo_path.exists():
        try:
            src = Image.open(photo_path).convert("RGB")
            sw, sh = src.size
            scale = max(target_w / sw, target_h / sh) * max(zoom, 1.0)
            nw, nh = int(sw * scale), int(sh * scale)
            resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
            left = max(0, (nw - target_w) // 2)
            top = max(0, (nh - target_h) // 2)
            cropped = resized.crop((left, top, left + target_w, top + target_h))
            # Haber fotoğrafının kontrastını ve canlılığını hafif artır
            cropped = ImageEnhance.Contrast(cropped).enhance(1.08)
            cropped = ImageEnhance.Color(cropped).enhance(1.06)
            return cropped
        except Exception as exc:
            print(f"[UYARI] Fotoğraf işlenemedi ({photo_path}): {exc}")

    # Yedek stüdyo arka planı (sadece fotoğraf bulunamazsa)
    fallback = Image.new("RGB", (target_w, target_h), COLOR_NAVY_DARK)
    return fallback


def generate_wp_featured_image(
    package: Dict[str, Any],
    category: dict,
    output_path: Path,
    real_photos: Optional[List[Path]] = None,
) -> Path:
    """
    WordPress ve Google Keşfet için 1200x675 (16:9) boyutunda:
    - Arka planda haberle alakalı gerçek Google/Haber fotoğrafı
    - Fotoğrafın üzerinde sinematik karartma geçişi ve büyük MANŞET yazısı
    - Sol üstte HABERMAT.COM logosu ve kategori rozeti
    üretir.
    """
    width, height = 1200, 675
    cover_photo = real_photos[0] if real_photos else None
    base_img = _fit_and_crop_photo(cover_photo, width, height, zoom=1.02).convert("RGBA")

    # Fotoğrafın üzerine okunaklılık sağlayan sinematik gradyan katmanı (Üstte hafif, altta güçlü)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    for y in range(height):
        if y < 140:
            # Üst bar için karartma
            alpha = int(185 * (1.0 - (y / 140.0) * 0.55))
        elif y < 230:
            # Orta alan (Fotoğrafın en net göründüğü kısım)
            alpha = int(75 + (y - 140) * 0.4)
        else:
            # Alt manşet alanı için kademeli koyu lacivert/siyah karartma
            ratio = (y - 230) / max(height - 230, 1)
            alpha = int(115 + min(ratio * 135, 130))
        odraw.line([(0, y), (width, y)], fill=(8, 13, 30, alpha))

    img = Image.alpha_composite(base_img, overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    font_logo = _get_font(34, bold=True)
    font_badge = _get_font(25, bold=True)
    font_headline = _get_font(54, bold=True)
    font_sub = _get_font(25, bold=True)

    # Üst kırmızı şerit
    draw.rectangle([0, 0, width, 12], fill=COLOR_RED)

    # Sol üst: HABERMAT.COM kurumsal logo kutusu
    draw.rounded_rectangle([55, 36, 385, 102], radius=12, fill=COLOR_RED)
    draw.text((79, 50), "HABERMAT.COM", font=font_logo, fill=COLOR_WHITE)

    # Kategori rozeti
    badge_text = tr_upper(package.get("reels_badge", "SON DAKİKA"))
    b_box = draw.textbbox((0, 0), badge_text, font=font_badge)
    badge_w = (b_box[2] - b_box[0]) + 48
    draw.rounded_rectangle([405, 40, 405 + badge_w, 98], radius=10, fill=(11, 19, 43), outline=COLOR_GOLD, width=3)
    draw.text((429, 55), badge_text, font=font_badge, fill=COLOR_GOLD)

    # Fotoğrafın Üzerinde Manşet Yazısı (Alt yarıya hizalı)
    headline = tr_upper(package.get("seo_title", package.get("reels_headline", "")))
    wrapped_lines = textwrap.wrap(headline, width=27)[:3]
    line_h = 72
    total_h = len(wrapped_lines) * line_h
    y_cursor = height - 115 - total_h

    # Manşetin soluna dikey kırmızı vurgu barı
    draw.rounded_rectangle([55, y_cursor + 6, 71, y_cursor + total_h - 8], radius=6, fill=COLOR_RED)

    for idx, line in enumerate(wrapped_lines):
        # Güçlü siyah gölge + Beyaz/Altın manşet metni
        draw.text((92, y_cursor + 4), line, font=font_headline, fill=(0, 0, 0))
        draw.text((90, y_cursor + 2), line, font=font_headline, fill=(0, 0, 0))
        line_color = COLOR_GOLD if idx == len(wrapped_lines) - 1 else COLOR_WHITE
        draw.text((88, y_cursor), line, font=font_headline, fill=line_color)
        y_cursor += line_h

    # Alt bilgi bandı (Ticker bar)
    draw.rectangle([0, height - 82, width, height], fill=COLOR_RED)
    draw.rectangle([0, height - 86, width, height - 82], fill=COLOR_GOLD)
    footer_text = "BAŞVURU ŞARTLARI VE DETAYLAR İÇİN: GOOGLE'A HABERMAT.COM YAZIN"
    draw.text((55, height - 56), footer_text, font=font_sub, fill=COLOR_WHITE)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="JPEG", quality=85, optimize=True)
    return output_path


def _render_reels_slide(
    package: Dict[str, Any],
    category: dict,
    photo_path: Optional[Path],
    photo_index: int,
    total_photos: int,
    zoom_factor: float,
    subtitle_text: str,
    progress_ratio: float,
    is_cta_screen: bool,
    slide_index: int,
) -> Image.Image:
    """
    1080x1920 dikey Reels sahnesi:
    - Arka planda ve orta pencerede gerçek dikey fotoğraf slaytı (en az 3-4 farklı gerçek fotoğraf)
    - Üstte HABERMAT.COM barı + Manşet
    - Ortada net gerçek haber fotoğrafı + fotoğraf slayt göstergesi (1/4, 2/4...)
    - Altta spikerin konuşma hızıyla birebir senkronize altyazı kutusu
    - En altta Google 'habermat.com' arama çubuğu
    """
    width, height = 1080, 1920

    # 1. Arka plan: Gerçek fotoğrafın bulanıklaştırılmış ve karartılmış stüdyo ambiyansı
    bg_ambient = _fit_and_crop_photo(photo_path, width, height, zoom=1.05).filter(
        ImageFilter.GaussianBlur(radius=26)
    )
    bg_ambient = ImageEnhance.Brightness(bg_ambient).enhance(0.32)
    img = bg_ambient.convert("RGB")

    # 2. ORTA VİTRİN (Y: 435 - 1055 -> 980x620): Gerçek fotoğrafın kırpılmadan net göründüğü ana ekran!
    showcase_w, showcase_h = 980, 620
    sharp_photo = _fit_and_crop_photo(photo_path, showcase_w, showcase_h, zoom=zoom_factor)
    img.paste(sharp_photo, (50, 435))

    draw = ImageDraw.Draw(img)

    font_logo = _get_font(40, bold=True)
    font_badge = _get_font(23, bold=True)
    font_cat = _get_font(34, bold=True)
    font_headline = _get_font(48, bold=True)
    font_sub = _get_font(50, bold=True)
    font_cta_title = _get_font(44, bold=True)
    font_cta_box = _get_font(54, bold=True)
    font_footer = _get_font(30, bold=True)
    font_pill = _get_font(24, bold=True)

    # 1. ÜST KURUMSAL HABER BARI (Y: 75 - 175)
    draw.rounded_rectangle([50, 75, 1030, 175], radius=18, fill=COLOR_NAVY_MID, outline=COLOR_RED, width=4)
    draw.rounded_rectangle([50, 75, 455, 175], radius=18, fill=COLOR_RED)
    draw.text((78, 103), "HABERMAT.COM", font=font_logo, fill=COLOR_WHITE)

    badge_text = tr_upper(package.get("reels_badge", "SON DAKİKA"))
    dot_color = COLOR_GOLD if slide_index % 2 == 0 else COLOR_RED_BRIGHT
    draw.ellipse([482, 113, 506, 137], fill=dot_color)
    draw.text((520, 112), badge_text[:35], font=font_badge, fill=COLOR_WHITE)

    # 2. ÜST MANŞET KARTI (Fotoğrafın üst kısmında - Y: 195 - 415)
    draw.rounded_rectangle(
        [50, 195, 1030, 415],
        radius=22,
        fill=(14, 22, 48),
        outline=COLOR_RED,
        width=3,
    )
    headline = tr_upper(package.get("reels_headline", package.get("seo_title", "")))
    h_lines = textwrap.wrap(headline, width=24)[:3]
    y_h = 215 + max(0, (180 - len(h_lines) * 58) // 2)
    for line in h_lines:
        bbox = draw.textbbox((0, 0), line, font=font_headline)
        lw = bbox[2] - bbox[0]
        xh = (width - lw) // 2
        draw.text((xh + 3, y_h + 3), line, font=font_headline, fill=(0, 0, 0))
        draw.text((xh, y_h), line, font=font_headline, fill=COLOR_GOLD if len(h_lines) == 1 else COLOR_WHITE)
        y_h += 58

    # 3. ORTA GERÇEK FOTOĞRAF VİTRİN ÇERÇEVESİ (Y: 435 - 1055)
    # Fotoğrafın etrafına şık kırmızı/altın yayın çerçevesi ve slayt göstergesi
    draw.rounded_rectangle(
        [50, 435, 1030, 1055],
        radius=24,
        fill=None,
        outline=COLOR_GOLD if is_cta_screen else COLOR_RED,
        width=5,
    )
    # Sol üst kategori etiketi (Fotoğrafın köşesinde)
    cat_label = tr_upper(category.get("visual_keywords", category.get("name", "GÜNDEM")))
    c_box = draw.textbbox((0, 0), f"► {cat_label}", font=font_pill)
    cw = (c_box[2] - c_box[0]) + 36
    draw.rounded_rectangle([70, 455, 70 + cw, 505], radius=12, fill=COLOR_RED)
    draw.text((88, 467), f"► {cat_label}", font=font_pill, fill=COLOR_WHITE)

    # Sağ üst slayt sayacı (Örn: GÖRSEL 1/4) + Nokta göstergeleri
    for p_i in range(max(total_photos, 3)):
        dot_x = 990 - (max(total_photos, 3) - 1 - p_i) * 28
        dot_c = COLOR_GOLD if p_i == photo_index else (180, 180, 180)
        draw.ellipse([dot_x - 8, 472, dot_x + 8, 488], fill=dot_c, outline=(0, 0, 0), width=2)

    # Fotoğrafın alt kenarında ses ilerleme çubuğu
    bar_left, bar_right = 75, 1005
    bar_y = 1025
    draw.rounded_rectangle([bar_left, bar_y, bar_right, bar_y + 14], radius=7, fill=(25, 35, 65))
    fill_w = max(20, int((bar_right - bar_left) * min(max(progress_ratio, 0.04), 1.0)))
    draw.rounded_rectangle([bar_left, bar_y, bar_left + fill_w, bar_y + 14], radius=7, fill=COLOR_GOLD)

    # 4. SPİKERİN HIZINA DUYARLI SENKRONİZE ALTYAZI KUTUSU (Y: 1080 - 1385)
    draw.rounded_rectangle(
        [50, 1080, 1030, 1385],
        radius=24,
        fill=(8, 12, 28),
        outline=COLOR_GOLD if is_cta_screen else COLOR_WHITE,
        width=4,
    )
    sub_lines = textwrap.wrap(subtitle_text, width=22)[:3]
    total_sub_h = len(sub_lines) * 66
    y_sub = 1080 + (305 - total_sub_h) // 2
    for sline in sub_lines:
        bbox = draw.textbbox((0, 0), sline, font=font_sub)
        line_w = bbox[2] - bbox[0]
        x_sub = (width - line_w) // 2
        text_color = COLOR_GOLD if ("habermat" in sline.lower() or is_cta_screen) else COLOR_WHITE
        draw.text((x_sub + 3, y_sub + 3), sline, font=font_sub, fill=(0, 0, 0))
        draw.text((x_sub, y_sub), sline, font=font_sub, fill=text_color)
        y_sub += 66

    # 5. ALT GOOGLE ARAMA / CTA KARTI (Y: 1415 - 1775)
    cta_bg = COLOR_RED if is_cta_screen else COLOR_NAVY_MID
    cta_outline = COLOR_GOLD if is_cta_screen else COLOR_RED
    draw.rounded_rectangle(
        [50, 1415, 1030, 1775],
        radius=26,
        fill=cta_bg,
        outline=cta_outline,
        width=6 if is_cta_screen else 3,
    )

    draw.text(
        (100, 1445),
        "BAŞVURU ŞARTLARI VE DETAYLAR İÇİN:",
        font=font_footer,
        fill=COLOR_GOLD if not is_cta_screen else COLOR_WHITE,
    )

    # Google Arama Çubuğu
    draw.rounded_rectangle([90, 1505, 990, 1620], radius=45, fill=COLOR_WHITE)
    draw.text((135, 1532), "G", font=font_cta_box, fill=(66, 133, 244))
    draw.text((215, 1532), "habermat.com", font=font_cta_box, fill=(20, 20, 20))
    draw.rounded_rectangle([775, 1520, 970, 1605], radius=32, fill=COLOR_RED)
    draw.text((818, 1538), "ARA", font=font_cta_title, fill=COLOR_WHITE)

    draw.text(
        (105, 1658),
        "» Google'a yaz, çıkan İLK SİTEYE tıklayın!",
        font=font_cat,
        fill=COLOR_GOLD if is_cta_screen else COLOR_WHITE,
    )

    return img


def _get_audio_duration_ffprobe(audio_path: Path) -> float:
    """FFprobe ile ses dosyasının saniye cinsinden tam süresini alır."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return max(float(res.stdout.strip()), 0.4)
    except Exception:
        return 3.5


def _generate_news_bg_music(output_wav: Path, duration_sec: float, sample_rate: int = 44100) -> None:
    """Telifsiz, hafif ritmik kurumsal Haber Bülteni arka plan müziği üretir."""
    total_samples = int((duration_sec + 1.0) * sample_rate)
    with wave.open(str(output_wav), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for i in range(total_samples):
            t = i / sample_rate
            beat = (math.sin(2 * math.pi * 2.0 * t) + 1.0) * 0.5
            pulse_env = math.exp(-4.0 * ((t * 2.0) % 1.0))
            tone1 = math.sin(2 * math.pi * 110.0 * t) * 0.35
            tone2 = math.sin(2 * math.pi * 220.0 * t) * 0.25 * pulse_env
            tone3 = math.sin(2 * math.pi * 329.63 * t) * 0.15 * beat
            tick = math.sin(2 * math.pi * 880.0 * t) * math.exp(-28.0 * ((t * 4.0) % 1.0)) * 0.12

            sample_val = (tone1 + tone2 + tone3 + tick) * 0.16
            sample_int = max(-32767, min(32767, int(sample_val * 32767)))
            frames.extend(struct.pack("<h", sample_int))

        wav_file.writeframes(frames)


def _int_to_tr_words(n: int) -> str:
    """Tam sayıları doğal Türkçe okunuş metnine çevirir (Örn: 1071 -> bin yetmiş bir, 2026 -> iki bin yirmi altı)."""
    if n == 0:
        return "sıfır"
    ones = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
    tens = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]

    def _under_1000(val: int) -> str:
        parts = []
        h = val // 100
        rem = val % 100
        t = rem // 10
        o = rem % 10
        if h > 0:
            parts.append("yüz" if h == 1 else f"{ones[h]} yüz")
        if t > 0:
            parts.append(tens[t])
        if o > 0:
            parts.append(ones[o])
        return " ".join(parts)

    chunks = []
    billions = n // 1_000_000_000
    n %= 1_000_000_000
    millions = n // 1_000_000
    n %= 1_000_000
    thousands = n // 1_000
    rem = n % 1_000

    if billions > 0:
        chunks.append(f"{_under_1000(billions)} milyar")
    if millions > 0:
        chunks.append(f"{_under_1000(millions)} milyon")
    if thousands > 0:
        chunks.append("bin" if thousands == 1 else f"{_under_1000(thousands)} bin")
    if rem > 0:
        chunks.append(_under_1000(rem))

    return " ".join(chunks)


def normalize_tr_for_tts(text: str) -> str:
    """
    Yazılı Türkçe haber metnini, spikerin sıfır kesilme, sıfır cümle içi takılma
    ve kusursuz Türkçe telaffuzla tek nefeste okuyacağı fonetik metne dönüştürür.
    """
    import re

    s = text.strip()
    # Tüm farklı Unicode tire/kısa çizgi karakterlerini (\u2010-\u2015, \u2212) standart '-' yap
    s = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]", "-", s)

    # Tırnak işaretlerini ve parantezleri kaldır
    s = re.sub(r'[“”"«»()]', " ", s)

    # Şapkalı harfleri düzleştir
    s = (
        s.replace("â", "a")
        .replace("Â", "A")
        .replace("î", "i")
        .replace("Î", "İ")
        .replace("û", "u")
        .replace("Û", "U")
    )

    # iddaaliyiz.tv (motion_reels.py) ile birebir aynı doğal Türkçe metin hazırlama:
    # Kelimelerin orijinal Türkçe yazılışını, kesme işaretlerini (Ankara'da, Google'a)
    # ve doğal cümle vurgusunu (!, ., ,) KORUR; sadece kısaltmaları ve ondalık sayıları açar.
    replacements = [
        (r"\bhabermat\.com\b", "habermat nokta com"),
        (r"\be-Devlet\b", "e Devlet"),
        (r"\bBağ-Kur\b", "Bağkur"),
        (r"\bSYDV\b", "Sosyal Yardımlaşma Vakfı"),
        (r"\bKYK\b", "Kredi ve Yurtlar Kurumu"),
        (r"\bMEB\b", "Milli Eğitim Bakanlığı"),
    ]
    for pat, repl in replacements:
        s = re.sub(pat, repl, s, flags=re.IGNORECASE)

    # 1) Binlik ayraçlı tam sayıları birleştir (Örn: 35.000 -> 35 bin, 250.000 -> 250 bin, 1.071 -> 1071)
    s = re.sub(r"\b(\d{1,3})\.000\b", r"\1 bin", s)
    s = re.sub(r"\b(\d{1,3})\.(\d{3})\b", r"\1\2", s)

    # 2) Ondalıklı oranları iddaaliyiz.tv'deki gibi doğal okut (Örn: 0.99 -> 0 nokta 99)
    s = re.sub(r"\b(\d+)[.,](\d{1,2})\b", r"\1 nokta \2", s)

    # 3) Yüzde işaretini (%66 -> yüzde 66) çevir
    s = re.sub(r"%\s*(\d+)", r"yüzde \1", s)

    # Fazla boşlukları temizle ve cümle sonunda doğal vurgu işareti (! veya .) olmasını sağla
    s = re.sub(r"\s+", " ", s).strip()
    if s and s[-1] not in ".!?":
        s += "!"
    return s


def _try_external_professional_tts(full_text: str, out_mp3: Path) -> bool:
    """
    Öncelik sırasıyla:
    1) Google Vids / NotebookLM Stüdyo Sesi (GEMINI_API_KEY -> gemini-2.5-flash-preview-tts, Orus / Kore)
    2) ElevenLabs Multilingual v2 (ELEVENLABS_API_KEY)
    3) OpenAI Studio Audio (OPENAI_API_KEY -> gpt-4o-mini-tts)
    üzerinden tek parça stüdyo sesi üretir.
    """
    import base64
    import requests

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            voice_name = os.environ.get("GOOGLE_VIDS_VOICE", "Orus").strip()
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={gemini_key}",
                json={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": f"Türkçe televizyon haber ve spor spikeri gibi çok doğal, enerjik, akıcı ve kesintisiz bir erkek ses tonuyla sadece şu metni oku: {full_text}"
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {
                                    "voiceName": voice_name
                                }
                            }
                        },
                    },
                },
                timeout=40,
            )
            if resp.status_code == 200:
                data = resp.json()
                b64_pcm = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("inlineData", {})
                    .get("data", "")
                )
                if b64_pcm:
                    pcm_bytes = base64.b64decode(b64_pcm)
                    raw_wav = out_mp3.with_suffix(".gvid.wav")
                    with wave.open(str(raw_wav), "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(24000)
                        wf.writeframes(pcm_bytes)
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", str(raw_wav), "-ar", "44100", "-ac", "1", str(out_mp3)],
                        check=True,
                        capture_output=True,
                    )
                    raw_wav.unlink(missing_ok=True)
                    print(f"      [TTS] Google Vids / Gemini 2.5 Studio ({voice_name}) seslendirme kullanıldı.")
                    return True
        except Exception as exc:
            print(f"      [UYARI] Google Vids TTS hatası, yedek motora geçiliyor: {exc}")

    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if eleven_key:
        try:
            voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM").strip()
            resp = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": eleven_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": full_text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.55,
                        "similarity_boost": 0.80,
                        "style": 0.15,
                        "use_speaker_boost": True,
                    },
                },
                timeout=35,
            )
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(out_mp3, "wb") as f:
                    f.write(resp.content)
                print("      [TTS] ElevenLabs Multilingual v2 profesyonel seslendirme kullanıldı.")
                return True
        except Exception as exc:
            print(f"      [UYARI] ElevenLabs TTS hatası, yedek motora geçiliyor: {exc}")

    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_key:
        try:
            resp = requests.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini-tts",
                    "voice": os.environ.get("OPENAI_TTS_VOICE", "onyx"),
                    "input": full_text,
                    "instructions": "Türkçe televizyon haber spikeri gibi akıcı, enerjik ve doğal bir erkek tonlamasıyla oku.",
                },
                timeout=35,
            )
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(out_mp3, "wb") as f:
                    f.write(resp.content)
                print("      [TTS] OpenAI gpt-4o-mini-tts profesyonel seslendirme kullanıldı.")
                return True
        except Exception as exc:
            print(f"      [UYARI] OpenAI TTS hatası, yedek motora geçiliyor: {exc}")

    return False


async def _synthesize_full_script_single_stream(
    segments: List[Dict[str, Any]],
    out_mp3: Path,
) -> Tuple[List[float], List[List[Dict[str, Any]]]]:
    """
    IDDAALIYIZ.TV (motion_reels.py) İLE BİREBİR AYNI DOĞAL ERKEK SPİKER (tr-TR-AhmetNeural) VE AKIŞ MİMARİSİ:
    - Cümlelerin doğal Türkçe noktalama ve ünlem vurgularını (!, ., ,) koruyarak
      tr-TR-AhmetNeural erkek spiker sesiyle (hız ve ton bozulmadan, %0 rate/pitch) tek seferde okutur.
    - Kesilme yapan silenceremove veya sesi robotikleştiren compressor/equalizer filtreleri KULLANMAZ.
    """
    cleaned_clauses: List[str] = []
    clause_word_counts: List[int] = []

    for seg in segments:
        norm_clause = normalize_tr_for_tts(seg["spoken"])
        words = norm_clause.split()
        cleaned_clauses.append(norm_clause)
        clause_word_counts.append(max(len(words), 1))

    # Tıpkı iddaaliyiz.tv'deki IY_VOICEOVER_TEXT ve KRAL_ORAN_VOICEOVER gibi
    # doğal noktalama işaretli cümleleri tek paragrafta birleştir:
    full_phonetic_text = " ".join(cleaned_clauses)

    if _try_external_professional_tts(full_phonetic_text, out_mp3):
        total_dur = _get_audio_duration_ffprobe(out_mp3)
        total_words = sum(clause_word_counts)
        seg_durs = [total_dur * (wc / total_words) for wc in clause_word_counts]
        return seg_durs, [[] for _ in segments]

    last_err = None
    for attempt in range(10):
        try:
            # iddaaliyiz.tv motion_reels.py generate_tts ile birebir aynı çağrı (voice="tr-TR-AhmetNeural")
            communicate = edge_tts.Communicate(
                text=full_phonetic_text,
                voice=PRIMARY_TR_VOICE,
                boundary="WordBoundary",
            )
            all_word_events: List[Dict[str, Any]] = []
            audio_bytes = bytearray()

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes.extend(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    all_word_events.append(
                        {
                            "text": chunk["text"],
                            "offset_sec": chunk["offset"] / 10_000_000.0,
                            "duration_sec": chunk["duration"] / 10_000_000.0,
                        }
                    )

            if len(audio_bytes) > 1000:
                with open(out_mp3, "wb") as f:
                    f.write(audio_bytes)

                total_dur = _get_audio_duration_ffprobe(out_mp3)
                if all_word_events:
                    last_word_end = all_word_events[-1]["offset_sec"] + all_word_events[-1]["duration_sec"]
                    trimmed_total = min(total_dur, last_word_end + 0.35)
                else:
                    trimmed_total = total_dur

                seg_durations: List[float] = []
                seg_word_events: List[List[Dict[str, Any]]] = []
                total_expected_words = sum(clause_word_counts)
                total_actual_events = len(all_word_events)

                if total_actual_events >= len(segments):
                    start_ev_idx = 0
                    seg_start_times: List[float] = []
                    seg_event_slices: List[List[Dict[str, Any]]] = []

                    cum_expected = 0
                    for idx, wc in enumerate(clause_word_counts):
                        cum_expected += wc
                        end_ev_idx = min(
                            int(round(cum_expected * total_actual_events / total_expected_words)),
                            total_actual_events,
                        )
                        if idx == len(clause_word_counts) - 1:
                            end_ev_idx = total_actual_events
                        ev_slice = all_word_events[start_ev_idx:end_ev_idx]
                        if not ev_slice and start_ev_idx < total_actual_events:
                            ev_slice = [all_word_events[start_ev_idx]]
                        seg_event_slices.append(ev_slice)
                        if idx == 0:
                            seg_start_times.append(0.0)
                        elif ev_slice:
                            seg_start_times.append(ev_slice[0]["offset_sec"])
                        else:
                            seg_start_times.append(seg_start_times[-1] + 2.5)
                        start_ev_idx = end_ev_idx

                    for idx in range(len(segments)):
                        s_t = seg_start_times[idx]
                        e_t = seg_start_times[idx + 1] if idx < len(segments) - 1 else trimmed_total
                        dur = max(0.8, e_t - s_t)
                        seg_durations.append(dur)
                        shifted_events = [
                            {
                                "text": ev["text"],
                                "offset_sec": max(0.0, ev["offset_sec"] - s_t),
                                "duration_sec": ev["duration_sec"],
                            }
                            for ev in seg_event_slices[idx]
                        ]
                        seg_word_events.append(shifted_events)

                    return seg_durations, seg_word_events

                seg_durs = [trimmed_total * (wc / total_expected_words) for wc in clause_word_counts]
                return seg_durs, [[] for _ in segments]
        except Exception as exc:
            last_err = exc
        await asyncio.sleep(1.0 + attempt * 0.4)

    raise RuntimeError(f"Erkek spiker (tr-TR-AhmetNeural) seslendirmesi oluşturulamadı: {last_err}")


def _build_synced_subtitle_chunks(
    subtitle_text: str,
    word_events: List[Dict[str, Any]],
    segment_audio_duration: float,
    words_per_chunk: int = 4,
) -> List[Tuple[str, float]]:
    """
    Spikerin gerçek kelime okuma zamanlamalarını (WordBoundary) kullanarak
    altyazıyı 3-4 kelimelik gruplara böler ve her grubun ekranda kalacağı
    tam süreyi (spikerin o kelimeleri konuştuğu gerçek süreyi) hesaplar.
    """
    display_words = subtitle_text.strip().split()
    if not display_words:
        return [(subtitle_text, segment_audio_duration)]

    chunks_words: List[List[str]] = []
    for i in range(0, len(display_words), words_per_chunk):
        chunks_words.append(display_words[i : i + words_per_chunk])

    num_chunks = len(chunks_words)
    if num_chunks == 1:
        return [(" ".join(chunks_words[0]), segment_audio_duration)]

    if word_events and len(word_events) >= 2:
        total_spoken_words = len(word_events)
        chunk_start_times: List[float] = []

        for c_idx in range(num_chunks):
            ev_idx = min(
                int(round(c_idx * total_spoken_words / num_chunks)),
                total_spoken_words - 1,
            )
            start_t = word_events[ev_idx]["offset_sec"]
            chunk_start_times.append(start_t)

        chunk_start_times[0] = 0.0
        durations: List[float] = []
        for c_idx in range(num_chunks):
            if c_idx < num_chunks - 1:
                dur = max(0.35, chunk_start_times[c_idx + 1] - chunk_start_times[c_idx])
            else:
                dur = max(0.45, segment_audio_duration - sum(durations))
            durations.append(dur)

        sum_d = sum(durations)
        if sum_d > 0:
            scale = segment_audio_duration / sum_d
            durations = [d * scale for d in durations]

        return [(" ".join(chunks_words[i]), durations[i]) for i in range(num_chunks)]

    total_chars = max(sum(len(" ".join(cw)) for cw in chunks_words), 1)
    result: List[Tuple[str, float]] = []
    for cw in chunks_words:
        txt = " ".join(cw)
        dur = segment_audio_duration * (len(txt) / total_chars)
        result.append((txt, max(dur, 0.35)))
    return result


def generate_reels_video(
    package: Dict[str, Any],
    category: dict,
    work_dir: Path,
    output_mp4: Path,
    real_photos: Optional[List[Path]] = None,
) -> Path:
    """
    1) Tüm haber senaryosunu TEK BİR KESİNTİSİZ SES AKIŞI (Single-Stream) olarak seslendirir (kesilme ve ekleme izi %0).
    2) Haberle alakalı en az 3-4 gerçek dikey fotoğrafı slayt olarak döngüye sokar.
    3) Altyazıları spikerin gerçek konuşma hızına göre milisaniye hassasiyetinde ekrana getirir.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    segments = package.get("script_segments", [])
    if not segments:
        raise ValueError("Reels senaryo segmentleri boş!")

    photos_list: List[Path] = list(real_photos) if real_photos else []
    total_photos = max(len(photos_list), 1)

    # 1. Tüm metni parçalara bölmeden TEK BİR MP3 olarak kesintisiz seslendir
    full_voice_mp3 = work_dir / "full_voiceover.mp3"
    segment_durations, segment_word_events = asyncio.run(
        _synthesize_full_script_single_stream(segments, full_voice_mp3)
    )
    total_duration = sum(segment_durations)

    # 2. Sesi hiçbir compressor/gate/silenceremove kesintisine uğratmadan saf stüdyo AAC formatına çevir
    mixed_audio_aac = work_dir / "mixed_audio.m4a"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(full_voice_mp3),
            "-t",
            f"{total_duration:.3f}",
            "-af",
            "volume=1.45",
            "-ar",
            "44100",
            "-ac",
            "1",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(mixed_audio_aac),
        ],
        check=True,
        capture_output=True,
    )

    # 3. Spikerin kelime zamanlamalarına göre senkronize slaytları ve gerçek fotoğraf geçişlerini oluştur
    slide_entries: List[Tuple[Path, float]] = []
    elapsed = 0.0
    slide_counter = 0

    for idx, seg in enumerate(segments):
        seg_dur = segment_durations[idx]
        subtitle_full = seg["subtitle"]
        is_cta = bool(seg.get("is_cta", False))
        word_events = segment_word_events[idx]

        # Her segmentte farklı bir gerçek haber fotoğrafına geç (Slayt akışı: Fotoğraf 1 -> 2 -> 3 -> 4)
        current_photo_idx = idx % total_photos if photos_list else 0
        current_photo_path = photos_list[current_photo_idx] if photos_list else None

        synced_chunks = _build_synced_subtitle_chunks(
            subtitle_text=subtitle_full,
            word_events=word_events,
            segment_audio_duration=seg_dur,
            words_per_chunk=4,
        )

        for c_idx, (chunk_text, chunk_dur) in enumerate(synced_chunks):
            elapsed += chunk_dur
            progress_ratio = elapsed / max(total_duration, 1.0)
            # Her altyazı adımında fotoğrafa hafif sinematik zoom hareketi uygula (1.00 -> 1.03 -> 1.06)
            zoom_factor = 1.0 + (c_idx * 0.025)

            slide_img = _render_reels_slide(
                package=package,
                category=category,
                photo_path=current_photo_path,
                photo_index=current_photo_idx,
                total_photos=total_photos,
                zoom_factor=zoom_factor,
                subtitle_text=chunk_text,
                progress_ratio=progress_ratio,
                is_cta_screen=is_cta,
                slide_index=slide_counter,
            )
            slide_path = work_dir / f"slide_{slide_counter:03d}.png"
            slide_img.save(slide_path, format="PNG")
            slide_entries.append((slide_path, max(chunk_dur, 0.25)))
            slide_counter += 1

    # 5. FFmpeg ile slaytları ve sesi 1080x1920 30fps MP4 olarak render et
    video_concat_txt = work_dir / "video_concat.txt"
    with open(video_concat_txt, "w", encoding="utf-8") as f:
        for s_path, s_dur in slide_entries:
            safe_p = str(s_path.resolve()).replace("\\", "/")
            f.write(f"file '{safe_p}'\n")
            f.write(f"duration {s_dur:.4f}\n")
        last_p = str(slide_entries[-1][0].resolve()).replace("\\", "/")
        f.write(f"file '{last_p}'\n")

    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(video_concat_txt),
            "-i",
            str(mixed_audio_aac),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-c:a",
            "copy",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_mp4),
        ],
        check=True,
        capture_output=True,
    )

    return output_mp4
