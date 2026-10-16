"""
Habermat.com - 8 Ana Haber Kategorisi ve Saatlik Rotasyon Yapılandırması
Sabah 07:00 - Gece 24:00 (00:00) arası toplam 18 saatlik yayın akışı.
"""

from datetime import datetime, timezone, timedelta

# Türkiye saati (UTC+3)
TR_TZ = timezone(timedelta(hours=3))

CATEGORIES = [
    {
        "id": "devlet_yardimlari",
        "name": "Devlet Yardımları",
        "wp_slug": "devlet-yardimlari",
        "badge": "SON DAKİKA • DEVLET YARDIMI",
        "accent_color": (217, 4, 41),  # Kırmızı
        "rss_queries": [
            "Aile ve Sosyal Hizmetler Bakanlığı destek ödemesi başvuru",
            "e-Devlet sosyal yardım başvurusu ödemeleri",
            "SED yardımı doğum yardımı aile destek ödemesi",
        ],
        "fallback_topics": [
            "e-Devlet Üzerinden Sosyal Yardım Başvurusu ve PTT Destek Ödemeleri Sorgulama Rehberi",
            "Aile ve Sosyal Hizmetler Bakanlığı Dar Gelirli Hanelere Nakdi Destek Başvuru Şartları",
            "Çocuklu Ailelere SED ve Doğum Yardımı Ödemelerinde Güncel Başvuru Ekranı",
        ],
        "hashtags": ["#devletyardımı", "#sosyalyardım", "#edevlet", "#ailebakanlığı", "#desteködemesi", "#habermat"],
        "visual_keywords": "E-DEVLET DESTEK ÖDEMESİ",
    },
    {
        "id": "emeklilik",
        "name": "Emeklilik Haberleri",
        "wp_slug": "emeklilik-haberleri",
        "badge": "SON DAKİKA • EMEKLİ HABERİ",
        "accent_color": (217, 4, 41),
        "rss_queries": [
            "emekli maaşı promosyon ikramiye SGK son dakika",
            "SSK Bağ-Kur emekli ek ödeme banka promosyonu",
            "SGK emeklilik şartları emekli maaş zammı",
        ],
        "fallback_topics": [
            "SSK ve Bağ-Kur Emeklilerine Banka Promosyon Ödemelerinde Güncel Tutarlar ve Başvuru Şartları",
            "Emeklilere Ek Ödeme ve İkramiye Düzenlemesinde Kimler Ne Kadar Alacak?",
            "e-Devlet SGK Emekli Maaşı ve Ek Ödeme Sorgulama Ekranı Açıldı",
        ],
        "hashtags": ["#emekli", "#emeklimaaşı", "#emeklipromosyon", "#sgk", "#ssk", "#bağkur", "#habermat"],
        "visual_keywords": "EMEKLİYE YENİ ÖDEME",
    },
    {
        "id": "toki_konut",
        "name": "TOKİ ve Konut Haberleri",
        "wp_slug": "toki-haberleri",
        "badge": "SON DAKİKA • TOKİ DUYURUSU",
        "accent_color": (217, 4, 41),
        "rss_queries": [
            "TOKİ konut başvurusu kura sonuçları sosyal konut",
            "TOKİ ucuz konut arsa satışı başvuru şartları",
            "Çevre Şehircilik kira yardımı konut desteği",
        ],
        "fallback_topics": [
            "TOKİ Sosyal Konut ve Uygun Taksitli Ev Başvurularında Aranan Şartlar Nelerdir?",
            "Dar Gelirli Vatandaşlara TOKİ Konut ve Kira Desteği Başvuru Rehberi",
            "e-Devlet TOKİ Başvuru Ekranı ve Kura Sonuçları Sorgulama Adımları",
        ],
        "hashtags": ["#toki", "#tokikonut", "#sosyalkonut", "#kirayardımı", "#konutdesteği", "#edevlet", "#habermat"],
        "visual_keywords": "TOKİ KONUT DUYURUSU",
    },
    {
        "id": "belediye_yardimlari",
        "name": "Belediye Yardımları",
        "wp_slug": "belediye-yardimlari",
        "badge": "SOSYAL DESTEK • BELEDİYE",
        "accent_color": (217, 4, 41),
        "rss_queries": [
            "belediye sosyal yardım başvurusu destek kartı",
            "büyükşehir belediyesi nakdi yardım sosyal destek ödemesi",
            "belediye fatura desteği ulaşım yardımı başvurusu",
        ],
        "fallback_topics": [
            "Büyükşehir ve İlçe Belediyeleri Sosyal Destek Kartı Başvurusu Nasıl Yapılır?",
            "Belediyelerden Dar Gelirli Ailelere Nakdi Yardım ve Fatura Desteği Başvuru Şartları",
            "e-Devlet Belediye Sosyal Yardım Başvuru Formu ve Sorgulama Ekranı",
        ],
        "hashtags": ["#belediyeyardımı", "#sosyaldestek", "#destekkartı", "#sosyalyardım", "#nakdiyardım", "#habermat"],
        "visual_keywords": "BELEDİYE DESTEK KARTI",
    },
    {
        "id": "kirtasiye_egitim",
        "name": "Kırtasiye ve Eğitim Yardımları",
        "wp_slug": "egitim-yardimlari",
        "badge": "EĞİTİM • KIRTASİYE DESTEĞİ",
        "accent_color": (217, 4, 41),
        "rss_queries": [
            "kırtasiye yardımı eğitim desteği öğrenci yardımı başvurusu",
            "öğrencilere burs eğitim yardımı e-Devlet başvuru",
            "belediye bakanlık kırtasiye kantin eğitim desteği",
        ],
        "fallback_topics": [
            "Öğrencilere Kırtasiye ve Eğitim Yardımı Ödemesi Başvurusu e-Devlet'ten Nasıl Yapılır?",
            "İlkokul, Ortaokul ve Lise Öğrencilerine Eğitim Desteği Başvuru Şartları",
            "Ailelere Kırtasiye, Kantin ve Öğrenci Ulaşım Desteği Ödemelerinde Güncel Detaylar",
        ],
        "hashtags": ["#kırtasiyeyardımı", "#eğitimdesteği", "#öğrenciburs", "#edevlet", "#sosyalyardım", "#habermat"],
        "visual_keywords": "KIRTASİYE VE EĞİTİM DESTEĞİ",
    },
    {
        "id": "erzak_gida",
        "name": "Erzak ve Gıda Yardımları",
        "wp_slug": "gida-yardimlari",
        "badge": "SOSYAL YARDIM • GIDA DESTEĞİ",
        "accent_color": (217, 4, 41),
        "rss_queries": [
            "gıda yardımı erzak kolisi başvurusu sosyal yardımlaşma",
            "market kartı gıda desteği başvurusu e-Devlet",
            "Vakıflar Genel Müdürlüğü kuru gıda erzak yardımı",
        ],
        "fallback_topics": [
            "e-Devlet Gıda ve Erzak Yardımı Başvurusu: Sosyal Yardımlaşma Market Kartı Şartları",
            "Vakıflar Genel Müdürlüğü ve Belediyelerden Kuru Gıda Kolisi Yardımı Başvuru Ekranı",
            "İhtiyaç Sahibi Ailelere Aylık Gıda ve Market Destek Kartı Başvurusu Nasıl Yapılır?",
        ],
        "hashtags": ["#erzakyardımı", "#gıdayardımı", "#marketkartı", "#sosyalyardım", "#edevlet", "#habermat"],
        "visual_keywords": "ERZAK VE GIDA YARDIMI",
    },
    {
        "id": "kiyafet_yakacak",
        "name": "Kıyafet ve Yakacak Yardımları",
        "wp_slug": "kiyafet-yakacak-yardimlari",
        "badge": "DESTEK PAKETİ • GİYİM & YAKACAK",
        "accent_color": (217, 4, 41),
        "rss_queries": [
            "doğalgaz tüketim desteği yakacak kömür yardımı başvurusu",
            "kışlık giyim kıyafet yardımı elektrik faturası desteği",
            "e-Devlet ısınma doğalgaz yardımı başvurusu",
        ],
        "fallback_topics": [
            "Ailelere Kıyafet, Bot-Mont ve Yakacak Yardımı Başvurusu e-Devlet Ekranı",
            "Doğalgaz Tüketim Desteği ve Kömür Yardımı Başvuru Şartları Açıklandı",
            "Dar Gelirli Hanelere Giyim Kartı ve Isınma Faturası Desteği Nasıl Alınır?",
        ],
        "hashtags": ["#kıyafetyardımı", "#yakacakyardımı", "#doğalgazdesteği", "#kömüryardımı", "#sosyalyardım", "#habermat"],
        "visual_keywords": "KIYAFET VE YAKACAK DESTEĞİ",
    },
    {
        "id": "kredi_banka",
        "name": "Kredi ve Banka Haberleri",
        "wp_slug": "kredi-haberleri",
        "badge": "SON DAKİKA • KREDİ & FİNANS",
        "accent_color": (217, 4, 41),
        "rss_queries": [
            "faizsiz kredi devlet destekli kredi başvurusu kamu bankaları",
            "Ziraat Bankası Vakıfbank Halkbank destek kredisi kampanyası",
            "evlilik kredisi ihtiyaç kredisi faizsiz destek",
        ],
        "fallback_topics": [
            "Kamu Bankalarından Vatandaşlara Düşük Faizli ve Ertelemeli Destek Kredisi Başvuru Şartları",
            "Devlet Destekli Faizsiz Kredi Başvurusu Kimlere Veriliyor? e-Devlet Başvuru Adımları",
            "Ziraat Bankası, VakıfBank ve Halkbank Yeni Nakit Destek Kampanyası Detayları",
        ],
        "hashtags": ["#kredi", "#faizsizkredi", "#destekkredisi", "#ziraatbankası", "#vakıfbank", "#halkbank", "#habermat"],
        "visual_keywords": "DEVLET DESTEKLİ KREDİ",
    },
]

