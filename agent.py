import os
import json
import time
import requests
import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from tavily import TavilyClient

# Ayarlar
from config import TARGET_URLS, SYSTEM_PROMPT

load_dotenv()

# API Kurulumları
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
model = genai.GenerativeModel('gemma-3-27b-it')

# --- YARDIMCI FONKSİYONLAR ---

def check_date_status(date_str):
    """
    Tarih durumunu kontrol eder.
    Dönüş Değerleri:
    - True: Gelecek tarih (veya bugün)
    - False: Geçmiş tarih
    - None: Tarih formatı bozuk veya 'belirtilmemiş'
    """
    if not date_str or "belirtilmemiş" in date_str.lower():
        return None

    try:
        # Kodun çalıştığı anki zaman
        current_now = datetime.datetime.now()
        
        # Gelen tarihi parse et
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        
        # Tarih bugünden küçükse (ve bugün değilse) False
        if target_date.date() < current_now.date():
            return False
        return True
    except:
        return None # Format bozuksa pas geç

def extract_events_with_ai(text_content, source_url):
    """Metni AI'a verip JSON istiyoruz"""
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    prompt = SYSTEM_PROMPT + f"\nBUGÜN: {today_str}\nKAYNAK: {source_url}\nİÇERİK:\n{text_content[:30000]}"
    try:
        resp = model.generate_content(prompt)
        clean = resp.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        # Liste değilse listeye çevir, boşsa boş dön
        if isinstance(data, dict): return [data]
        if isinstance(data, list): return data
        return []
    except: return []

# --- MODÜL 1: DOĞRUDAN KAZIMA (SCRAPING) ---
def run_scraping():
    found = []
    print("\n--- Siteler Taranıyor (Meetup/Kommunity/Coderspace/Luma) ---")
    for url in TARGET_URLS:
        print(f"📡 Bağlanılıyor: {url}...")
        try:
            resp = requests.get(f"https://r.jina.ai/{url}", timeout=30)
            if resp.status_code == 200:
                events = extract_events_with_ai(resp.text, url)
                if events:
                    print(f"   ✨ {len(events)} ham veri çekildi.")
                    found.extend(events)
            time.sleep(2)
        except Exception as e:
            print(f"Hata: {e}")
    return found

# --- MODÜL 2: ARAMA MOTORU (LINKEDIN) ---


# --- ANA MOTOR ---
def run_agent():
    today_display = datetime.date.today().strftime("%d.%m.%Y")
    print(f"🤖 TECH EVENT AI BAŞLATILIYOR... [Tarih: {today_display}]\n")
    
    all_events = []
    seen = set()

    # 1. Verileri Topla
    raw_list = run_scraping()
    # linkedin ekleyince run_scraping() + run_search()

    print(f"\n🧹 TEMİZLİK BAŞLIYOR... (Ham Veri: {len(raw_list)})")

    # --- FİLTRELEME ---
    for ev in raw_list:
        title = ev.get('title', 'Bilinmiyor')
        e_date = ev.get('event_date')
        d_date = ev.get('deadline')
        
        # 1. Mükerrer Kontrolü
        if title in seen: continue

        # 2. Tarih Durumlarını Analiz Et
        # (True: Gelecek, False: Geçmiş, None: Yok)
        e_status = check_date_status(e_date)
        d_status = check_date_status(d_date)

        # KURAL A: Eğer tarihi net olarak GEÇMİŞSE -> SİL
        if e_status is False:
            print(f"   🗑️ SİLİNDİ (Geçmiş Tarih): {title} -> Tarih: {e_date}")
            continue
        
        # KURAL B: Eğer deadline net olarak GEÇMİŞSE -> SİL
        if d_status is False:
            print(f"   🗑️ SİLİNDİ (Başvuru Bitmiş): {title} -> Deadline: {d_date}")
            continue

        # KURAL C: İkisi de YOKSA (Belirtilmemiş) -> SİL (Çöp Veri)
        if e_status is None and d_status is None:
            print(f"   🗑️ SİLİNDİ (Tarih Bulunamadı): {title} -> AI Tarihi: '{e_date}' olarak görmüş.")
            continue

        # 3. Konum Kontrolü
        loc = ev.get('location', 'Other').lower()
        if "istanbul" not in loc and "online" not in loc:
            print(f"   🗑️ SİLİNDİ (Konum Uymadı): {title} -> Konum: {loc}")
            continue

        # Validasyon geçti!
        all_events.append(ev)
        seen.add(title)

    # RAPOR
    print(f"\n🚀 TARAMA BİTTİ! TOPLAM {len(all_events)} EVENT:\n")
    for opp in all_events:
        print(f"📌 {opp['title']}")
        print(f"📅 Tarih: {opp.get('event_date')} | ⏳ Son Başvuru: {opp.get('deadline')}")
        print(f"📍 {opp.get('location')}")
        print(f"🔗 {opp['link']}")
        print("---")

if __name__ == "__main__":
    run_agent()