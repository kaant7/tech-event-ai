import os
import json
import time
import requests
import datetime
import html
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

# --- TELEGRAM AYARLARI (YENİ EKLENDİ) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HISTORY_FILE = "history.json" # Gönderilenleri hatırlamak için dosya

# --- YARDIMCI FONKSİYONLAR ---

def load_history():
    """Daha önce gönderilmiş etkinliklerin listesini yükler."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_history(sent_events):
    """Gönderilen etkinlikleri dosyaya kaydeder."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(list(sent_events), f, ensure_ascii=False)

def send_telegram_message(message):
    """Telegram'a mesaj atar."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram Token veya Chat ID eksik! Mesaj gönderilmedi.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML", # Kalın yazı ve linkler için
        "disable_web_page_preview": True 
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ Telegram Hatası: {e}")

def check_date_status(date_str):
    """Tarih kontrolü: Geçmiş mi Gelecek mi?"""
    if not date_str or "belirtilmemiş" in date_str.lower():
        return None
    try:
        current_now = datetime.datetime.now()
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        if target_date.date() < current_now.date():
            return False
        return True
    except:
        return None 

def extract_events_with_ai(text_content, source_url):
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    prompt = SYSTEM_PROMPT + f"\nBUGÜN: {today_str}\nKAYNAK: {source_url}\nİÇERİK:\n{text_content[:30000]}"
    try:
        resp = model.generate_content(prompt)
        clean = resp.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
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
            resp = requests.get(f"https://r.jina.ai/{url}", timeout=60)
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
            res = tavily_client.search(query, search_depth="advanced", max_results=7)
            results = res.get('results', [])
            print(f"   🔹 {len(results)} sonuç geldi, analiz ediliyor...")
            
            for item in results:
                # print(f"   👀 Okunuyor: {item['title'][:40]}...") # Kalabalık yapmasın diye kapattım
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
    
    # 1. Önce Hafızayı Yükle (Daha önce attıklarımızı hatırlayalım)
    history = load_history()
    print(f"🧠 Hafıza Yüklendi: {len(history)} eski etkinlik biliniyor.")

    # 2. Verileri Topla
    raw_list = run_scraping() + run_search()

    print(f"\n🧹 TEMİZLİK VE FİLTRELEME BAŞLIYOR... (Ham Veri: {len(raw_list)})")

    new_events_to_send = []
    
    # Bu turda işlediklerimizi takip etmek için geçici liste
    processed_titles_in_this_run = set() 

    for ev in raw_list:
        title = ev.get('title', 'Bilinmiyor').strip()
        e_date = ev.get('event_date')
        link = ev.get('link', '').strip()
        loc = ev.get('location', 'Other').lower()
        
        # Etkinlik için benzersiz kimlik (Başlık + Tarih)
        unique_id = f"{title}_{e_date}"

        # 1. TEKRAR KONTROLLERİ
        # A) Bu çalışmada zaten buldum mu? (Mükerrer kaynak)
        if title in processed_titles_in_this_run: 
            continue
        
        # B) Daha önce Telegram'dan atmış mıyım? (History)
        if unique_id in history:
            # print(f"   ♻️ Zaten gönderildi: {title}")
            continue

        # 2. KONUM KONTROLÜ (Sadece İstanbul - Online İstemiyoruz)
        if "istanbul" not in loc:
            continue

        # 3. TARİH KONTROLÜ
        e_status = check_date_status(e_date)
        if e_status is False: continue # Geçmiş
        if e_status is None: continue  # Tarihsiz

        # HER ŞEY TAMAM! ✅
        new_events_to_send.append(ev)
        
        # Listelere ekle
        processed_titles_in_this_run.add(title)
        history.add(unique_id) # Hafızaya da ekle ki bir dahakine atmasın

    # --- RAPORLAMA VE GÖNDERİM ---
    if new_events_to_send:
        print(f"\n🚀 {len(new_events_to_send)} YENİ ETKİNLİK BULUNDU! Telegram'a gönderiliyor...\n")
        
        # Mesaj Başlığı
        msg = f"📢 <b>YENİ TEKNOLOJİ ETKİNLİKLERİ ({today_display})</b>\n\n"
        
        for opp in new_events_to_send:
            # Terminale Yaz (Burada escape yapmana gerek yok)
            print(f"📌 {opp['title']}")
            print(f"📅 {opp.get('event_date')} | 📍 {opp.get('location')}")
            print("---")
            
            # 🛡️ GÜVENLİK ÖNLEMİ: Özel karakterleri temizle
            safe_title = html.escape(opp.get('title', 'Başlık Yok'))
            safe_summary = html.escape(opp.get('summary', ''))
            safe_loc = html.escape(opp.get('location', ''))
            
            # Telegram Mesajına Ekle (Temizlenmiş değişkenleri kullan)
            msg += (
                f"🔥 <b>{safe_title}</b>\n"
                f"📅 {opp.get('event_date')} | 📍 {safe_loc}\n"
                f"ℹ️ <i>{safe_summary}</i>\n"
                f"🔗 <a href='{opp.get('link')}'>Başvuru ve Detaylar</a>\n\n"
            )
        
        # Tek seferde gönder
        send_telegram_message(msg)
        
        # Hafızayı dosyaya kaydet (Kritik!)
        save_history(history)
        print("✅ Mesaj gönderildi ve hafıza güncellendi.")
        
    else:
        print("\n😴 Yeni bir etkinlik bulunamadı. (Bulunanlar ya eski ya da online)")

if __name__ == "__main__":
    run_agent()