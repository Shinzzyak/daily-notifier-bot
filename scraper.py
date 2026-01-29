import os
import requests
import feedparser
import json
import time
from bs4 import BeautifulSoup
from groq import Groq
from duckduckgo_search import DDGS

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

# --- 2. DEEP RESEARCH SYSTEM ---
def scrape_url_content(url):
    print(f"📖 Membaca isi artikel: {url}...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        full_text = " ".join([p.get_text() for p in paragraphs])
        return full_text[:6000] # Limit karakter biar token aman
    except Exception as e:
        print(f"Gagal baca artikel: {e}")
        return None

def research_fallback_deep(topic):
    print(f"⚠️ Mode Fallback Deep Scraping...")
    try:
        results = DDGS().text(topic, max_results=2)
        if not results: return None
        top_url = results[0]['href']
        full_content = scrape_url_content(top_url)
        if full_content and len(full_content) > 500:
            return f"[SUMBER: {top_url}]\nDATA ARTIKEL:\n{full_content}"
        else:
            return f"[SUMBER: DuckDuckGo]\nRINGKASAN:\n{results[0]['body']}"
    except Exception as e:
        print(f"Fallback Deep Error: {e}")
        return None

def research_with_perplexity(topic):
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key: return research_fallback_deep(topic)

    print(f"🕵️ Riset Premium (Perplexity): {topic}...")
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "Kamu Data Scraper. Cari fakta valid, angka, spesifikasi. JANGAN BEROPINI."},
            {"role": "user", "content": f"Cari data lengkap tentang: {topic}"}
        ]
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return research_fallback_deep(topic)
    except:
        return research_fallback_deep(topic)

# --- 3. GROQ WRITER (HOOK + IMAGE PROMPT) ---
def generate_content_strategy(topic, category='GENERAL'):
    research_data = research_with_perplexity(topic)
    context = research_data if research_data else f"Judul: {topic}"

    groq_key = os.getenv('GROQ_API_KEY')
    if not groq_key: return "Error: GROQ_API_KEY missing."
    
    client = Groq(api_key=groq_key)

    # --- PROMPT DIUPDATE DENGAN FITUR BARU ---
    if category == 'TECH':
        sys_prompt = f"""
        Kamu Content Creator Tech (Ala GadgetIn).
        Data Riset: {context}
        
        Tugas: Buat konten lengkap dengan Variasi Hook & Prompt Gambar.
        
        OUTPUT WAJIB (Markdown):
        
        ### 🎣 5 PILIHAN HOOK VIRAL (Pilih Satu)
        1. **Fear:** (Contoh: "Jangan beli HP ini sebelum...")
        2. **Curiosity:** (Contoh: "Fitur rahasia yang disembunyikan...")
        3. **Price Drop:** (Fokus ke harga).
        4. **Comparison:** (Bandingkan dgn kompetitor).
        5. **Savage:** (Pendapat jujur/pedas).
        
        ### 📱 NASKAH TIKTOK (Isi)
        * **Pilihan Hook:** (Pilih yang terbaik dari atas).
        * **Isi:** (3 Poin Spesifikasi/Fakta Utama).
        * **Closing:** (Kesimpulan: Worth it/Skip?).

        ### 🎨 AI IMAGE PROMPT (Untuk Thumbnail)
        * **Prompt:** (Tulis prompt bahasa Inggris detail untuk Bing Image Creator. Contoh: "A close up shot of [Product], cyberpunk lighting, youtube thumbnail style...").
        
        ### 📸 INSTAGRAM & X
        * **Caption IG:** (Review santai + Hashtags).
        * **Tweet Savage:** (1 Tweet opini tajam).
        """
    else:
        sys_prompt = f"""
        Kamu News Anchor Senior.
        Data Riset: {context}
        
        Tugas: Buat konten berita lengkap dengan Variasi Angle.
        
        OUTPUT WAJIB (Markdown):
        
        ### 🎣 5 PILIHAN LEAD BERITA (Hook)
        1. **Breaking:** (Gaya berita terkini).
        2. **Pertanyaan:** (Pancingan emosi audiens).
        3. **Data:** (Fokus ke angka mengejutkan).
        4. **Kutipan:** (Ambil quote tokoh jika ada).
        5. **Kontroversial:** (Sudut pandang debat).
        
        ### 📺 NASKAH BERITA (60 Detik)
        * **Lead:** (Pilih lead terbaik).
        * **Kronologi:** (Fakta 5W+1H).
        * **Closing:** (Pertanyaan interaktif).

        ### 🎨 AI IMAGE PROMPT (Ilustrasi Berita)
        * **Prompt:** (Tulis prompt bahasa Inggris untuk ilustrasi berita. Hindari nama tokoh spesifik jika melanggar policy, gunakan deskripsi jabatan/situasi. Contoh: "A dramatic meeting in a parliament hall, cinematic lighting...").
        
        ### 📸 INSTAGRAM & X
        * **Caption IG:** (Editorial deep dive + Hashtags).
        * **Thread X:** (3 Tweet Investigasi).
        """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"Buatkan konten: {topic}"}
            ],
            temperature=0.7,
            max_tokens=4096
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error Groq: {e}"

