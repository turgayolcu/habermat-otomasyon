"""
Habermat.com - Türkiye'nin 30 Büyükşehir Belediyesi ve İlçe Belediyeleri Sosyal Yardım Kategorileri
30 Büyükşehir İli:
Adana, Ankara, Antalya, Aydın, Balıkesir, Bursa, Denizli, Diyarbakır, Erzurum, Eskişehir,
Gaziantep, Hatay, İstanbul, İzmir, Kahramanmaraş, Kayseri, Kocaeli, Konya, Malatya, Manisa,
Mardin, Mersin, Muğla, Ordu, Sakarya, Samsun, Şanlıurfa, Tekirdağ, Trabzon, Van.

Sabah 07:00 - Gece 24:00 (00:00) arası toplam 18 saatlik yayın akışı.
Her saat başı sıradaki Büyükşehir ilinin hem Büyükşehir hem de İlçe Belediyelerinin verdiği
gerçek sosyal yardımlar, destekler ve başvurular araştırılıp paylaşılır.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Türkiye saati (UTC+3)
TR_TZ = timezone(timedelta(hours=3))
HISTORY_FILE = Path(__file__).resolve().parent.parent / "data" / "published_history.json"


def _make_city_category(
    city_id: str,
    city_name: str,
    slug_prefix: str,
    districts: list[str],
    extra_queries: list[str] | None = None,
    extra_hashtags: list[str] | None = None,
) -> dict:
    upper_city = city_name.replace("i", "İ").replace("ı", "I").upper()
    d1 = districts[1] if len(districts) > 1 else f"{city_name} Büyükşehir Belediyesi"
    d2 = districts[2] if len(districts) > 2 else d1
    d3 = districts[3] if len(districts) > 3 else d2
    d4 = districts[4] if len(districts) > 4 else d3

    rss_queries = [
        f"{city_name} Büyükşehir Belediyesi sosyal yardım destek ödemesi başvuru",
        f"{d1} {d2} sosyal yardım gıda nakdi destek kartı başvurusu",
        f"{d3} {d4} öğrenci emekli aile sosyal destek yardımı",
        f"{city_name} belediye sosyal yardım kartı erzak kırtasiye desteği başvuru",
    ]
    if extra_queries:
        rss_queries = extra_queries + rss_queries[:2]

    fallback_topics = [
        f"{city_name} Büyükşehir Belediyesi Sosyal Yardım Kartı, Gıda ve Nakdi Destek Başvurusu",
        f"{city_name} {d1} ve {d2} Dar Gelirli Ailelere Sosyal Destek ve Erzak Yardımı",
        f"{city_name} Büyükşehir Belediyesi Emekli, Öğrenci Eğitim ve Kırtasiye Desteği",
        f"{city_name} {d3} ve {d4} Sosyal Market, Sıcak Yemek ve Hoş Geldin Bebek Desteği",
    ]

    base_hashtags = [f"#{slug_prefix.replace('-', '')}", "#belediyeyardımı", "#sosyaldestek", "#başvuru", "#habermat"]
    if extra_hashtags:
        hashtags = list(dict.fromkeys(extra_hashtags + base_hashtags))
    else:
        hashtags = base_hashtags

    return {
        "id": city_id,
        "city": city_name,
        "name": f"{city_name} Belediye Yardımları",
        "wp_slug": f"{slug_prefix}-belediye-yardimlari",
        "badge": f"{upper_city} • BELEDİYE DESTEĞİ",
        "accent_color": (217, 4, 41),
        "districts": districts,
        "rss_queries": rss_queries,
        "fallback_topics": fallback_topics,
        "hashtags": hashtags,
        "visual_keywords": f"{upper_city} BELEDİYE YARDIMI",
    }


CATEGORIES = [
    _make_city_category(
        "adana_belediye",
        "Adana",
        "adana",
        [
            "Adana Büyükşehir Belediyesi", "Seyhan Belediyesi", "Yüreğir Belediyesi",
            "Çukurova Belediyesi", "Sarıçam Belediyesi", "Ceyhan Belediyesi",
            "Kozan Belediyesi", "İmamoğlu Belediyesi", "Karataş Belediyesi",
            "Karaisalı Belediyesi", "Pozantı Belediyesi", "Yumurtalık Belediyesi",
        ],
        extra_hashtags=["#adana", "#seyhan", "#yüreğir", "#çukurova", "#sarıçam"],
    ),
    _make_city_category(
        "ankara_belediye",
        "Ankara",
        "ankara",
        [
            "Ankara Büyükşehir Belediyesi", "Çankaya Belediyesi", "Keçiören Belediyesi",
            "Yenimahalle Belediyesi", "Mamak Belediyesi", "Etimesgut Belediyesi",
            "Sincan Belediyesi", "Altındağ Belediyesi", "Pursaklar Belediyesi",
            "Gölbaşı Belediyesi", "Polatlı Belediyesi", "Çubuk Belediyesi",
            "Kahramankazan Belediyesi", "Beypazarı Belediyesi", "Elmadağ Belediyesi",
        ],
        extra_queries=[
            "Ankara Büyükşehir Belediyesi Başkent Kart sosyal yardım emekli et doğalgaz desteği",
            "Çankaya Keçiören Yenimahalle Mamak Sincan Belediyesi sosyal yardım başvurusu",
        ],
        extra_hashtags=["#ankara", "#başkentkart", "#çankaya", "#keçiören", "#mamak", "#sincan"],
    ),
    _make_city_category(
        "antalya_belediye",
        "Antalya",
        "antalya",
        [
            "Antalya Büyükşehir Belediyesi", "Kepez Belediyesi", "Muratpaşa Belediyesi",
            "Alanya Belediyesi", "Manavgat Belediyesi", "Konyaaltı Belediyesi",
            "Serik Belediyesi", "Aksu Belediyesi", "Kumluca Belediyesi",
            "Döşemealtı Belediyesi", "Kaş Belediyesi", "Korkuteli Belediyesi",
            "Gazipaşa Belediyesi", "Finike Belediyesi", "Kemer Belediyesi",
        ],
        extra_hashtags=["#antalya", "#kepez", "#muratpaşa", "#alanya", "#manavgat", "#konyaaltı"],
    ),
    _make_city_category(
        "aydin_belediye",
        "Aydın",
        "aydin",
        [
            "Aydın Büyükşehir Belediyesi", "Efeler Belediyesi", "Nazilli Belediyesi",
            "Söke Belediyesi", "Kuşadası Belediyesi", "Didim Belediyesi",
            "İncirliova Belediyesi", "Çine Belediyesi", "Germencik Belediyesi",
            "Bozdoğan Belediyesi", "Köşk Belediyesi", "Kuyucak Belediyesi", "Sultanhisar Belediyesi",
        ],
        extra_hashtags=["#aydın", "#efeler", "#nazilli", "#söke", "#kuşadası", "#didim"],
    ),
    _make_city_category(
        "balikesir_belediye",
        "Balıkesir",
        "balikesir",
        [
            "Balıkesir Büyükşehir Belediyesi", "Karesi Belediyesi", "Altıeylül Belediyesi",
            "Edremit Belediyesi", "Bandırma Belediyesi", "Gönen Belediyesi",
            "Ayvalık Belediyesi", "Burhaniye Belediyesi", "Bigadiç Belediyesi",
            "Susurluk Belediyesi", "Dursunbey Belediyesi", "Sındırgı Belediyesi",
        ],
        extra_queries=[
            "Balıkesir Büyükşehir Belediyesi Yakın Kart sosyal yardım emekli öğrenci desteği",
            "Karesi Belediyesi Altıeylül Belediyesi Edremit Bandırma Belediyesi sosyal yardım başvurusu",
        ],
        extra_hashtags=["#balıkesir", "#karesi", "#altıeylül", "#bandırma", "#edremit"],
    ),
    _make_city_category(
        "bursa_belediye",
        "Bursa",
        "bursa",
        [
            "Bursa Büyükşehir Belediyesi", "Osmangazi Belediyesi", "Yıldırım Belediyesi",
            "Nilüfer Belediyesi", "İnegöl Belediyesi", "Gemlik Belediyesi",
            "Mustafakemalpaşa Belediyesi", "Mudanya Belediyesi", "Gürsu Belediyesi",
            "Kestel Belediyesi", "Karacabey Belediyesi", "Orhangazi Belediyesi",
            "Yenişehir Belediyesi", "İznik Belediyesi",
        ],
        extra_queries=[
            "Bursa Büyükşehir Belediyesi Kart16 sosyal yardım emekli öğrenci desteği",
            "Osmangazi Yıldırım Nilüfer İnegöl Gemlik Belediyesi sosyal yardım başvurusu",
        ],
        extra_hashtags=["#bursa", "#osmangazi", "#yıldırım", "#nilüfer", "#inegöl"],
    ),
    _make_city_category(
        "denizli_belediye",
        "Denizli",
        "denizli",
        [
            "Denizli Büyükşehir Belediyesi", "Pamukkale Belediyesi", "Merkezefendi Belediyesi",
            "Çivril Belediyesi", "Acıpayam Belediyesi", "Tavas Belediyesi",
            "Honaz Belediyesi", "Sarayköy Belediyesi", "Buldan Belediyesi",
            "Kale Belediyesi", "Çal Belediyesi", "Serinhisar Belediyesi",
        ],
        extra_hashtags=["#denizli", "#pamukkale", "#merkezefendi", "#çivril", "#acıpayam"],
    ),
    _make_city_category(
        "diyarbakir_belediye",
        "Diyarbakır",
        "diyarbakir",
        [
            "Diyarbakır Büyükşehir Belediyesi", "Bağlar Belediyesi", "Kayapınar Belediyesi",
            "Yenişehir Belediyesi", "Sur Belediyesi", "Ergani Belediyesi",
            "Bismil Belediyesi", "Silvan Belediyesi", "Çınar Belediyesi",
            "Çermik Belediyesi", "Dicle Belediyesi", "Kulp Belediyesi",
        ],
        extra_hashtags=["#diyarbakır", "#bağlar", "#kayapınar", "#sur", "#ergani"],
    ),
    _make_city_category(
        "erzurum_belediye",
        "Erzurum",
        "erzurum",
        [
            "Erzurum Büyükşehir Belediyesi", "Yakutiye Belediyesi", "Palandöken Belediyesi",
            "Aziziye Belediyesi", "Horasan Belediyesi", "Oltu Belediyesi",
            "Pasinler Belediyesi", "Karayazı Belediyesi", "Hınıs Belediyesi",
            "Aşkale Belediyesi", "İspir Belediyesi", "Tortum Belediyesi",
        ],
        extra_hashtags=["#erzurum", "#yakutiye", "#palandöken", "#aziziye", "#oltu"],
    ),
    _make_city_category(
        "eskisehir_belediye",
        "Eskişehir",
        "eskisehir",
        [
            "Eskişehir Büyükşehir Belediyesi", "Odunpazarı Belediyesi", "Tepebaşı Belediyesi",
            "Sivrihisar Belediyesi", "Çifteler Belediyesi", "Seyitgazi Belediyesi",
            "Alpu Belediyesi", "Mihalıççık Belediyesi", "Mahmudiye Belediyesi", "İnönü Belediyesi",
        ],
        extra_hashtags=["#eskişehir", "#odunpazarı", "#tepebaşı", "#sivrihisar"],
    ),
    _make_city_category(
        "gaziantep_belediye",
        "Gaziantep",
        "gaziantep",
        [
            "Gaziantep Büyükşehir Belediyesi", "Şahinbey Belediyesi", "Şehitkamil Belediyesi",
            "Nizip Belediyesi", "İslahiye Belediyesi", "Nurdağı Belediyesi",
            "Oğuzeli Belediyesi", "Araban Belediyesi", "Yavuzeli Belediyesi", "Karkamış Belediyesi",
        ],
        extra_queries=[
            "Şahinbey Belediyesi Şehitkamil Belediyesi sosyal yardım destek ödemesi başvuru",
            "Gaziantep Büyükşehir Belediyesi sosyal yardım başvurusu emekli öğrenci gıda",
        ],
        extra_hashtags=["#gaziantep", "#şahinbey", "#şehitkamil", "#nizip", "#islahiye"],
    ),
    _make_city_category(
        "hatay_belediye",
        "Hatay",
        "hatay",
        [
            "Hatay Büyükşehir Belediyesi", "Antakya Belediyesi", "İskenderun Belediyesi",
            "Defne Belediyesi", "Dörtyol Belediyesi", "Samandağ Belediyesi",
            "Kırıkhan Belediyesi", "Reyhanlı Belediyesi", "Arsuz Belediyesi",
            "Payas Belediyesi", "Erzin Belediyesi", "Hassa Belediyesi", "Altınözü Belediyesi",
        ],
        extra_hashtags=["#hatay", "#antakya", "#iskenderun", "#defne", "#dörtyol"],
    ),
    _make_city_category(
        "istanbul_belediye",
        "İstanbul",
        "istanbul",
        [
            "İstanbul Büyükşehir Belediyesi", "Esenyurt Belediyesi", "Küçükçekmece Belediyesi",
            "Bağcılar Belediyesi", "Ümraniye Belediyesi", "Pendik Belediyesi",
            "Bahçelievler Belediyesi", "Sultangazi Belediyesi", "Üsküdar Belediyesi",
            "Maltepe Belediyesi", "Gaziosmanpaşa Belediyesi", "Kadıköy Belediyesi",
            "Kartal Belediyesi", "Başakşehir Belediyesi", "Esenler Belediyesi",
            "Avcılar Belediyesi", "Kağıthane Belediyesi", "Fatih Belediyesi",
            "Sancaktepe Belediyesi", "Ataşehir Belediyesi", "Eyüpsultan Belediyesi",
            "Beylikdüzü Belediyesi", "Sarıyer Belediyesi", "Sultanbeyli Belediyesi",
            "Zeytinburnu Belediyesi", "Şişli Belediyesi", "Güngören Belediyesi",
            "Arnavutköy Belediyesi", "Tuzla Belediyesi", "Çekmeköy Belediyesi",
            "Büyükçekmece Belediyesi", "Beykoz Belediyesi", "Beyoğlu Belediyesi",
            "Bakırköy Belediyesi", "Silivri Belediyesi",
        ],
        extra_queries=[
            "İstanbul Büyükşehir Belediyesi İBB sosyal yardım İstanbulkart emekli pazar desteği",
            "Esenyurt Küçükçekmece Bağcılar Ümraniye Pendik Üsküdar Belediyesi sosyal yardım başvurusu",
        ],
        extra_hashtags=["#istanbul", "#ibb", "#esenyurt", "#üsküdar", "#ümraniye", "#pendik"],
    ),
    _make_city_category(
        "izmir_belediye",
        "İzmir",
        "izmir",
        [
            "İzmir Büyükşehir Belediyesi", "Buca Belediyesi", "Karabağlar Belediyesi",
            "Bornova Belediyesi", "Konak Belediyesi", "Karşıyaka Belediyesi",
            "Bayraklı Belediyesi", "Çiğli Belediyesi", "Torbalı Belediyesi",
            "Menemen Belediyesi", "Gaziemir Belediyesi", "Ödemiş Belediyesi",
            "Kemalpaşa Belediyesi", "Bergama Belediyesi", "Aliağa Belediyesi",
            "Menderes Belediyesi", "Tire Belediyesi", "Balçova Belediyesi",
            "Narlıdere Belediyesi", "Urla Belediyesi", "Çeşme Belediyesi", "Seferihisar Belediyesi",
        ],
        extra_hashtags=["#izmir", "#buca", "#karabağlar", "#bornova", "#konak", "#karşıyaka"],
    ),
    _make_city_category(
        "kahramanmaras_belediye",
        "Kahramanmaraş",
        "kahramanmaras",
        [
            "Kahramanmaraş Büyükşehir Belediyesi", "Onikişubat Belediyesi", "Dulkadiroğlu Belediyesi",
            "Elbistan Belediyesi", "Afşin Belediyesi", "Türkoğlu Belediyesi",
            "Pazarcık Belediyesi", "Göksun Belediyesi", "Andırın Belediyesi", "Çağlayancerit Belediyesi",
        ],
        extra_queries=[
            "Kahramanmaraş Büyükşehir Belediyesi Derman Kart sosyal yardım başvurusu",
            "Onikişubat Belediyesi Dulkadiroğlu Belediyesi Elbistan Afşin sosyal yardım desteği",
        ],
        extra_hashtags=["#kahramanmaraş", "#onikişubat", "#dulkadiroğlu", "#elbistan", "#afşin"],
    ),
    _make_city_category(
        "kayseri_belediye",
        "Kayseri",
        "kayseri",
        [
            "Kayseri Büyükşehir Belediyesi", "Melikgazi Belediyesi", "Kocasinan Belediyesi",
            "Talas Belediyesi", "Develi Belediyesi", "Yahyalı Belediyesi",
            "Bünyan Belediyesi", "İncesu Belediyesi", "Pınarbaşı Belediyesi",
            "Tomarza Belediyesi", "Yeşilhisar Belediyesi", "Hacılar Belediyesi",
        ],
        extra_hashtags=["#kayseri", "#melikgazi", "#kocasinan", "#talas", "#develi"],
    ),
    _make_city_category(
        "kocaeli_belediye",
        "Kocaeli",
        "kocaeli",
        [
            "Kocaeli Büyükşehir Belediyesi", "Gebze Belediyesi", "İzmit Belediyesi",
            "Darıca Belediyesi", "Körfez Belediyesi", "Gölcük Belediyesi",
            "Derince Belediyesi", "Çayırova Belediyesi", "Kartepe Belediyesi",
            "Başiskele Belediyesi", "Karamürsel Belediyesi", "Kandıra Belediyesi", "Dilovası Belediyesi",
        ],
        extra_queries=[
            "Kocaeli Büyükşehir Belediyesi 41 Kart sosyal yardım emekli öğrenci süt desteği",
            "Gebze Belediyesi İzmit Belediyesi Darıca Körfez Gölcük sosyal yardım başvurusu",
        ],
        extra_hashtags=["#kocaeli", "#izmit", "#gebze", "#darıca", "#körfez", "#gölcük"],
    ),
    _make_city_category(
        "konya_belediye",
        "Konya",
        "konya",
        [
            "Konya Büyükşehir Belediyesi", "Selçuklu Belediyesi", "Meram Belediyesi",
            "Karatay Belediyesi", "Ereğli Belediyesi", "Akşehir Belediyesi",
            "Beyşehir Belediyesi", "Çumra Belediyesi", "Seydişehir Belediyesi",
            "Ilgın Belediyesi", "Cihanbeyli Belediyesi", "Kulu Belediyesi", "Karapınar Belediyesi",
        ],
        extra_queries=[
            "Konya Büyükşehir Belediyesi Sosyal Kart eğitim emekli gıda yardımı başvurusu",
            "Selçuklu Belediyesi Meram Belediyesi Karatay Belediyesi sosyal destek başvurusu",
        ],
        extra_hashtags=["#konya", "#selçuklu", "#meram", "#karatay", "#ereğli"],
    ),
    _make_city_category(
        "malatya_belediye",
        "Malatya",
        "malatya",
        [
            "Malatya Büyükşehir Belediyesi", "Yeşilyurt Belediyesi", "Battalgazi Belediyesi",
            "Doğanşehir Belediyesi", "Akçadağ Belediyesi", "Darende Belediyesi",
            "Hekimhan Belediyesi", "Yazıhan Belediyesi", "Pütürge Belediyesi", "Arapgir Belediyesi",
        ],
        extra_hashtags=["#malatya", "#yeşilyurt", "#battalgazi", "#doğanşehir", "#akçadağ"],
    ),
    _make_city_category(
        "manisa_belediye",
        "Manisa",
        "manisa",
        [
            "Manisa Büyükşehir Belediyesi", "Yunusemre Belediyesi", "Şehzadeler Belediyesi",
            "Akhisar Belediyesi", "Turgutlu Belediyesi", "Salihli Belediyesi",
            "Soma Belediyesi", "Alaşehir Belediyesi", "Saruhanlı Belediyesi",
            "Kula Belediyesi", "Kırkağaç Belediyesi", "Demirci Belediyesi",
        ],
        extra_hashtags=["#manisa", "#yunusemre", "#şehzadeler", "#akhisar", "#turgutlu", "#salihli"],
    ),
    _make_city_category(
        "mardin_belediye",
        "Mardin",
        "mardin",
        [
            "Mardin Büyükşehir Belediyesi", "Kızıltepe Belediyesi", "Artuklu Belediyesi",
            "Midyat Belediyesi", "Nusaybin Belediyesi", "Derik Belediyesi",
            "Mazıdağı Belediyesi", "Dargeçit Belediyesi", "Savur Belediyesi", "Yeşilli Belediyesi",
        ],
        extra_hashtags=["#mardin", "#kızıltepe", "#artuklu", "#midyat", "#nusaybin"],
    ),
    _make_city_category(
        "mersin_belediye",
        "Mersin",
        "mersin",
        [
            "Mersin Büyükşehir Belediyesi", "Akdeniz Belediyesi", "Toroslar Belediyesi",
            "Yenişehir Belediyesi", "Mezitli Belediyesi", "Tarsus Belediyesi",
            "Erdemli Belediyesi", "Silifke Belediyesi", "Anamur Belediyesi", "Mut Belediyesi",
        ],
        extra_queries=[
            "Mersin Büyükşehir Belediyesi Halk Kart sosyal yardım başvurusu",
            "Tarsus Akdeniz Toroslar Yenişehir Mezitli Belediyesi sosyal yardım desteği",
        ],
        extra_hashtags=["#mersin", "#tarsus", "#akdeniz", "#toroslar", "#yenişehir", "#mezitli"],
    ),
    _make_city_category(
        "mugla_belediye",
        "Muğla",
        "mugla",
        [
            "Muğla Büyükşehir Belediyesi", "Bodrum Belediyesi", "Fethiye Belediyesi",
            "Milas Belediyesi", "Menteşe Belediyesi", "Marmaris Belediyesi",
            "Seydikemer Belediyesi", "Ortaca Belediyesi", "Yatağan Belediyesi",
            "Dalaman Belediyesi", "Köyceğiz Belediyesi", "Ula Belediyesi", "Datça Belediyesi",
        ],
        extra_queries=[
            "Muğla Büyükşehir Belediyesi Halk Kart sosyal yardım emekli öğrenci desteği",
            "Bodrum Fethiye Milas Menteşe Marmaris Belediyesi sosyal yardım başvurusu",
        ],
        extra_hashtags=["#muğla", "#bodrum", "#fethiye", "#milas", "#menteşe", "#marmaris"],
    ),
    _make_city_category(
        "ordu_belediye",
        "Ordu",
        "ordu",
        [
            "Ordu Büyükşehir Belediyesi", "Altınordu Belediyesi", "Ünye Belediyesi",
            "Fatsa Belediyesi", "Perşembe Belediyesi", "Kumru Belediyesi",
            "Korgan Belediyesi", "Gölköy Belediyesi", "Akkuş Belediyesi", "Aybastı Belediyesi",
        ],
        extra_hashtags=["#ordu", "#altınordu", "#ünye", "#fatsa", "#perşembe"],
    ),
    _make_city_category(
        "sakarya_belediye",
        "Sakarya",
        "sakarya",
        [
            "Sakarya Büyükşehir Belediyesi", "Adapazarı Belediyesi", "Serdivan Belediyesi",
            "Akyazı Belediyesi", "Erenler Belediyesi", "Hendek Belediyesi",
            "Karasu Belediyesi", "Geyve Belediyesi", "Arifiye Belediyesi",
            "Sapanca Belediyesi", "Pamukova Belediyesi", "Ferizli Belediyesi",
        ],
        extra_queries=[
            "Sakarya Büyükşehir Belediyesi Kart54 sosyal yardım gıda eğitim desteği",
            "Adapazarı Serdivan Akyazı Erenler Hendek Belediyesi sosyal yardım başvurusu",
        ],
        extra_hashtags=["#sakarya", "#adapazarı", "#serdivan", "#akyazı", "#hendek"],
    ),
    _make_city_category(
        "samsun_belediye",
        "Samsun",
        "samsun",
        [
            "Samsun Büyükşehir Belediyesi", "İlkadım Belediyesi", "Atakum Belediyesi",
            "Bafra Belediyesi", "Çarşamba Belediyesi", "Canik Belediyesi",
            "Vezirköprü Belediyesi", "Terme Belediyesi", "Tekkeköy Belediyesi",
            "Havza Belediyesi", "Alaçam Belediyesi", "19 Mayıs Belediyesi",
        ],
        extra_hashtags=["#samsun", "#ilkadım", "#atakum", "#bafra", "#çarşamba", "#canik"],
    ),
    _make_city_category(
        "sanliurfa_belediye",
        "Şanlıurfa",
        "sanliurfa",
        [
            "Şanlıurfa Büyükşehir Belediyesi", "Haliliye Belediyesi", "Eyyübiye Belediyesi",
            "Karaköprü Belediyesi", "Siverek Belediyesi", "Viranşehir Belediyesi",
            "Suruç Belediyesi", "Akçakale Belediyesi", "Birecik Belediyesi",
            "Ceylanpınar Belediyesi", "Harran Belediyesi", "Bozova Belediyesi",
            "Hilvan Belediyesi", "Halfeti Belediyesi",
        ],
        extra_hashtags=["#şanlıurfa", "#haliliye", "#eyyübiye", "#karaköprü", "#siverek"],
    ),
    _make_city_category(
        "tekirdag_belediye",
        "Tekirdağ",
        "tekirdag",
        [
            "Tekirdağ Büyükşehir Belediyesi", "Çorlu Belediyesi", "Süleymanpaşa Belediyesi",
            "Çerkezköy Belediyesi", "Kapaklı Belediyesi", "Ergene Belediyesi",
            "Malkara Belediyesi", "Saray Belediyesi", "Hayrabolu Belediyesi",
            "Şarköy Belediyesi", "Muratlı Belediyesi", "Marmaraereğlisi Belediyesi",
        ],
        extra_hashtags=["#tekirdağ", "#çorlu", "#süleymanpaşa", "#çerkezköy", "#kapaklı"],
    ),
    _make_city_category(
        "trabzon_belediye",
        "Trabzon",
        "trabzon",
        [
            "Trabzon Büyükşehir Belediyesi", "Ortahisar Belediyesi", "Akçaabat Belediyesi",
            "Araklı Belediyesi", "Of Belediyesi", "Yomra Belediyesi",
            "Arsin Belediyesi", "Vakfıkebir Belediyesi", "Sürmene Belediyesi",
            "Maçka Belediyesi", "Beşikdüzü Belediyesi", "Çaykara Belediyesi",
        ],
        extra_hashtags=["#trabzon", "#ortahisar", "#akçaabat", "#araklı", "#of", "#yomra"],
    ),
    _make_city_category(
        "van_belediye",
        "Van",
        "van",
        [
            "Van Büyükşehir Belediyesi", "İpekyolu Belediyesi", "Erciş Belediyesi",
            "Tuşba Belediyesi", "Edremit Belediyesi", "Özalp Belediyesi",
            "Çaldıran Belediyesi", "Başkale Belediyesi", "Muradiye Belediyesi",
            "Gürpınar Belediyesi", "Gevaş Belediyesi", "Saray Belediyesi",
        ],
        extra_hashtags=["#van", "#ipekyolu", "#erciş", "#tuşba", "#edremit"],
    ),
]


def get_category_for_current_hour(override_category_id: str | None = None) -> dict:
    """
    Türkiye'nin 30 Büyükşehir Belediyesi kategorisi arasında kesintisiz ve adil döngü (Round-Robin) sağlar:
    - Eğer override_category_id verilmişse doğrudan o kategoriyi döndürür.
    - Aksi halde data/published_history.json içerisindeki son yayın geçmişine bakarak
      en uzun süredir yayınlanmamış (veya hiç yayınlanmamış) sıradaki Büyükşehir ilini seçer.
      Böylece 30 Büyükşehir ilinin tamamı sırayla döner ve aynı il/haber tekrarı yaşanmaz.
    """
    if override_category_id:
        for cat in CATEGORIES:
            if cat["id"] == override_category_id or cat["wp_slug"] == override_category_id:
                return cat

    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data.get("items", [])
            last_seen_index: dict[str, int] = {}
            for idx, item in enumerate(items):
                cid = item.get("category_id", "")
                if cid:
                    last_seen_index[cid] = idx

            # Hiç yayınlanmamış olanlara (-1) ve en eski yayınlananlara öncelik ver
            best_cat = min(
                CATEGORIES,
                key=lambda c: last_seen_index.get(c["id"], -1),
            )
            return best_cat
    except Exception:
        pass

    now_tr = datetime.now(TR_TZ)
    total_hours = int(now_tr.timestamp() // 3600)
    return CATEGORIES[total_hours % len(CATEGORIES)]
