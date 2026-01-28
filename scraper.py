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
            {"role": "system", "content": "Kamu Data Scraper. Cari fakta valid, angka, spesifikasi, dan kontroversi. JANGAN BEROPINI."},
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

# --- 3. GROQ WRITER ---
def generate_content_strategy(topic, category='GENERAL'):
    research_data = research_with_perplexity(topic)
    context = research_data if research_data else f"Judul: {topic} (Data minim, kembangkan dari judul)."

    groq_key = os.getenv('GROQ_API_KEY')
    if not groq_key: return "Error: GROQ_API_KEY missing."
    
    client = Groq(api_key=groq_key)

    if category == 'TECH':
        sys_prompt = f"""
        Kamu Content Creator Tech (Ala GadgetIn).
        Data: {context}
        Tugas: TULIS NASKAH JADI (Siap Baca). To the point.
        
        OUTPUT (Markdown):
        ### 📱 NASKAH TIKTOK (Tech)
        * **Opening:** (Hook ngegas).
        * **Isi:** (3 Poin Spesifikasi/Fakta).
        * **Closing:** (Kesimpulan: Worth it/Skip?).
        
        ### 💰 ANALISA CUAN
        * **Status:** (BELI / TAHAN / SKIP)
        * **Alasan:** (1 Kalimat).
        """
    else:
        sys_prompt = f"""
        Kamu News Anchor Senior.
        Data: {context}
        Tugas: TULIS TEKS BERITA JADI. Investigatif.
        
        OUTPUT (Markdown):
        ### 📺 NASKAH BERITA (News)
        * **Headline:** (Judul Bombastis).
        * **Lead:** (1 Kalimat pembuka).
        * **Fakta:** (Poin-poin 5W+1H).
        * **Closing:** (Pertanyaan ke penonton).
        
        ### 🐦 THREAD X
        * Tweet 1: (Fakta Utama).
        * Tweet 2: (Data).
        """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"Buat konten: {topic}"}
            ],
            temperature=0.6,
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
    keywords = ['war', 'conflict', 'military', 'attack', 'politics', 'crisis', 'tension', 'government']
    
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
    return results

def get_tech_list(history):
    print("Scraping Tech News...")
    url = "https://www.gsmarena.com/rss-news-reviews.php3" 
    results = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if entry.title not in history:
                results.append({"title": entry.title, "link": entry.link, "source": "GSMArena"})
                history.append(entry.title)
                if len(results) >= 5: break
    except: pass
    return results

def get_trending_indo(history):
    print("Scraping Indo News...")
    url = "https://news.google.com/rss?ceid=ID:id&hl=id&gl=ID"
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if entry.title not in history:
                history.append(entry.title)
                return entry.title, entry.link
    except: pass
    return None, None

# --- 5. DISCORD SENDERS ---
def send_discord_text(webhook_url, title, content, color):
    if not content: return
    if len(content) > 4000: content = content[:4000] + "..."
    embed = {"title": title, "description": content, "color": color}
    requests.post(webhook_url, json={"username": "AI Assistant", "embeds": [embed]})

def send_discord_list(webhook_url, title, items, color):
    if not items: return
    embeds = []
    for item in items:
        embeds.append({
            "title": item['title'],
            "url": item['link'],
            "description": f"Sumber: {item['source']}",
            "color": color
        })
    # Kirim list berita (Max 10 per pesan)
    payload = {"username": "News Feed", "content": f"**{title}**", "embeds": embeds[:10]}
    requests.post(webhook_url, json=payload)

# --- MAIN LOGIC ---
def main():
    print("🚀 Bot Started...")
    history = load_history()
    discord_url = os.getenv("DISCORD_WEBHOOK")
    
    # --- 1. AMBIL DATA ---
    geo_list = get_geopolitics_list(history)
    tech_list = get_tech_list(history)
    indo_title, indo_link = get_trending_indo(history)
    
    # --- 2. KIRIM LIST BERITA DULU (Agar tidak hilang) ---
    if discord_url:
        if geo_list: 
            send_discord_list(discord_url, "🌍 Geopolitics News", geo_list, 15158332) # Merah
        if tech_list: 
            send_discord_list(discord_url, "📱 Tech News Feed", tech_list, 3447003) # Biru

    # --- 3. AI SECTION (JALANKAN KEDUANYA) ---
    
    # A. AI GENERAL NEWS (Indo/Politik)
    if indo_title:
        print(f"🧠 AI General Processing: {indo_title}")
        ai_news = generate_content_strategy(indo_title, 'GENERAL')
        if discord_url:
            send_discord_text(discord_url, f"📺 AI News Script: {indo_title}", ai_news, 16776960) # Kuning

    # B. AI TECH (Gadget)
    # Ambil topik tech dari list tech yang baru discrape (jika ada)
    if tech_list:
        tech_topic = tech_list[0]['title']
        print(f"🧠 AI Tech Processing: {tech_topic}")
        ai_tech = generate_content_strategy(tech_topic, 'TECH')
        if discord_url:
            send_discord_text(discord_url, f"📱 AI Tech Script: {tech_topic}", ai_tech, 5763719) # Hijau Teal

    # --- 4. SIMPAN ---
    save_history(history)
    print("✅ Done!")

if __name__ == "__main__":
    main()
