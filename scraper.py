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
        return full_text[:6000]
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
            {"role": "system", "content": "Kamu Gaming & Tech Scraper. Cari bocoran skin/hero, tanggal rilis, harga diamond, buff/nerf, dan reaksi komunitas. Cari juga nama YouTuber yang sudah review jika ada."},
            {"role": "user", "content": f"Cari info lengkap: {topic}"}
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

# --- 3. GROQ WRITER ---
def generate_content_strategy(topic, category='GENERAL'):
    research_data = research_with_perplexity(topic)
    context = research_data if research_data else f"Judul: {topic}"

    groq_key = os.getenv('GROQ_API_KEY')
    if not groq_key: return None
    
    client = Groq(api_key=groq_key)

    # --- SETUP PROMPT BERDASARKAN KATEGORI ---
    if category == 'GAMING':
        sys_prompt = f"""
        Kamu Content Creator Mobile Legends (Ala Leaker Terpercaya/AceUnyil/Dafrixkun).
        Data Riset: {context}
        
        Tugas: Buat konten Bocoran/Update MLBB yang HYPE abis.
        Gunakan istilah: OP, Buff, Nerf, Revamp, Gacha, Diamond, Pity System.
        
        OUTPUT WAJIB (Markdown):
        ### 🎣 5 HOOK GAMING VIRAL
        1. Hype: (Misal: "Skin Collector Bulan Ini Gila Banget!")
        2. Fear/FOMO: (Misal: "Jangan Gacha Dulu Sebelum Nonton Ini!")
        3. Gameplay: (Fokus ke skill baru).
        4. Wallet: (Bahas harga diamond).
        5. Savage: (Pendapat jujur).
        
        ### 📱 NASKAH TIKTOK (Gaya Cepat)
        * Hook: ...
        * Info Skin/Hero: (Nama, Tier, Tanggal Rilis).
        * Efek Visual: (Jelaskan partikel skill/ultinya).
        * Harga: (Perkiraan Diamond).
        * Closing: (Saran: Tabung atau Skip?).
        
        ### 🎨 IMAGE PROMPT (Wajib Keren)
        * Prompt: (Bahasa Inggris. Deskripsikan Hero/Skin dengan gaya 'Splash Art', cinematic lighting, 4k, mobile legends style).
        
        ### 📸 CAPTION IG & X
        * Caption: (Pendek, padat, hashtag #MLBB #MobileLegendsIndonesia).
        * Tweet: (Info singkat leak).
        """
    elif category == 'TECH':
        sys_prompt = f"""
        Kamu Content Creator Tech (Ala GadgetIn).
        Data Riset: {context}
        Tugas: Review Gadget/HP.
        
        OUTPUT WAJIB (Markdown):
        ### 🎣 5 HOOK VIRAL
        1. Fear: ...
        2. Curiosity: ...
        3. Price: ...
        4. Versus: ...
        5. Savage: ...
        
        ### 📱 NASKAH TIKTOK
        * Hook: ...
        * Isi: (3 Poin Spesifikasi).
        * Closing: ...

        ### 🎨 IMAGE PROMPT
        * Prompt: (Bahasa Inggris untuk Thumbnail YouTube/Tech).
        
        ### 📸 INSTAGRAM & X
        * Caption IG: ...
        * Tweet: ...
        """
    else: # GENERAL NEWS
        sys_prompt = f"""
        Kamu News Anchor Senior.
        Data Riset: {context}
        Tugas: Berita Terkini.
        
        OUTPUT WAJIB (Markdown):
        ### 🎣 5 LEAD BERITA
        1. Breaking: ...
        2. Emosional: ...
        3. Data: ...
        4. Quote: ...
        5. Kontroversi: ...
        
        ### 📺 NASKAH BERITA
        * Lead: ...
        * Kronologi: ...
        * Closing: ...

        ### 🎨 IMAGE PROMPT
        * Prompt: (Bahasa Inggris untuk Ilustrasi Berita).
        
        ### 📸 INSTAGRAM & X
        * Caption IG: ...
        * Thread X: ...
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
        print(f"Groq Error: {e}")
        return None

# --- 4. NOTION INTEGRATION ---
def save_to_notion(title, content, category, link):
    token = os.getenv('NOTION_API_KEY')
    db_id = os.getenv('NOTION_DATABASE_ID')
    
    if not token or not db_id: return

    print(f"📝 Notion: {title}...")
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    
    chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
    children = []
    
    if link:
        children.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"🔗 Sumber: {link}", "link": {"url": link}}}]}})
    
    for chunk in chunks:
        children.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}})

    payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "Category": {"select": {"name": category}} 
        },
        "children": children
    }

    try:
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code != 200:
            del payload["properties"]["Category"]
            requests.post(url, json=payload, headers=headers)
    except: pass

# --- 5. SCRAPERS ---
def get_mlbb_news(history):
    print("Scraping MLBB Leaks...")
    # Menggunakan Google News Search Query khusus MLBB
    url = "https://news.google.com/rss/search?q=Mobile+Legends+Bang+Bang+Update+OR+Skin+Leak+OR+Hero+Baru&hl=id&gl=ID&ceid=ID:id"
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if entry.title not in history:
                # Filter tambahan biar gak dapet berita turnamen doang
                keywords = ['skin', 'hero', 'patch', 'update', 'revamp', 'bocoran', 'leak', 'kolaborasi']
                if any(k in entry.title.lower() for k in keywords):
                    history.append(entry.title)
                    return entry.title, entry.link
    except: pass
    return None, None

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

# --- 6. DISCORD SENDERS ---
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
    
    # --- 1. AMBIL TOPIC ---
    tech_list = get_tech_list(history)
    indo_title, indo_link = get_trending_indo(history)
    mlbb_title, mlbb_link = get_mlbb_news(history) # <-- New Feature
    
    # Kirim Tech List ke Discord
    if discord_url and tech_list: 
        send_discord_list(discord_url, "📱 Tech News Feed", tech_list, 3447003)

    # --- 2. PROSES AI (BERURUTAN DENGAN JEDA) ---

    # A. MLBB LEAKS (Priority Gaming)
    if mlbb_title:
        print(f"🎮 AI Gaming: {mlbb_title}")
        ai_gaming = generate_content_strategy(mlbb_title, 'GAMING')
        if ai_gaming:
            if discord_url: send_discord_text(discord_url, f"🎮 MLBB Leaks: {mlbb_title}", ai_gaming, 10181046) # Ungu
            save_to_notion(mlbb_title, ai_gaming, "Gaming MLBB", mlbb_link)
        
        print("⏳ Jeda 60 detik (Safety)...")
        time.sleep(60)

    # B. TECH NEWS
    if tech_list:
        tech_topic = tech_list[0]['title']
        tech_link_url = tech_list[0]['link']
        print(f"📱 AI Tech: {tech_topic}")
        ai_tech = generate_content_strategy(tech_topic, 'TECH')
        if ai_tech:
            if discord_url: send_discord_text(discord_url, f"📱 Tech Kit: {tech_topic}", ai_tech, 5763719)
            save_to_notion(tech_topic, ai_tech, "Tech Gadget", tech_link_url)

        print("⏳ Jeda 60 detik (Safety)...")
        time.sleep(60)

    # C. GENERAL NEWS
    if indo_title:
        print(f"📺 AI News: {indo_title}")
        ai_news = generate_content_strategy(indo_title, 'GENERAL')
        if ai_news:
            if discord_url: send_discord_text(discord_url, f"📺 News Kit: {indo_title}", ai_news, 16776960)
            save_to_notion(indo_title, ai_news, "General News", indo_link)

    save_history(history)
    print("✅ Done!")

if __name__ == "__main__":
    main()
