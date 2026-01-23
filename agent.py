import os
import json
import time
import requests
import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from tavily import TavilyClient

# Ayarlar
from config import TARGET_URLS, LINKEDIN_QUERIES, SYSTEM_PROMPT

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
    print("\n--- Siteler Taranıyor (Meetup/Luma) ---")
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
def run_search():
    found = []
    print("\n--- 🔍 ARAMA MOTORU (LinkedIn Posts) ---")
    for query in LINKEDIN_QUERIES:
        print(f"🔎 Tavily Soruluyor: {query[:40]}...")
        try:
            # max_results=5 yeterli, test için çok harcama
            res = tavily_client.search(query, search_depth="advanced", max_results=7)
            results = res.get('results', [])
            print(f"   🔹 {len(results)} sonuç geldi, analiz ediliyor...")
            
            for item in results:
                print(f"   👀 Okunuyor: {item['title'][:40]}...")
                events = extract_events_with_ai(item['content'], item['url'])
                if events: found.extend(events)
                time.sleep(1)
        except Exception as e:
            print(f"❌ Tavily Hatası: {e}")
    return found


# --- ANA MOTOR ---
def run_agent():
    today_display = datetime.date.today().strftime("%d.%m.%Y")
    print(f"🤖 TECH EVENT AI BAŞLATILIYOR... [Tarih: {today_display}]\n")

    # 1. Verileri Topla
    raw_list = run_scraping()+ run_search()

    print(f"\n🧹 TEMİZLİK BAŞLIYOR... (Ham Veri: {len(raw_list)})")

    all_events = []
    seen = set()

    # --- FİLTRELEME ---
    for ev in raw_list:
        title = ev.get('title', 'Bilinmiyor').strip()
        e_date = ev.get('event_date')
        link = ev.get('link', '').strip() # Linki temizle
        loc = ev.get('location', 'Other').lower()

        # 1. Tekrarlanma Kontrolü
        if title in seen: continue

        # 2. KONUM KONTROLÜ (Sadece İstanbul - Online İstemiyoruz) 🏙️
        # Eski Kod: if "istanbul" not in loc and "online" not in loc:
        # Yeni Kod: Sadece içinde "istanbul" geçenleri al.
        if "istanbul" not in loc:
            # print(f"   🗑️ SİLİNDİ (Fiziksel Değil): {title} -> {loc}")
            continue

        # 3. TARİH KONTROLÜ
        e_status = check_date_status(e_date)
        if e_status is False: continue # Geçmiş
        if e_status is None: continue  # Tarihsiz

        # Validasyon geçti!
        all_events.append(ev)
        seen.add(title)

    # RAPOR
    print(f"\n🚀 TARAMA BİTTİ! TOPLAM {len(all_events)} EVENT:\n")
    for opp in all_events:
        print(f"📌 {opp['title']}")
        print(f"❓ {opp.get('summary')}")
        print(f"📍 {opp.get('location')} | 📅 Tarih: {opp.get('event_date')}")
        print(f"🔗 {opp['link']}")
        print("---")

if __name__ == "__main__":
    run_agent()