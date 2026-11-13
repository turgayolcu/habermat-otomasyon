"""
Habermat.com - 10 Büyükşehir Belediyesi Kalıcı "Yardım Başvurusu ve Sosyal Kart Rehberi" Yayınlayıcı
Kural #1: 1200x675 WebP tamamen yazısız, çerçevesiz, logosuz gerçek haber fotoğrafı
Kural #3: İstanbul, İzmir, Bursa, Antalya, Adana, Konya, Mersin, Kocaeli, Diyarbakır, Samsun
          için kalıcı /<sehir>-buyuksehir-belediyesi-yardim-basvurusu/ ana rehberleri
"""

from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

from src.categories import CATEGORIES
from src.image_search import fetch_news_images
from src.media_generator import generate_wp_featured_image
from src.wp_publisher import WordPressPublisher

BASE_DIR = Path(__file__).resolve().parent
WORK_DIR = BASE_DIR / "output" / "pillar_work"

PILLAR_CITIES: List[Dict[str, str]] = [
    {
        "city": "İstanbul",
        "cat_id": "istanbul_belediye",
        "slug": "istanbul-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "İstanbulkart Sosyal Destek Kartı (İBB Sosyal Yardım Kartı)",
        "portal": "sosyalhizmetler.ibb.gov.tr, İstanbul Senin Uygulaması ve ALO 153 Çözüm Merkezi",
        "official_domain": "ibb.istanbul",
        "call_center": "ALO 153 Çözüm Merkezi",
        "districts": "Esenyurt, Küçükçekmece, Bağcılar, Pendik, Ümraniye, Bahçelievler, Sultangazi, Üsküdar, Maltepe, Kadıköy, Kartal, Gaziosmanpaşa ve 39 ilçe",
        "special_programs": "İstanbulkart Sosyal Destek (Market/Gıda Yardımı), Emekli Pazar Desteği (10.000 TL), Halk Süt, Anne Kart (0-4 Yaş Ücretsiz Ulaşım), Yenidoğan Destek Paketi, Genç Üniversiteli Eğitim Desteği ve Askıda Fatura",
        "photo_query": "İstanbul Büyükşehir Belediyesi Saraçhane binası sosyal yardım",
    },
    {
        "city": "İzmir",
        "cat_id": "izmir_belediye",
        "slug": "izmir-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "İzmir Şehir Kartı (Bizİzmir Dayanışma ve Sosyal Yardım Kartı)",
        "portal": "bizizmir.com (Bizİzmir Dijital Platformu) ve HİM 153 Hemşehri İletişim Merkezi",
        "official_domain": "izmir.bel.tr",
        "call_center": "153 Hemşehri İletişim Merkezi (HİM)",
        "districts": "Buca, Karabağlar, Bornova, Konak, Karşıyaka, Bayraklı, Çiğli, Torbalı, Menemen, Gaziemir, Ödemiş, Bergama ve 30 ilçe",
        "special_programs": "İzmir Şehir Kartı Nakit ve Market Desteği, Emekli Kira ve Su Faturası Desteği, Süt Kuzusu Projesi, İlköğretim Kırtasiye-Bot-Mont Yardımı, Üniversite Eğitim Desteği ve Halkın Bakkalı Gıda Kolisi",
        "photo_query": "İzmir Büyükşehir Belediyesi sosyal yardım dağıtımı",
    },
    {
        "city": "Bursa",
        "cat_id": "bursa_belediye",
        "slug": "bursa-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Bursa Kart16 Sosyal Destek Kartı",
        "portal": "bursa.bel.tr Sosyal Destek Başvuru Ekranı ve ALO 153 Beyaz Masa",
        "official_domain": "bursa.bel.tr",
        "call_center": "ALO 153 Beyaz Masa (444 16 00)",
        "districts": "Osmangazi, Yıldırım, Nilüfer, İnegöl, Gemlik, Mustafakemalpaşa, Mudanya, Gürsu, Kestel, Karacabey ve 17 ilçe",
        "special_programs": "Kart16 Gıda ve Ekonomik Destek Kartı, Emekli Bayram ve Nakit Desteği, BURSKOOP Üniversite ve Meslek Lisesi Bursu, Kırtasiye Çeki, Yenidoğan Bebek Paketi ve Kışlık Yakacak Desteği",
        "photo_query": "Bursa Büyükşehir Belediyesi hizmet binası sosyal yardım",
    },
    {
        "city": "Antalya",
        "cat_id": "antalya_belediye",
        "slug": "antalya-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Antalya Halk Kart (Büyükşehir Sosyal Destek Kartı)",
        "portal": "antalya.bel.tr Online Sosyal Yardım Başvuru Formu ve ABİM 0242 249 50 00",
        "official_domain": "antalya.bel.tr",
        "call_center": "ABİM (Antalya Büyükşehir İletişim Merkezi - 444 94 20)",
        "districts": "Kepez, Muratpaşa, Alanya, Manavgat, Konyaaltı, Serik, Aksu, Kumluca, Döşemealtı, Kaş, Korkuteli ve 19 ilçe",
        "special_programs": "Antalya Halk Kart Aylık Market ve Gıda Desteği, Halk Süt, Halk Mama, Sosyal Market Giyim ve Erzak Yardımı, Öğrenci Eğitim-Ulaşım Desteği ve Emekli Su Faturası İndirimi",
        "photo_query": "Antalya Büyükşehir Belediyesi hizmet binası yardım",
    },
    {
        "city": "Adana",
        "cat_id": "adana_belediye",
        "slug": "adana-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Adana Halk Kart (Sosyal Yardım ve Dayanışma Kartı)",
        "portal": "adana.bel.tr Sosyal Hizmetler Dairesi Başvuru Ekranı ve ALO 153",
        "official_domain": "adana.bel.tr",
        "call_center": "ALO 153 Çağrı Merkezi",
        "districts": "Seyhan, Yüreğir, Çukurova, Sarıçam, Ceyhan, Kozan, İmamoğlu, Karataş, Karaisalı, Pozantı ve 15 ilçe",
        "special_programs": "Adana Halk Kart Market ve Gıda Desteği, Dar Gelirli Nakdi Yardım, Ramazan ve Kış Dönemi Erzak Kolisi, Hoş Geldin Bebek Paketi, Öğrenci Ulaşım-Kırtasiye Desteği ve Evde Sıcak Yemek Hizmeti",
        "photo_query": "Adana Büyükşehir Belediyesi sosyal yardım kolisi",
    },
    {
        "city": "Konya",
        "cat_id": "konya_belediye",
        "slug": "konya-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Konya Sosyal Kart (Şehir Kartı Sosyal Destek Programı)",
        "portal": "konya.bel.tr Sosyal İnovasyon ve Sosyal Yardım Başvuru Ekranı / Açık Kapı",
        "official_domain": "konya.bel.tr",
        "call_center": "ALO 153 Konya Büyükşehir İletişim Merkezi (0332 221 14 00)",
        "districts": "Selçuklu, Meram, Karatay, Ereğli, Akşehir, Beyşehir, Çumra, Seydişehir, Ilgın, Cihanbeyli, Kulu ve 31 ilçe",
        "special_programs": "Konya Sosyal Kart Aylık Alışveriş Limiti, Eğitim ve Üniversite Öğrencisi Nakdi Desteği, Yeni Bebek Sahibi Aile Desteği, Kışlık Yakacak ve Doğalgaz Yardımı, Su Faturası İndirimi ve Glutensiz Gıda Desteği",
        "photo_query": "Konya Büyükşehir Belediyesi sosyal destek yardımı",
    },
    {
        "city": "Mersin",
        "cat_id": "mersin_belediye",
        "slug": "mersin-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Mersin Halk Kart (Büyükşehir Sosyal Yardım Kartı)",
        "portal": "mersin.bel.tr Teksin Online Başvuru Sistemi ve ALO 185 / 153 Teksin Çağrı Merkezi",
        "official_domain": "mersin.bel.tr",
        "call_center": "Teksin 185 / ALO 153 Çağrı Merkezi",
        "districts": "Akdeniz, Toroslar, Yenişehir, Mezitli, Tarsus, Erdemli, Silifke, Anamur, Mut, Bozyazı ve 13 ilçe",
        "special_programs": "Mersin Halk Kart Aylık Gıda ve Market Bakiyesi, Üniversite Öğrencisi Öğrenim Yardımı, Mahalle Mutfakları 1 Kap Sıcak Yemek, Süt Senin Gurur Mersin, Hoş Geldin Bebek Paketi ve Yakacak/Gıda Kolisi",
        "photo_query": "Mersin Büyükşehir Belediyesi Halk Kart sosyal yardım",
    },
    {
        "city": "Kocaeli",
        "cat_id": "kocaeli_belediye",
        "slug": "kocaeli-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Kocaeli 41 Kart (Gıda, Giyim, Medikal ve Fatura Destek Kartı)",
        "portal": "kocaeli.bel.tr e-Kocaeli Sosyal Yardım Portalı ve 153 Çağrı Merkezi",
        "official_domain": "kocaeli.bel.tr",
        "call_center": "ALO 153 Kocaeli Çağrı Merkezi",
        "districts": "İzmit, Gebze, Darıca, Körfez, Gölcük, Derince, Çayırova, Kartepe, Başiskele, Karamürsel, Kandıra, Dilovası (12 ilçe)",
        "special_programs": "41 Kart Gıda ve Market Desteği, 41 Kart Su ve Doğalgaz Fatura Desteği, Anne Şehir Süt ve Bebek Desteği, Emekli Nakit ve Pazar Desteği, Kırtasiye-Giyim Yardımı ve Medikal Malzeme Desteği",
        "photo_query": "Kocaeli Büyükşehir Belediyesi 41 Kart sosyal yardım",
    },
    {
        "city": "Diyarbakır",
        "cat_id": "diyarbakir_belediye",
        "slug": "diyarbakir-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Diyarbakır Sosyal Destek Kartı ve Halk Market",
        "portal": "diyarbakir.bel.tr Sosyal Hizmetler Daire Başkanlığı ve ALO 153",
        "official_domain": "diyarbakir.bel.tr",
        "call_center": "ALO 153 Büyükşehir Çözüm Merkezi",
        "districts": "Bağlar, Kayapınar, Yenişehir, Sur, Ergani, Bismil, Silvan, Çınar, Çermik, Dicle, Kulp, Hani, Lice ve 17 ilçe",
        "special_programs": "Sosyal Destek Kartı ve Sosyal Market Alışveriş Desteği, Dar Gelirli Gıda Kolisi, Çölyak/Glütensiz Gıda Paketi, İlköğretim ve Üniversite Kırtasiye-Eğitim Yardımı, Halk Lokantası ve Kışlık Destek",
        "photo_query": "Diyarbakır Büyükşehir Belediyesi sosyal yardım kolisi",
    },
    {
        "city": "Samsun",
        "cat_id": "samsun_belediye",
        "slug": "samsun-buyuksehir-belediyesi-yardim-basvurusu",
        "card_name": "Samsun Büyükşehir Sosyal Destek Kartı ve Gıda Bankası",
        "portal": "samsun.bel.tr Çözüm Merkezi Online Başvuru Ekranı ve ALO 153",
        "official_domain": "samsun.bel.tr",
        "call_center": "ALO 153 Samsun Çözüm Merkezi",
        "districts": "İlkadım, Atakum, Canik, Tekkeköy, Bafra, Çarşamba, Terme, Vezirköprü, Havza, Alaçam, 19 Mayıs ve 17 ilçe",
        "special_programs": "Sosyal Destek Kartı (Market ve Gıda Yardımı), Emekli ve Dar Gelirli Nakit/Fatura Desteği, Öğrenci Kırtasiye ve Burs Yardımı, Sıcak Yemek / Aşevi Hizmeti, Hoş Geldin Bebek ve Kışlık Yakacak Yardımı",
        "photo_query": "Samsun Büyükşehir Belediyesi sosyal yardım desteği",
    },
]


