import os
import datetime
import requests
from bs4 import BeautifulSoup
import feedparser
import random
import time
import json
from groq import Groq

# Header User-Agent palsu untuk menghindari pemblokiran
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

HISTORY_FILE = 'history.json'

# --- Memory Functions ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    # Batasi hanya 50 judul terakhir
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history[-50:], f, indent=4)

# --- Helper Functions ---
EMOTIONAL_PREFIXES = [
    '🔥 BREAKING:', '🤯 GILA:', '⚠️ WAJIB TAU:', 
    '📱 UPDATE PENTING:', '💸 DISKON GEDE:', '🤔 MENDING MANA?'
]

def generate_hook(original_title):
    prefix = random.choice(EMOTIONAL_PREFIXES)
    return f"{prefix} {original_title}"

# --- AI Writer Function (Groq) ---
def get_ai_content_idea(trending_topic, category='GENERAL'):
    """Menggunakan Groq (Llama 3.3) dengan persona yang disesuaikan kategori."""
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return "Error: GROQ_API_KEY tidak ditemukan."
    
    try:
        client = Groq(api_key=api_key)
        time.sleep(1) # Safety delay
        
        if category == 'TECH':
            system_prompt = """
            Persona: Tech Reviewer Profesional (Gaya ala GadgetIn/MKBHD).
            Tugas: Buat ide konten TikTok tentang gadget/HP terbaru.
            Fokus: Spesifikasi Inti, Harga, Kelebihan/Kekurangan.
            Market Insight: Bahas Resale Value atau bandingkan dengan kompetitor (Mending beli ini atau X?).
            Netizen Check: Prediksi keluhan netizen (Misal: 'Baterai boros', 'Mahal banget').
            Bahasa: Gaul Indonesia, santai tapi informatif.
            """
        else:
            system_prompt = """
            Persona: Senior News Anchor (Gaya Berwibawa & Investigatif).
            Tugas: Buat ringkasan berita viral dengan format 5W+1H.
            Fokus: Fakta utama, dampak kejadian, dan investigasi singkat.
            Bahasa: Formal tapi tetap menarik untuk audiens media sosial.
            """

        prompt = f"""
        Topik: "{trending_topic}"
        
        Buatkan ide konten TikTok yang viral. Format output:
        *Hook:* [Kalimat pembuka yang sangat menarik]
        *Pembahasan 1:* [Poin utama 1]
        *Pembahasan 2:* [Poin utama 2]
        *Pembahasan 3:* [Poin utama 3]
        """
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=600
        )
        return completion.choices[0].message.content.strip()
        
    except Exception as e:
        return f"Error AI Writer (Groq): {e}"

# --- Scraping Functions ---
def get_google_news_id(history):
    print("Scraping Google News Indonesia...")
    url = "https://news.google.com/rss?ceid=ID:id&hl=id&gl=ID"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        feed = feedparser.parse(response.content)
        news_list = []
        new_top_topic = None
        
        for entry in feed.entries:
            if entry.title not in history:
                if not new_top_topic: new_top_topic = entry.title
                news_list.append(f"- {entry.title} ([Link]({entry.link}))")
                history.append(entry.title)
            if len(news_list) >= 5: break
            
        return "\n".join(news_list) if news_list else "Tidak ada berita baru.", new_top_topic
    except Exception as e:
        return f"Error Google News ID: {str(e)}", None

def get_geopolitics_news(history):
    print("Scraping Geopolitics news...")
    RSS_SOURCES = {
        "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml"
    }
    all_news = []
    keywords = ['war', 'conflict', 'military', 'battle', 'army', 'attack', 'strike', 'geopolitics']
    
    for source_name, url in RSS_SOURCES.items():
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            feed = feedparser.parse(response.content)
            count = 0
            for entry in feed.entries:
                if entry.title not in history and any(keyword.lower() in entry.title.lower() for keyword in keywords):
                    all_news.append({
                        "title": entry.title,
                        "link": entry.link,
                        "source": source_name
                    })
                    history.append(entry.title)
                    count += 1
                if count >= 3: break
        except Exception as e:
            print(f"Error scraping {source_name}: {e}")
            
    return all_news

