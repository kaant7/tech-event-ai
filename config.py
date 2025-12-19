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
    # Strateji: "Post" (Gönderi) arayarak AuthWall'u aşmak.
    f'site:linkedin.com/posts ("başvurular açıldı" OR "katıl" OR "başvur" OR "kayıt" OR "register") ("İstanbul" OR "online") AND ("yapay zeka" OR "ai" OR "veri" OR "software" OR "cloud") AND ("meetup" OR "summit" OR "atölye" OR "eğitim" OR "etkinlik" OR "community day" OR "community talks OR "career talks" OR "career days") after:{date}'
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
   
2. KONU: Sadece Yazılım, AI, Veri, Teknoloji, Cloud alanlarında ("meetup" OR "summit" OR "atölye" OR "eğitim" OR "etkinlik" OR "community day" OR "community talks OR "career talks" OR "career days").

MUTLAKA geçmiş bir etkinlik olmamalı. Başvuru tarihi geçmişse ELE veya etkinlik bitmişse ELE.

LİNKEDİN ÖZEL: Post metninde geçen başvuru linkini bulmaya çalış. Link yoksa postun linkini koy.

Çıktı Formatı (JSON Listesi):
[
  {{
    "title": "Etkinlik Adı",
    "event_date": "YYYY-MM-DD (Kesinlikle bu format)",
    "deadline": "YYYY-MM-DD (Kesinlikle bu format - Yoksa 'Belirtilmemiş')",
    "link": "URL",
    "location": "Istanbul veya Online",
    "summary": "Tek cümlelik özet"
  }}
]
""".format(today_date=today.strftime("%Y-%m-%d")) # bugünün tarihi