# --- 4. SCRAPERS ---
def get_geopolitics_list(history):
    print("Scraping Geopolitics...")
    sources = [("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"), ("BBC", "http://feeds.bbci.co.uk/news/world/rss.xml")]
    results = []
    keywords = ['war', 'conflict', 'military', 'politics', 'crisis', 'government']
    for src, url in sources:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if entry.title not in history and any(k in entry.title.lower() for k in keywords):
                    results.append({"title": entry.title, "link": entry.link, "source": src})
                    history.append(entry.title)
                    if len(results) >= 5: break
        except: continue
    return results

def get_tech_list(history):
    print("Scraping Tech...")
    results = []
    try:
        feed = feedparser.parse("https://www.gsmarena.com/rss-news-reviews.php3")
        for entry in feed.entries:
            if entry.title not in history:
                results.append({"title": entry.title, "link": entry.link, "source": "GSMArena"})
                history.append(entry.title)
                if len(results) >= 5: break
    except: pass
    return results

def get_trending_indo(history):
    print("Scraping Indo...")
    try:
        feed = feedparser.parse("https://news.google.com/rss?ceid=ID:id&hl=id&gl=ID")
        for entry in feed.entries:
            if entry.title not in history:
                history.append(entry.title)
                return entry.title, entry.link
    except: pass
    return None, None

# --- 5. DISCORD SENDERS ---
def send_discord_text(webhook_url, title, content, color):
    if not content: return
    chunks = [content[i:i+4000] for i in range(0, len(content), 4000)]
    for i, chunk in enumerate(chunks):
        t = title if i == 0 else f"{title} (Part {i+1})"
        requests.post(webhook_url, json={"username": "AI Assistant", "embeds": [{"title": t, "description": chunk, "color": color}]})
        time.sleep(1)

def send_discord_list(webhook_url, title, items, color):
    if not items: return
    embeds = [{"title": i['title'], "url": i['link'], "description": f"Sumber: {i['source']}", "color": color} for i in items[:10]]
    requests.post(webhook_url, json={"username": "News Feed", "content": f"**{title}**", "embeds": embeds})

# --- MAIN LOGIC ---
def main():
    print("🚀 Bot Started...")
    history = load_history()
    discord_url = os.getenv("DISCORD_WEBHOOK")
    
    geo_list = get_geopolitics_list(history)
    tech_list = get_tech_list(history)
    indo_title, _ = get_trending_indo(history)
    
    if discord_url:
        if geo_list: send_discord_list(discord_url, "🌍 Geopolitics News", geo_list, 15158332)
        if tech_list: send_discord_list(discord_url, "📱 Tech News Feed", tech_list, 3447003)

    # A. AI GENERAL
    if indo_title:
        print(f"🧠 AI General: {indo_title}")
        ai_news = generate_content_strategy(indo_title, 'GENERAL')
        if discord_url: send_discord_text(discord_url, f"📺 News Kit: {indo_title}", ai_news, 16776960)

    # --- SAFETY DELAY (PENTING BIAR GAK KENA LIMIT) ---
    if indo_title and tech_list:
        print("⏳ Menunggu 60 detik sebelum proses Tech (Safety Limit)...")
        time.sleep(60) 
    # --------------------------------------------------

    # B. AI TECH
    if tech_list:
        tech_topic = tech_list[0]['title']
        print(f"🧠 AI Tech: {tech_topic}")
        ai_tech = generate_content_strategy(tech_topic, 'TECH')
        if discord_url: send_discord_text(discord_url, f"📱 Tech Kit: {tech_topic}", ai_tech, 5763719)

    save_history(history)
    print("✅ Done!")

if __name__ == "__main__":
    main()