def get_tech_news(history):
    print("Scraping GSMArena...")
    url = "https://www.gsmarena.com/news.php3"
    results = []
    brand_filter = ['Samsung', 'Apple', 'iPhone', 'Xiaomi', 'Redmi', 'Poco', 'Infinix', 'iQOO', 'Realme', 'Pixel']
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('div', class_='news-item')
        
        for item in items:
            title_tag = item.find('h3')
            link_tag = item.find('a')
            if title_tag and link_tag:
                title = title_tag.text.strip()
                if title not in history and any(brand.lower() in title.lower() for brand in brand_filter):
                    results.append({
                        "title": title,
                        "link": "https://www.gsmarena.com/" + link_tag['href'],
                        "source": "GSMArena"
                    })
                    history.append(title)
                if len(results) >= 5: break
        return results
    except Exception as e:
        print(f"Error GSMArena: {e}")
        return []

def get_reddit_deals(history):
    print("Scraping Reddit r/coupons via RSS...")
    url = "https://www.reddit.com/r/coupons/new/.rss"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        feed = feedparser.parse(response.content)
        deals = []
        keywords = ['100% off', 'free', 'coupon', 'deal', 'promo']
        
        for entry in feed.entries:
            if entry.title not in history and any(kw.lower() in title.lower() for kw in keywords):
                deals.append(f"- {entry.title} ([Link]({entry.link}))")
                history.append(entry.title)
            if len(deals) >= 5: break
            
        return "\n".join(deals) if deals else "Tidak ada penawaran baru."
    except Exception as e:
        return f"Error Reddit (RSS): {str(e)}"

# --- Discord Sender Functions ---
def send_discord_text(webhook_url, title, content):
    if not content: return
    payload = {"username": "Daily Notifier Bot", "content": f"**{title}**\n{content}"}
    requests.post(webhook_url, json=payload, timeout=15)

def send_discord_embeds(webhook_url, title, items, color=3447003):
    if not items: return
    embeds = [{"title": generate_hook(item['title']), "url": item['link'], "description": f"Sumber: {item['source']}", "color": color} for item in items]
    payload = {"username": "Daily Notifier Bot", "content": f"**{title}**", "embeds": embeds[:10]}
    requests.post(webhook_url, json=payload, timeout=15)

def send_to_telegram(token, chat_id, content):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": content, "parse_mode": "Markdown"}
    requests.post(url, json=payload, timeout=15)

# --- Main Logic ---
def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history = load_history()
    
    # 1. Ambil Data
    google_news_text, top_news_topic = get_google_news_id(history)
    geopolitics = get_geopolitics_news(history)
    tech = get_tech_news(history)
    deals = get_reddit_deals(history)
    
    # 2. AI Writer (Smart Category)
    ai_reports = []
    if top_news_topic:
        ai_reports.append(f"**[NEWS]** {top_news_topic}\n{get_ai_content_idea(top_news_topic, 'GENERAL')}")
    if tech:
        top_tech = tech[0]['title']
        ai_reports.append(f"**[TECH]** {top_tech}\n{get_ai_content_idea(top_tech, 'TECH')}")
    
    ai_final_text = "\n\n---\n\n".join(ai_reports) if ai_reports else "Tidak ada berita baru untuk diolah AI."
    
    # 3. Format Laporan
    geo_text = "\n".join([f"- {item['title']} ([Link]({item['link']}))" for item in geopolitics])
    tech_text = "\n".join([f"- {item['title']} ([Link]({item['link']}))" for item in tech])
    
    report = f"""
# 🤖 Daily Notification Bot Report
Generated at: {now}

## 🧠 AI Content Ideas
{ai_final_text}

## 🔥 Trending Indonesia
{google_news_text}

## 🌍 Geopolitics
{geo_text}

## 📱 Tech News
{tech_text}

## 💸 Deals
{deals}

---
*Automated by GitHub Actions*
"""
    
    with open("latest_report.md", "w") as f:
        f.write(report)
    
    save_history(history)
    
    # 4. Kirim Notifikasi
    discord_webhook = os.getenv("DISCORD_WEBHOOK")
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if discord_webhook:
        if ai_reports: send_discord_text(discord_webhook, "🧠 AI Content Ideas", ai_final_text)
        if geopolitics: send_discord_embeds(discord_webhook, "🌍 Geopolitics", geopolitics, color=16711680)
        if tech: send_discord_embeds(discord_webhook, "📱 Tech News", tech, color=3447003)
        if google_news_text != "Tidak ada berita baru.": send_discord_text(discord_webhook, "🔥 Trending Indonesia", google_news_text)
        if deals != "Tidak ada penawaran baru.": send_discord_text(discord_webhook, "💸 Deals", deals)
        
    if telegram_token and telegram_chat_id:
        send_to_telegram(telegram_token, telegram_chat_id, report[:4000])

if __name__ == "__main__":
    main()
