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
            {"role": "system", "content": "Kamu Data Scraper. Cari fakta valid, angka, spesifikasi, tanggal, dan kutipan penting. JANGAN BEROPINI."},
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

# --- 3. GROQ WRITER (MULTI-PLATFORM) ---
def generate_content_strategy(topic, category='GENERAL'):
    research_data = research_with_perplexity(topic)
    context = research_data if research_data else f"Judul: {topic} (Data minim, kembangkan dari judul)."

    groq_key = os.getenv('GROQ_API_KEY')
    if not groq_key: return "Error: GROQ_API_KEY missing."
    
    client = Groq(api_key=groq_key)

    # --- PROMPT BARU: WAJIB 3 PLATFORM ---
    if category == 'TECH':
        sys_prompt = f"""
        Kamu Content Creator Tech (Ala GadgetIn/David).
        Data Riset: {context}
        
        Tugas: Buat konten media sosial lengkap.
        
        OUTPUT WAJIB (Markdown):
        
        ### 📱 TIKTOK / REELS (Naskah)
        * **Visual:** (Saran visual, misal: Zoom ke kamera).
        * **Audio:** (Saran musik/sfx).
        * **Script:** (Dialog lengkap: Opening Hook -> Spesifikasi -> Kelebihan/Kekurangan -> Closing).
        
        ### 📸 INSTAGRAM (Feed/Carousel)
        * **Caption:** (Gaya review santai, estetik).
        * **Slide 1-3:** (Ide isi gambar slide).
        * **Hashtags:** (10 hashtag relevan).
        
        ### 🐦 X / TWITTER (Post)
        * **Tweet:** (Pendapat singkat, padat, dan "Savage" tentang produk ini).
        
        ### 💰 MARKET INSIGHT
        * **Verdict:** (BELI / TAHAN / SKIP).
        * **Alasan:** (Singkat).
        """
    else:
        sys_prompt = f"""
        Kamu Social Media Strategist untuk Portal Berita.
        Data Riset: {context}
        
        Tugas: Buat paket konten berita untuk 3 platform.
        
        OUTPUT WAJIB (Markdown):
        
        ### 📱 TIKTOK / REELS (Breaking News)
        * **Headline Video:** (Teks di layar).
        * **Script:** (Naskah 60 detik gaya News Anchor: Lead -> Fakta 1 -> Fakta 2 -> Closing).
        
        ### 📸 INSTAGRAM (Postingan)
        * **Headline Image:** (Teks untuk di gambar).
        * **Caption:** (Gaya editorial, deep dive, analitis, paragraf rapi).
        * **Hashtags:** (10 hashtag berita).
        
        ### 🐦 X / TWITTER (Thread Investigasi)
        * **Tweet 1:** (Hook Fakta Mengejutkan).
        * **Tweet 2:** (Data/Angka Pendukung).
        * **Tweet 3:** (Konteks/Kronologi).
        * **Tweet 4:** (Kesimpulan/Pertanyaan).
        """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"Buatkan konten: {topic}"}
            ],
            temperature=0.6,
            max_tokens=4096 # Token maksimal
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
    # Chunking pesan panjang
    chunks = [content[i:i+4000] for i in range(0, len(content), 4000)]
    for i, chunk in enumerate(chunks):
        title_part = title if i == 0 else f"{title} (Part {i+1})"
        embed = {"title": title_part, "description": chunk, "color": color}
        requests.post(webhook_url, json={"username": "AI Assistant", "embeds": [embed]})
        time.sleep(1)

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
    payload = {"username": "News Feed", "content": f"**{title}**", "embeds": embeds[:10]}
    requests.post(webhook_url, json=payload)

# --- MAIN LOGIC ---
def main():
    print("🚀 Bot Started...")
    history = load_history()
    discord_url = os.getenv("DISCORD_WEBHOOK")
    
    # 1. AMBIL DATA
    geo_list = get_geopolitics_list(history)
    tech_list = get_tech_list(history)
    indo_title, indo_link = get_trending_indo(history)
    
    # 2. KIRIM LIST BERITA
    if discord_url:
        if geo_list: send_discord_list(discord_url, "🌍 Geopolitics News", geo_list, 15158332)
        if tech_list: send_discord_list(discord_url, "📱 Tech News Feed", tech_list, 3447003)

    # 3. AI SECTION (DUAL ENGINE)
    # A. AI GENERAL
    if indo_title:
        print(f"🧠 AI General: {indo_title}")
        ai_news = generate_content_strategy(indo_title, 'GENERAL')
        if discord_url:
            send_discord_text(discord_url, f"📺 News Content Kit: {indo_title}", ai_news, 16776960)

    # B. AI TECH
    if tech_list:
        tech_topic = tech_list[0]['title']
        print(f"🧠 AI Tech: {tech_topic}")
        ai_tech = generate_content_strategy(tech_topic, 'TECH')
        if discord_url:
            send_discord_text(discord_url, f"📱 Tech Content Kit: {tech_topic}", ai_tech, 5763719)

    # 4. SIMPAN
    save_history(history)
    print("✅ Done!")

if __name__ == "__main__":
    main()