def _build_pillar_package(info: Dict[str, str], category: dict) -> Dict[str, Any]:
    city = info["city"]
    slug = info["slug"]
    card_name = info["card_name"]
    portal = info["portal"]
    call_center = info["call_center"]
    districts = info["districts"]
    special_programs = info["special_programs"]

    seo_title = f"{city} Büyükşehir Belediyesi Yardım Başvurusu ve Sosyal Kart Rehberi: Başvuru Şartları ve Formu 2026"
    spot = (
        f"{city} Büyükşehir Belediyesi 2026 sosyal yardım başvurusu ekranı üzerinden dar gelirli ailelere, "
        f"emeklilere, kiracılara ve öğrencilere yönelik {card_name}, nakdi destek, gıda kolisi, yakacak ve eğitim "
        f"yardımları başlamıştır. Online başvuru formu, gelir şartları ve sorgulama adımlarını tek rehberde derledik."
    )

    html_content = f"""
<p class="habermat-spot"><strong>{spot}</strong></p>

<div class="habermat-toc" style="background:#F8FAFC;border:1px solid #E2E8F0;border-left:4px solid #0B132B;border-radius:6px;padding:14px 18px;margin:20px 0;">
<p style="margin:0 0 8px 0;font-weight:700;color:#0B132B;">📌 Bu Rehberde Öne Çıkan Başlıklar:</p>
<ul style="margin:0;padding-left:20px;color:#1E293B;font-size:15px;">
  <li style="margin-bottom:6px;">{city} Büyükşehir Belediyesi Yardım Başvurusu Nasıl Yapılır? (2026 Online Form)</li>
  <li style="margin-bottom:6px;">{card_name} Nedir, Kimlere Verilir?</li>
  <li style="margin-bottom:6px;">{city} Belediyesi Sosyal Yardım Başvuru Şartları ve Gelir Kriteri Nelerdir?</li>
  <li style="margin-bottom:6px;">Gıda Kolisi, Nakdi Destek, Emekli ve Öğrenci Yardımı Kalemleri</li>
  <li style="margin-bottom:6px;">Başvuru Sorgulama ve Sıkça Sorulan Sorular (SSS)</li>
</ul>
</div>

<h2>{city} Büyükşehir Belediyesi Yardım Başvurusu Nasıl Yapılır?</h2>
<p>{city} genelinde ikamet eden ve ekonomik desteğe ihtiyaç duyan vatandaşlar, <strong>{city} Büyükşehir Belediyesi Sosyal Hizmetler Dairesi Başkanlığı</strong> tarafından yürütülen sosyal destek programlarına hem internet üzerinden online başvuru formu ile hem de hizmet noktalarından şahsen müracaat edebilmektedir. 2026 yılı itibarıyla {districts} ilçelerinde yaşayan haneler için başvurular üç resmi kanal üzerinden kabul edilmektedir:</p>
<ul>
  <li><strong>Online Başvuru Formu:</strong> Doğrudan <strong>{portal}</strong> üzerinden T.C. kimlik numarası, iletişim telefonu ve hane gelir/ikamet bilgileri doldurularak dakikalar içinde ön başvuru kaydı oluşturulur.</li>
  <li><strong>e-Devlet Kapısı Üzerinden Başvuru:</strong> <code>turkiye.gov.tr</code> arama çubuğuna <em>"Belediye Sosyal Yardım Başvurusu ve Sorgulama"</em> veya <em>"Sosyal Yardım Başvuru Hizmeti"</em> yazılarak elektronik başvuru tamamlanabilir.</li>
  <li><strong>Telefon ve Hizmet Masası Başvurusu:</strong> İnternet erişimi bulunmayan yaşlı, engelli veya dezavantajlı vatandaşlar <strong>{call_center}</strong> hattını arayarak ya da ilçe sosyal hizmet merkezlerine T.C. kimlik kartlarıyla başvurarak kayıt açtırabilir.</li>
</ul>

<h2>{card_name} Nedir, Kimlere Verilir?</h2>
<p><strong>{card_name}</strong>, {city} Büyükşehir Belediyesi'nin geleneksel erzak kolisi dağıtımı yerine vatandaşların kendi temel ihtiyaçlarını anlaşmalı yerel marketlerden, fırınlardan ve sosyal market noktalarından özgürce karşılayabilmesi amacıyla geliştirdiği ön ödemeli sosyal destek kartıdır. Sosyal inceleme uzmanları tarafından onaylanan hak sahiplerinin kartlarına her ay veya dönemsel olarak hane nüfusuna göre bakiye yüklemesi yapılmaktadır.</p>
<p>Kart sahipleri; gıda, bebek maması, çocuk bezi, temizlik malzemesi, kırtasiye ve kış aylarında yakacak/fatura desteği gibi farklı destek paketlerinden tek bir kart üzerinden yararlanabilmektedir. Bakiyeler yüklendiğinde hak sahibinin cep telefonuna SMS ile bilgilendirme mesajı gönderilir.</p>

<figure class="wp-block-table" style="margin:24px 0;">
<table style="width:100%;border-collapse:collapse;font-size:15px;">
<thead><tr>
<th colspan="2" style="background:#0B132B;color:#FFFFFF;padding:12px 14px;text-align:left;">
📊 {city} Büyükşehir Belediyesi – 2026 Güncel Sosyal Yardım ve Sosyal Kart Özeti Tablosu
</th></tr></thead>
<tbody>
<tr><td style="padding:10px 14px;border:1px solid #CBD5E1;font-weight:700;background:#F1F5F9;width:38%;">Kurum Adı</td><td style="padding:10px 14px;border:1px solid #CBD5E1;">{city} Büyükşehir Belediyesi Sosyal Hizmetler Dairesi Başkanlığı</td></tr>
<tr><td style="padding:10px 14px;border:1px solid #CBD5E1;font-weight:700;background:#F1F5F9;width:38%;">Sosyal Destek Kartı</td><td style="padding:10px 14px;border:1px solid #CBD5E1;">{card_name}</td></tr>
<tr><td style="padding:10px 14px;border:1px solid #CBD5E1;font-weight:700;background:#F1F5F9;width:38%;">Kapsanan İlçeler</td><td style="padding:10px 14px;border:1px solid #CBD5E1;">{districts}</td></tr>
<tr><td style="padding:10px 14px;border:1px solid #CBD5E1;font-weight:700;background:#F1F5F9;width:38%;">Başlıca Yardım Kalemleri</td><td style="padding:10px 14px;border:1px solid #CBD5E1;">{special_programs}</td></tr>
<tr><td style="padding:10px 14px;border:1px solid #CBD5E1;font-weight:700;background:#F1F5F9;width:38%;">Başvuru ve Sorgulama Kanalı</td><td style="padding:10px 14px;border:1px solid #CBD5E1;">{portal} &amp; e-Devlet</td></tr>
</tbody></table></figure>

<h2>{city} Büyükşehir Belediyesi Sosyal Yardım Başvuru Şartları Nelerdir?</h2>
<p>Belediye sosyal yardımlarından ve {card_name} programından faydalanabilmek için hanenin sosyo-ekonomik durumunun belirlenen muhtaçlık sınırının altında olması gerekmektedir. Sosyal inceleme heyetinin dikkate aldığı temel başvuru şartları şunlardır:</p>
<ul>
  <li>Türkiye Cumhuriyeti vatandaşı olmak ve <strong>{city}</strong> il sınırları içerisindeki ilçelerden birinde resmi ikametgahının bulunması,</li>
  <li>Hane içinde kişi başına düşen aylık net gelirin asgari ücretin üçte birinden veya belediye sosyal destek komisyonunun belirlediği dar gelir eşiğinden düşük olması,</li>
  <li>Başvuru sahibi veya hanedeki bireyler adına kayıtlı yüksek değerli gayrimenkul, ticari işletme veya lüks araç bulunmaması,</li>
  <li>Kiracı aileler, tek maaşlı emekliler, eşi vefat etmiş kadınlar, %40 ve üzeri engelli raporu bulunan bireyler, 65 yaş üstü yalnız yaşayan vatandaşlar ile okuyan çocuğu bulunan ailelere sosyal inceleme puanlamasında öncelik tanınmaktadır.</li>
</ul>
<p>Hane geliriniz ve kişi sayınıza göre hangi yardımlara uygun olduğunuzu hemen öğrenmek için <a href="https://www.habermat.com/devlet-ve-belediye-yardimi-sorgulama-robotu/"><strong>2026 Devlet ve Belediye Yardımı Sorgulama Robotu</strong></a> aracımızı ücretsiz kullanabilirsiniz.</p>

<h2>{city} Belediyesi Hangi Yardımları Veriyor? (2026 Destek Paketi)</h2>
<p>2026 sosyal belediyecilik bütçesi kapsamında <strong>{city} Büyükşehir Belediyesi</strong> tarafından dar gelirli vatandaşlara sunulan başlıca ayni ve nakdi yardımlar şunlardır:</p>
<ol>
  <li><strong>Sosyal Kart ve Market Alışveriş Desteği:</strong> Hak sahibi ailelerin kartlarına düzenli olarak gıda, hijyen ve temel mutfak alışverişi bakiyesi tanımlanır.</li>
  <li><strong>Gıda Kolisi ve Sıcak Yemek (Aşevi) Yardımı:</strong> Yemek yapamayacak durumda olan yaşlı ve engelli vatandaşlara günlük sıcak yemek, dar gelirli ailelere ise temel kuru gıda kolisi ulaştırılır.</li>
  <li><strong>Emekli Pazar, Nakit ve Fatura Desteği:</strong> Sadece en düşük emekli aylığı ile geçinen ve kiracı olan emeklilere nakdi pazar desteği, su faturası indirimi ve kışlık ısınma yardımı sağlanır.</li>
  <li><strong>Öğrenci Kırtasiye, Ulaşım ve Eğitim Bursu:</strong> İlkokul, ortaokul, lise ve üniversite öğrencisi bulunan ailelere kırtasiye çeki, bot-mont desteği, indirimli öğrenci abonman kartı ve eğitim yardımı ödenir.</li>
  <li><strong>Süt Yardımı ve Yenidoğan Bebek Paketi:</strong> Çocuklu ailelere düzenli süt desteği ve yeni doğan bebekler için hijyen, bez ve kıyafet setinden oluşan Hoş Geldin Bebek paketi hediye edilir.</li>
</ol>

<h2>{city} Sosyal Yardım Başvurusu İçin Gerekli Belgeler Nelerdir?</h2>
<p>Online ön başvuru sırasında e-Devlet entegrasyonu sayesinde belge yükleme zorunluluğu en aza indirilmiştir. Ancak sosyal inceleme görevlilerinin hane ziyareti veya kesin kayıt aşamasında talep edebileceği belgeler şunlardır:</p>
<ul>
  <li>Başvuru sahibinin T.C. Kimlik Kartı fotokopisi,</li>
  <li>e-Devlet üzerinden barkodlu <strong>Tarihçeli Yerleşim Yeri ve Diğer Adres Belgesi</strong> ile <strong>Vukuatlı Nüfus Kayıt Örneği</strong>,</li>
  <li>Hanede çalışan veya emekli varsa maaş bordrosu / gelir belgesi, işsiz bireyler için SGK Tescil ve Hizmet Dökümü,</li>
  <li>Kiracı olunduğunu gösteren kira sözleşmesi ve örnek su/doğalgaz faturası,</li>
  <li>Öğrenci yardımı için güncel Öğrenci Belgesi, engelli/kronik hastalık yardımı için Sağlık Kurulu Raporu.</li>
</ul>

<h2>Sıkça Sorulan Sorular (SSS)</h2>

<h3>{city} Büyükşehir Belediyesi yardım başvurusu sonucu nasıl sorgulanır?</h3>
<p>{city} Büyükşehir Belediyesi sosyal yardım ve {card_name} başvuru sonuçlarınızı {portal} üzerindeki başvuru takip ekranından T.C. kimlik numaranızla veya doğrudan {call_center} hattını arayarak öğrenebilirsiniz. Ayrıca inceleme tamamlandığında cep telefonunuza SMS ile bilgilendirme gönderilmektedir.</p>

<h3>{card_name} başvurusu kaç günde sonuçlanır ve bakiye ne zaman yatar?</h3>
<p>Online veya şahsen yapılan başvurular, sosyal hizmet uzmanlarının gelir testi ve hane incelemesi sürecinin ardından ortalama 15 ile 30 iş günü içerisinde sonuçlandırılır. Onaylanan kartlara ödemeler belediyenin belirlediği aylık veya dönemsel ödeme takvimine göre yatırılır.</p>

<h3>Kiracılar ve emekliler {city} Belediyesi sosyal yardımlarından yararlanabilir mi?</h3>
<p>Evet. Hane içinde kişi başına düşen gelir kriterini sağlayan kiracı aileler ve dar gelirli emekliler hem {card_name} market desteğinden hem de emeklilere özel nakit, su faturası indirimi ve yakacak yardımlarından öncelikli olarak faydalanabilmektedir.</p>

<h3>Hem Bakanlık (e-Devlet SYDV) hem de {city} Belediyesi yardımına aynı anda başvurulabilir mi?</h3>
<p>Evet, Aile ve Sosyal Hizmetler Bakanlığı Sosyal Yardımlaşma ve Dayanışma Vakfı (SYDV) yardımları ile {city} Büyükşehir Belediyesi sosyal destek programları birbirinden bağımsızdır; şartları sağlayan haneler her iki kurumun desteklerine de eşzamanlı başvurabilir.</p>
"""

    return {
        "seo_title": seo_title,
        "slug": slug,
        "meta_description": spot[:158],
        "spot": spot,
        "wp_html_content": html_content,
        "tags": [
            f"{city} Büyükşehir Belediyesi",
            f"{city} Sosyal Yardım Başvurusu",
            card_name.split("(")[0].strip(),
            "Belediye Yardım Başvurusu 2026",
            "Sosyal Kart Başvurusu",
        ],
        "reels_headline": seo_title,
        "reels_badge": f"{city.upper()} • SOSYAL YARDIM REHBERİ",
        "visual_queries": [
            info["photo_query"],
            f"{city} Büyükşehir Belediyesi hizmet binası",
            f"{city} belediye sosyal yardım",
        ],
    }


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    wp = WordPressPublisher()
    headers = wp._ensure_session_or_auth()
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    cat_map = {c["id"]: c for c in CATEGORIES}
    published_links: List[str] = []

    for info in PILLAR_CITIES:
        city = info["city"]
        slug = info["slug"]
        cat = cat_map.get(info["cat_id"], CATEGORIES[0])

        # Mevcut post var mı kontrol et
        check = wp.session.get(
            f"{wp.api_base}/posts",
            params={"slug": slug},
            headers=headers,
            timeout=15,
        )
        if check.status_code == 200 and check.json():
            existing_url = check.json()[0].get("link")
            print(f"[MEVCUT] {city} rehberi zaten yayında: {existing_url}")
            published_links.append(f"{city}: {existing_url}")
            continue

        package = _build_pillar_package(info, cat)
        photo_dir = WORK_DIR / slug
        real_photos = fetch_news_images(
            news_title=info["photo_query"],
            category=cat,
            ai_visual_queries=package["visual_queries"],
            work_dir=photo_dir,
            min_count=1,
        )

        webp_path = WORK_DIR / f"{slug}.webp"
        generate_wp_featured_image(package, cat, webp_path, real_photos=real_photos)

        res = wp.publish_article(package, cat, webp_path)
        link = res.get("link", "")
        print(f"[YAYINLANDI] {city} -> {link}")
        published_links.append(f"{city}: {link}")

    print("\n=== TÜM BÜYÜKŞEHİR ANA REHBERLERİ TAMAMLANDI ===")
    for item in published_links:
        print(" -", item)


if __name__ == "__main__":
    main()
