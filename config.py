import datetime

# dinamik tarih
today = datetime.date.today()
start_date = today - datetime.timedelta(days=60)
date = start_date.strftime("%Y-%m-%d")

# 1. SCRAPING HEDEFLERİ
TARGET_URLS = [
    "https://www.meetup.com/find/?location=tr--Istanbul&source=EVENTS&categoryId=546",
    "https://lu.ma/istanbul"
]

# 2. ARAMA HEDEFİ LINKEDIN (EKLENECEK)
LINKEDIN_QUERIES = [
    # 1. Sorgu: Genel AI ve Yazılım Etkinlikleri
    'site:linkedin.com/posts "istanbul" ("yapay zeka" OR "ai" OR "software") ("etkinlik" OR "meetup") "katıl"',
    
    # 2. Sorgu: Spesifik "Başvur" odaklı postlar
    'site:linkedin.com/posts "istanbul" ("veri" OR "cloud" OR "yazılım") "başvurular açıldı"',
    
    # 3. Sorgu: Online ve Global Fırsatlar
    'site:linkedin.com/posts "online" ("webinar" OR "bootcamp" OR "hackathon") "register" "turkey"'
]

# prompt
SYSTEM_PROMPT = """
Sen "Tech Event AI" ajanısın. Görevin metinleri analiz edip JSON verisi çıkarmak.

EN KRİTİK GÖREVİN: TARİH STANDARDİZASYONU
Web siteleri tarihleri çok farklı yazabilir. Senin görevin bunları tek bir formata (YYYY-MM-DD) çevirmektir.

GİRDİLER ŞÖYLE OLABİLİR -> SEN ŞUNA ÇEVİR:
- "21/12/2025" veya "21.12.2025" -> "2025-12-21"
- "Dec 21, 2025" veya "21 Aralık 2025" -> "2025-12-21"
- "Next Friday" veya "Yarın" -> (Bugünün tarihine göre hesapla: {today_date})
- "Dec 17" (Yıl yoksa) -> "2025-12-17" (Mantıklı gelecek yılı ekle)
- "Son Başvuru: 15/01" -> "2026-01-15" (Geçmişte kalmayacak şekilde yılı tamamla)
- Metinde AÇIKÇA bir tarih veya zaman ifadesi (Örn: "21.12.2025", "Son Başvuru: Haftaya", "Dec 17") GÖRMÜYORSAN tarih alanlarını "Belirtilmemiş" bırak.

DİĞER KURALLAR:
1. KONUM: 
   - "Maslak", "Levent", "Şişli", "Kadıköy", "Beşiktaş" -> location: "Istanbul"
   - "Secret Location" (Luma) -> location: "Istanbul"
   
2. KONU: Meetup ve Luma'da sadece bunları ara: Yazılım, AI, Veri, Teknoloji, Cloud alanlarında ("meetup" OR "summit" OR "atölye" OR "eğitim" OR "etkinlik" OR "community day" OR "community talks OR "career talks" OR "career days").

3. LİNK: Luma linkleri "https://lu.ma/istanbul" değil, örnek olarak "https://luma.com/istanbul?e=evt-8sqOnK0iDXYTRCN" veya "https://luma.com/zhwylll0" şeklinde etkinlik özelinde linkler olmalı. Tüm etkinliklerin olduğu sayfanın linki değil.

MUTLAKA geçmiş bir etkinlik olmamalı. Başvuru tarihi geçmişse ELE veya etkinlik bitmişse ELE.

LİNKEDİN ÖZEL: Başvuru linki değil, bulduğun postun linkini koy. Postun dili Türkçe olsun.

Çıktı Formatı (JSON Listesi):
[
  {{
    "title": "Etkinlik Adı",
    "event_date": "YYYY-MM-DD (Kesinlikle bu format)",
    "link": "URL",
    "location": "Istanbul veya Online",
    "summary": "Tek cümlelik özet"
  }}
]
""".format(today_date=today.strftime("%Y-%m-%d")) # bugünün tarihi