# 07:00 - 24:00 (00:00) arası 18 saatlik yayın çizelgesi.
# 8 kategorinin tamamı günde en az 2 kez döner, en yoğun aranan (Devlet Yardımı & Emeklilik) 3 kez yer alır.
HOURLY_SCHEDULE = {
    7: "emeklilik",
    8: "devlet_yardimlari",
    9: "toki_konut",
    10: "belediye_yardimlari",
    11: "kirtasiye_egitim",
    12: "kredi_banka",
    13: "erzak_gida",
    14: "kiyafet_yakacak",
    15: "devlet_yardimlari",
    16: "emeklilik",
    17: "toki_konut",
    18: "kredi_banka",
    19: "belediye_yardimlari",
    20: "kirtasiye_egitim",
    21: "erzak_gida",
    22: "kiyafet_yakacak",
    23: "devlet_yardimlari",
    0: "emeklilik",
}


def get_category_for_current_hour(override_category_id: str = None) -> dict:
    """
    Verilen kategori ID'sine veya Türkiye saatine (07:00 - 00:00) göre
    sıradaki kategoriyi döndürür.
    """
    if override_category_id:
        for cat in CATEGORIES:
            if cat["id"] == override_category_id or cat["wp_slug"] == override_category_id:
                return cat

    now_tr = datetime.now(TR_TZ)
    current_hour = now_tr.hour
    target_id = HOURLY_SCHEDULE.get(current_hour)

    if not target_id:
        # Eğer 01:00 - 06:00 arasında manuel tetiklenirse saate göre mod al
        target_id = CATEGORIES[current_hour % len(CATEGORIES)]["id"]

    for cat in CATEGORIES:
        if cat["id"] == target_id:
            return cat

    return CATEGORIES[0]
