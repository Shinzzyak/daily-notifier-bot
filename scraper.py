import os
import requests
import feedparser
import json
import time
from groq import Groq

# --- KONFIGURASI ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
HISTORY_FILE = 'history.json'

# --- 1. MEMORY SYSTEM ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history[-60:], f, indent=4)

# --- 2. PERPLEXITY RESEARCHER ---
def research_with_perplexity(topic):
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key: return None

    print(f"🕵️ Riset Perplexity: {topic}...")
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "Kamu adalah Data Scraper. Cari harga spesifik, spesifikasi teknis, tanggal rilis, dan perbandingan langsung. JANGAN BEROPINI. HANYA DATA."},
            {"role": "user", "content": f"Cari data lengkap tentang: {topic}"}
        ]
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Perplexity Error: {e}")
    return None

# --- 3. GROQ WRITER (DIRECT SCRIPT MODE) ---
def generate_content_strategy(topic, category='GENERAL'):
    research_data = research_with_perplexity(topic)
    context = research_data if research_data else f"Judul: {topic} (Data tidak ditemukan, gunakan info umum)."

    groq_key = os.getenv('GROQ_API_KEY')
    if not groq_key: return "Error: GROQ_API_KEY missing."
    
    client = Groq(api_key=groq_key)

    # --- PERUBAHAN BESAR DI SINI (PROMPT LEBIH GALAK) ---
    if category == 'TECH':
        sys_prompt = f"""
        Kamu adalah Content Creator Tech (Gaya GadgetIn/David).
        Data Riset: {context}
        
        Tugas: TULIS NASKAH JADI (Siap Baca). JANGAN buat rencana/brief. JANGAN ada kata 'Tujuan' atau 'Strategi'.
        
        OUTPUT WAJIB (Markdown):
        
        ### 📱 NASKAH TIKTOK (Langsung Baca)
        * **Opening:** (Hook langsung ngegas. Contoh: "Woy! Harga Samsung naik lagi?!")
        * **Isi:** (Jelaskan 3 poin teknis dari data riset. Bahas spesifikasi/harga real).
        * **Closing:** (Kesimpulan pedas. Worth it atau Skip?).

        ### 🐦 TWEET (Langsung Post)
        * (Buat 1 Tweet pendek yang menyindir/memuji fakta dari data riset).

        ### 💰 ANALISA CUAN (Singkat Padat)
        * **Status:** (BELI SEKARANG / TAHAN DULU / JUAL RUGI)
        * **Alasan:** (1 Kalimat alasan ekonomi/teknis).
        """
    else:
        sys_prompt = f"""
        Kamu adalah News Anchor Senior.
        Data Riset: {context}
        
        Tugas: TULIS TEKS BERITA JADI. JANGAN buat proposal.
        
        OUTPUT WAJIB (Markdown):
        
        ### 📺 NASKAH BERITA (60 Detik)
        * **Headline:** (Judul Kapital yang Bombastis)
        * **Lead:** (Teras berita 1 kalimat).
        * **Body:** (Rangkuman fakta 5W+1H dari data riset).
        * **Closing:** (Pertanyaan retoris ke penonton).

        ### 🐦 THREAD X (Investigasi)
        * Tweet 1: (Fakta Utama)
        * Tweet 2: (Data Pendukung/Angka)
        * Tweet 3: (Kesimpulan/Pertanyaan)
        """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"Buatkan konten untuk topik: {topic}"}
            ],
            temperature=0.6, # Turunkan suhu agar lebih konsisten/tidak ngelantur
            max_tokens=1500
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error Groq: {e}"

# --- 4. SCRAPERS ---
def get_geopolitics_list(history):
    print("Scraping Geopolitics...")
    sources = [
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml")
    ]
    results = []
    keywords = ['war', 'conflict', 'military', 'army', 'politics', 'crisis', 'nuclear', 'tension']
    
    for source_name, url in sources:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if entry.title not in history:
                    if any(k in entry.title.lower() for k in keywords):
                        results.append({"title": entry.title, "link": entry.link, "source": source_name})
                        history.append(entry.title)
                        if len(results) >= 5: break
        except: continue
        if len(results) >= 5: break
    return results

def get_tech_list(history):
    print("Scraping Tech News...")
    # Gunakan RSS TechCrunch atau GSMArena
    url = "https://www.gsmarena.com/rss-news-reviews.php3" 
    results = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if entry.title not in history:
                results.append({"title": entry.title, "link": entry.link, "source": "GSMArena"})
                history.append(entry.title)
                if len(results) >= 5: break
    except Exception as e:
        print(f"Tech Error: {e}")
    return results

def get_trending_indo(history):
    url = "https://news.google.com/rss?ceid=ID:id&hl=id&gl=ID"
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if entry.title not in history:
                history.append(entry.title)
                return entry.title, entry.link
        return None, None
    except: return None, None

# --- 5. DISCORD SENDERS ---
def send_discord_text(webhook_url, title, content, color=3447003):
    if not content: return
    if len(content) > 4000: content = content[:4000] + "..."
    embed = {"title": title, "description": content, "color": color}
    requests.post(webhook_url, json={"username": "AI Assistant", "embeds": [embed]})

def send_discord_list(webhook_url, title, items, color=3447003):
    if not items: return
    embeds = []
    for item in items:
        embeds.append({
            "title": item['title'],
            "url": item['link'],
            "description": f"Sumber: {item['source']}",
            "color": color
        })
    payload = {"username": "News Feed", "content": f"**{title}**", "embeds": embeds[:10]}
    requests.post(webhook_url, json=payload)

# --- MAIN LOGIC ---
def main():
    print("🚀 Bot Started...")
    history = load_history()
    discord_url = os.getenv("DISCORD_WEBHOOK")
    
    # 1. FETCH & SEND LIST (Agar User tetap dapat update berita banyak)
    geo_list = get_geopolitics_list(history)
    tech_list = get_tech_list(history)
    
    if discord_url:
        if geo_list: send_discord_list(discord_url, "🌍 Geopolitics News", geo_list, 15158332)
        if tech_list: send_discord_list(discord_url, "📱 Tech News Updates", tech_list, 3447003)

    # 2. SELECT TOPIC FOR AI (Pilih 1 topik paling menarik)
    ai_topic = None
    ai_category = 'GENERAL'
    
    # Prioritas: Tech -> Indo Trending
    if tech_list:
        ai_topic = tech_list[0]['title'] # Ambil tech terbaru
        ai_category = 'TECH'
    else:
        indo_title, _ = get_trending_indo(history)
        if indo_title:
            ai_topic = indo_title
            ai_category = 'GENERAL'

    # 3. GENERATE AI CONTENT (Hanya jika ada topik)
    if ai_topic:
        print(f"🧠 AI Processing: {ai_topic}")
        ai_content = generate_content_strategy(ai_topic, ai_category)
        if discord_url:
            send_discord_text(discord_url, f"🧠 AI Script: {ai_category}", ai_content, 16776960)
            
    save_history(history)
    print("✅ Done!")

if __name__ == "__main__":
    main()
