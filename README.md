# Habermat.com — Saatlik WordPress SEO Haber + Instagram Reels Otomasyonu

Sabah **07:00** ile gece **24:00 (00:00)** arasında **her saat başı (günde 18 kez)** otomatik olarak:
1. Sıradaki kategoriye göre (**Devlet Yardımları, Emeklilik, TOKİ, Belediye Yardımları, Kırtasiye/Eğitim, Erzak/Gıda, Kıyafet/Yakacak, Kredi/Banka**) en güncel haberi Google News RSS üzerinden bulur.
2. **Google Gemini AI** ile:
   - **WordPress (`habermat.com`)** için Google Keşfet ve SEO uyumlu, alt başlıklı (`H2/H3`), Sıkça Sorulan Sorular içeren **450-600 kelimelik özgün makale** yazar.
   - **Instagram Reels** için ilk 3 saniyesi merak uyandıran (*"e-Devlet'ten yeni destek ödemesi başladı! Kimler başvurabilir?"* tarzı) **20-30 saniyelik spiker senaryosu** üretir.
3. **Görsel ve Sesli/Altyazılı Video Üretimi:**
   - **WordPress Öne Çıkan Görseli (`1200x675` - 16:9 Google Keşfet standardı):** Kırmızı - Beyaz - Koyu Lacivert Haber TV temasında hazırlanır.
   - **Reels Videosu (`1080x1920` - 9:16 Dikey MP4):**
     - `Edge-TTS` **Erkek Haber Spikeri (Ahmet)** seslendirmesi,
     - Sesle birebir senkronize **dinamik altyazı**,
     - Telifsiz kurumsal haber bülteni arka plan fon müziği,
     - Her videonun sonunda hem sesli hem de ekranda Google arama çubuğu görseliyle:
       > **"Başvuru şartları ve detayları için Google'a habermat.com yaz, çıkan ilk siteye tıklayın!"** çağrısı yer alır.
4. **Tam Otomatik Yayınlama:**
   - WordPress REST API ile haberi ilgili kategoriye doğrudan yayınlar (`publish`).
   - Instagram Graph API ile Reels videosunu otomatik paylaşır.

---

## Saatlik Kategori Yayın Akışı (07:00 – 24:00)

| Saat (TR) | Kategori | Saat (TR) | Kategori |
| :--- | :--- | :--- | :--- |
| **07:00** | Emeklilik Haberleri | **16:00** | Emeklilik Haberleri |
| **08:00** | Devlet Yardımları | **17:00** | TOKİ ve Konut Haberleri |
| **09:00** | TOKİ ve Konut Haberleri | **18:00** | Kredi ve Banka Haberleri |
| **10:00** | Belediye Yardımları | **19:00** | Belediye Yardımları |
| **11:00** | Kırtasiye ve Eğitim Yardımları | **20:00** | Kırtasiye ve Eğitim Yardımları |
| **12:00** | Kredi ve Banka Haberleri | **21:00** | Erzak ve Gıda Yardımları |
| **13:00** | Erzak ve Gıda Yardımları | **22:00** | Kıyafet ve Yakacak Yardımları |
| **14:00** | Kıyafet ve Yakacak Yardımları | **23:00** | Devlet Yardımları |
| **15:00** | Devlet Yardımları | **00:00** | Emeklilik Haberleri |

---

## GitHub Actions Kurulumu (Adım Adım)

### 1. WordPress Uygulama Şifresi (Application Password) Alma
Ekstra hiçbir eklenti kurmanıza gerek yoktur:
1. `habermat.com/wp-admin` paneline giriş yapın.
2. Sol menüden **Kullanıcılar -> Profil** sayfasına girin.
3. Sayfanın alt kısmındaki **Uygulama Şifreleri (Application Passwords)** bölümüne gelin.
4. Yeni uygulama şifresi adına `HabermatBot` yazıp **Yeni Uygulama Şifresi Ekle** butonuna tıklayın.
5. Ekranda verilen `xxxx xxxx xxxx xxxx xxxx xxxx` biçimindeki şifreyi kopyalayın.

### 2. GitHub Secrets Tanımlama
GitHub reponuzda **Settings -> Secrets and variables -> Actions -> New repository secret** kısmına şu 6 değişkeni ekleyin:

| Secret Adı | Açıklama |
| :--- | :--- |
| `GEMINI_API_KEY` | Google AI Studio'dan alınan ücretsiz Gemini API anahtarı |
| `WP_URL` | `https://habermat.com` |
| `WP_USERNAME` | WordPress yönetici/editör kullanıcı adınız |
| `WP_APP_PASSWORD` | 1. adımda aldığınız WordPress Uygulama Şifresi |
| `IG_USER_ID` | Instagram Business / Creator Hesap ID'niz (`178414...`) |
| `IG_ACCESS_TOKEN` | Instagram Graph API uzun ömürlü Access Token |

### 3. Yerel Test (Paylaşım Yapmadan Önizleme Üretme)
Bilgisayarınızda örnek kapak görselini ve sesli/altyazılı Reels videosunu test etmek için:
```bash
pip install -r requirements.txt
python main.py --dry-run
```
Üretilen dosyalar `output/featured_image.jpg` ve `output/reels_video.mp4` içine kaydedilir.
