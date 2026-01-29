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

# --- 3. GROQ WRITER ---
def generate_content_strategy(topic, category='GENERAL'):
    research_data = research_with_perplexity(topic)
    context = research_data if research_data else f"Judul: {topic}"

    groq_key = os.getenv('GROQ_API_KEY')
    if not groq_key: return None # Return None biar ketahuan error
    
    client = Groq(api_key=groq_key)

    if category == 'TECH':
        sys_prompt = f"""
        Kamu Content Creator Tech (Ala GadgetIn).
        Data Riset: {context}
        Tugas: Buat konten lengkap + Variasi Hook.
        
        OUTPUT WAJIB (Markdown):
        ### 🎣 5 HOOK VIRAL
        1. Fear: ...
        2. Curiosity: ...
        3. Price: ...
        4. Versus: ...
        5. Savage: ...
        
        ### 📱 NASKAH TIKTOK
        * Hook Pilihan: ...
        * Isi: (3 Poin Spesifikasi).
        * Closing: ...

        ### 🎨 IMAGE PROMPT
        * Prompt: (Bahasa Inggris untuk Thumbnail).
        
        ### 📸 INSTAGRAM & X
        * Caption IG: ...
        * Tweet: ...
        """
    else:
        sys_prompt = f"""
        Kamu News Anchor Senior.
        Data Riset: {context}
        Tugas: Buat konten berita lengkap.
        
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
        * Prompt: (Bahasa Inggris untuk Ilustrasi).
        
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

# --- 4. NOTION INTEGRATION (FITUR BARU) ---
def save_to_notion(title, content, category, link):
    token = os.getenv('NOTION_API_KEY')
    db_id = os.getenv('NOTION_DATABASE_ID')
    
    if not token or not db_id:
        print("⚠️ Notion Skip: API Key atau DB ID belum disetting.")
        return

    print(f"📝 Menyimpan ke Notion: {title}...")
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # Potong konten jadi chunk 2000 char (Notion Limit per block)
    chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
    children_blocks = []
    
    # Tambahkan Link Sumber di paling atas
    if link:
        children_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": f"🔗 Sumber Berita: {link}", "link": {"url": link}}}]
            }
        })
    
    # Masukkan Naskah AI
    for chunk in chunks:
        children_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            }
        })

    payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            # Opsional: Jika kolom 'Category' ada di Notion, ini akan terisi
            "Category": {"select": {"name": category}} 
        },
        "children": children_blocks
    }

    try:
        # Coba kirim dengan properti lengkap
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code != 200:
            # Jika gagal (mungkin kolom Category gak ada), coba kirim Title & Body saja
            print(f"Notion Retry (Simple Mode)... Error: {res.text}")
            del payload["properties"]["Category"]
            res = requests.post(url, json=payload, headers=headers)
            
        if res.status_code == 200:
            print("✅ Sukses simpan ke Notion!")
        else:
            print(f"❌ Gagal simpan ke Notion: {res.text}")
    except Exception as e:
        print(f"Notion Error: {e}")

# --- 5. SCRAPERS ---
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
    
    geo_list = get_geopolitics_list(history)
    tech_list = get_tech_list(history)
    indo_title, indo_link = get_trending_indo(history)
    
    if discord_url:
        if geo_list: send_discord_list(discord_url, "🌍 Geopolitics News", geo_list, 15158332)
        if tech_list: send_discord_list(discord_url, "📱 Tech News Feed", tech_list, 3447003)

    # A. AI GENERAL
    if indo_title:
        print(f"🧠 AI General: {indo_title}")
        ai_news = generate_content_strategy(indo_title, 'GENERAL')
        if ai_news:
            if discord_url: send_discord_text(discord_url, f"📺 News Kit: {indo_title}", ai_news, 16776960)
            save_to_notion(indo_title, ai_news, "General News", indo_link) # <-- KIRIM NOTION

    # SAFETY DELAY
    if indo_title and tech_list:
        print("⏳ Menunggu 60 detik (Safety Limit)...")
        time.sleep(60) 

    # B. AI TECH
    if tech_list:
        tech_topic = tech_list[0]['title']
        tech_link = tech_list[0]['link']
        print(f"🧠 AI Tech: {tech_topic}")
        ai_tech = generate_content_strategy(tech_topic, 'TECH')
        if ai_tech:
            if discord_url: send_discord_text(discord_url, f"📱 Tech Kit: {tech_topic}", ai_tech, 5763719)
            save_to_notion(tech_topic, ai_tech, "Tech", tech_link) # <-- KIRIM NOTION

    save_history(history)
    print("✅ Done!")

if __name__ == "__main__":
    main()
