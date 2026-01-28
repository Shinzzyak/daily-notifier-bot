import os
import datetime
import requests
from bs4 import BeautifulSoup
import feedparser
import random
import time
from groq import Groq

# Header User-Agent palsu untuk menghindari pemblokiran
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- Helper Functions ---
EMOTIONAL_PREFIXES = [
    '🔥 BREAKING:', '🤯 GILA:', '⚠️ WAJIB TAU:', 
    '📱 UPDATE PENTING:', '💸 DISKON GEDE:', '🤔 MENDING MANA?'
]

def generate_hook(original_title):
    """Memilih secara acak prefix emosional dan menggabungkannya dengan judul asli."""
    prefix = random.choice(EMOTIONAL_PREFIXES)
    return f"{prefix} {original_title}"

# --- AI Writer Function (Groq) ---
def get_ai_content_idea(trending_topic):
    """Menggunakan Groq (Llama 3.3) untuk membuat ide konten TikTok dari topik trending."""
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return "Error: GROQ_API_KEY tidak ditemukan."
    
    try:
        client = Groq(api_key=api_key)
        
        # Jeda singkat untuk keamanan rate limit
        time.sleep(1)
        
        prompt = f"""
        Buatkan ide konten TikTok yang singkat, menarik, dan viral dari topik trending berikut: "{trending_topic}".
        Gunakan bahasa gaul Indonesia. Format outputnya harus:
        
        *Hook:* [Kalimat pembuka yang sangat menarik]
        *Pembahasan 1:* [Poin utama 1]
        *Pembahasan 2:* [Poin utama 2]
        *Pembahasan 3:* [Poin utama 3]
        """
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return completion.choices[0].message.content.strip()
        
    except Exception as e:
        return f"Error AI Writer (Groq): {e}"

# --- Scraping Functions ---
def get_google_news_id():
    print("Scraping Google News Indonesia...")
    url = "https://news.google.com/rss?ceid=ID:id&hl=id&gl=ID"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        feed = feedparser.parse(response.content)
        news_list = []
        
        for entry in feed.entries[:5]:
            news_list.append(f"- {entry.title} ([Link]({entry.link}))")
            
        top_topic = feed.entries[0].title if feed.entries else None
        return "\n".join(news_list) if news_list else "Tidak ada berita utama ditemukan.", top_topic
    except Exception as e:
        return f"Error Google News ID: {str(e)}", None

def get_geopolitics_news():
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
                if any(keyword.lower() in entry.title.lower() for keyword in keywords):
                    all_news.append({
                        "title": entry.title,
                        "link": entry.link,
                        "source": source_name
                    })
                    count += 1
                if count >= 3: break
        except Exception as e:
            print(f"Error scraping {source_name}: {e}")
            
    return all_news

def get_tech_news():
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
                if any(brand.lower() in title.lower() for brand in brand_filter):
                    results.append({
                        "title": title,
                        "link": "https://www.gsmarena.com/" + link_tag['href'],
                        "source": "GSMArena"
                    })
                if len(results) >= 5: break
        return results
    except Exception as e:
        print(f"Error GSMArena: {e}")
        return []

def get_reddit_deals():
    print("Scraping Reddit r/coupons...")
    url = "https://www.reddit.com/r/coupons/new/.json?limit=25"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        data = response.json()
        posts = data['data']['children']
        deals = []
        keywords = ['100% off', 'free', 'coupon', 'deal']
        
        for post in posts:
            title = post['data']['title']
            link = "https://www.reddit.com" + post['data']['permalink']
            if any(kw.lower() in title.lower() for kw in keywords):
                deals.append(f"- {title} ([Link]({link}))")
            if len(deals) >= 5: break
        return "\n".join(deals) if deals else "Tidak ada penawaran ditemukan."
    except Exception as e:
        return f"Error Reddit: {str(e)}"

# --- Discord Sender Functions ---
def send_discord_embeds(webhook_url, title, items, color=3447003):
    if not items: return
    embeds = []
    for item in items:
        embeds.append({
            "title": generate_hook(item['title']),
            "url": item['link'],
            "description": f"Sumber: {item['source']}",
            "color": color,
            "footer": {"text": "Daily Notifier Bot"}
        })
        
    payload = {
        "username": "Daily Notifier Bot",
        "content": f"**{title}**",
        "embeds": embeds[:10]
    }
    requests.post(webhook_url, json=payload, timeout=15)

def send_discord_text(webhook_url, title, content):
    if not content: return
    payload = {
        "username": "Daily Notifier Bot",
        "content": f"**{title}**\n{content}"
    }
    requests.post(webhook_url, json=payload, timeout=15)

def send_to_telegram(token, chat_id, content):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": content, "parse_mode": "Markdown"}
    requests.post(url, json=payload, timeout=15)

# --- Main Logic ---
def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Ambil Data
    google_news_text, top_topic = get_google_news_id()
    geopolitics = get_geopolitics_news()
    tech = get_tech_news()
    deals = get_reddit_deals()
    
    # Fallback Topik AI
    ai_topic = top_topic
    if not ai_topic and geopolitics: ai_topic = geopolitics[0]['title']
    elif not ai_topic and tech: ai_topic = tech[0]['title']
    
    # 2. AI Writer (Groq)
    ai_idea = get_ai_content_idea(ai_topic) if ai_topic else "Tidak ada topik untuk AI."
    
    # 3. Format Laporan
    geo_text = "\n".join([f"- {item['title']} ([Link]({item['link']}))" for item in geopolitics])
    tech_text = "\n".join([f"- {item['title']} ([Link]({item['link']}))" for item in tech])
    
    report = f"""
# 🤖 Daily Notification Bot Report
Generated at: {now}

## 🧠 AI Content Idea (Topic: {ai_topic or 'N/A'})
{ai_idea}

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
    
    # 4. Kirim Notifikasi
    discord_webhook = os.getenv("DISCORD_WEBHOOK")
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if discord_webhook:
        send_discord_text(discord_webhook, "🧠 AI Content Idea", f"**Topik:** {ai_topic}\n\n{ai_idea}")
        send_discord_embeds(discord_webhook, "🌍 Geopolitics", geopolitics, color=16711680)
        send_discord_embeds(discord_webhook, "📱 Tech News", tech, color=3447003)
        send_discord_text(discord_webhook, "🔥 Trending Indonesia", google_news_text)
        send_discord_text(discord_webhook, "💸 Deals", deals)
        
    if telegram_token and telegram_chat_id:
        send_to_telegram(telegram_token, telegram_chat_id, report[:4000])

if __name__ == "__main__":
    main()
