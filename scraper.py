import os
import datetime
import json
import requests
from bs4 import BeautifulSoup
import feedparser
import random
import time
from groq import Groq # Import Groq
# from duckduckgo_search import DDGS # DuckDuckGo Search tidak digunakan lagi

# Header User-Agent palsu untuk menghindari pemblokiran
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- Helper Functions ---

EMOTIONAL_PREFIXES = [
    '🔥 BREAKING:', 
    '🤯 GILA:', 
    '⚠️ WAJIB TAU:', 
    '📱 UPDATE PENTING:', 
    '💸 DISKON GEDE:', 
    '🤔 MENDING MANA?'
]

def generate_hook(original_title):
    """Memilih secara acak prefix emosional dan menggabungkannya dengan judul asli."""
    prefix = random.choice(EMOTIONAL_PREFIXES)
    return f"{prefix} {original_title}"

# Fungsi get_image dihapus sesuai permintaan

# --- AI Writer Function (Groq Integration) ---

def get_ai_content_idea(trending_topic, ai_persona="default"):
    """Menggunakan Groq (Llama 3) untuk membuat ide konten TikTok dari topik trending dengan persona tertentu."""
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        return "Error: GROQ_API_KEY tidak ditemukan."

    try:
        client = Groq(api_key=groq_api_key)
        
        system_prompt = ""
        prompt_template = ""

        if ai_persona == "AI_SEC":
            system_prompt = "Kamu adalah AI Security Researcher (White Hat Hacker). Gaya bahasamu analitis, tajam, dan penuh wawasan (Cybersecurity style)."
            prompt_template = f"""
            Dari topik riset keamanan AI berikut: "{trending_topic}", buatkan:
            
            🎣 5 HOOK: (Fokus ke celah keamanan/bahaya AI).
            📱 NASKAH TIKTOK/REELS: Jelaskan celah keamanannya (Exploit), bagaimana cara kerjanya (secara sederhana), dan dampaknya.
            🔒 MITIGATION: (Tips singkat cara mencegah serangan ini bagi developer).
            
            Gunakan bahasa gaul Indonesia.
            """
        else:
            # Default prompt untuk topik umum
            prompt_template = f"""
            Buatkan ide konten TikTok yang singkat, menarik, dan viral dari topik trending berikut: "{trending_topic}".
            Gunakan bahasa gaul Indonesia. Format outputnya harus:
            
            *Hook:* [Kalimat pembuka yang sangat menarik]
            *Pembahasan 1:* [Poin utama 1]
            *Pembahasan 2:* [Poin utama 2]
            *Pembahasan 3:* [Poin utama 3]
            """
        
        messages = []
        if system_prompt: messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt_template})

        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile", # Menggunakan model Llama 3.3 terbaru yang stabil
        )
        
        return chat_completion.choices[0].message.content.strip()
        
    except Exception as e:
        return f"Error AI Writer (Groq): {e}"

# --- Scraping Functions ---

def get_google_news_id():
    print("Scraping Google News Indonesia via RSS (Pengganti Pytrends)...")
    url = "https://news.google.com/rss?ceid=ID:id&hl=id&gl=ID"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        feed = feedparser.parse(response.content)
        news_list = []
        
        for entry in feed.entries:
            news_list.append(f"- {entry.title} ([Link]({entry.link}))")
            if len(news_list) >= 5: break
            
        # Ambil judul berita pertama untuk AI Writer
        top_topic = feed.entries[0].title if feed.entries else None
        
        return "\n".join(news_list) if news_list else "Tidak ada berita utama ditemukan saat ini.", top_topic
    except Exception as e:
        return f"Error scraping Google News ID: {str(e)}", None

def get_geopolitics_news():
    print("Scraping Geopolitics news from multiple sources...")
    RSS_SOURCES = {
        "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "Google News (Geopolitics)": "https://news.google.com/rss/search?q=geopolitics"
    }
    all_news = []
    keywords = ['war', 'conflict', 'military', 'battle', 'army', 'attack', 'strike', 'geopolitics', 'tension']
    
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
                        "source": source_name,
                        "image": None # Gambar dihapus
                    })
                    count += 1
                if count >= 3: break
        except Exception as e:
            print(f"Error scraping {source_name}: {e}")
            
    return all_news

def get_tech_news():
    print("Scraping GSMArena for latest device news with brand filter...")
    url = "https://www.gsmarena.com/news.php3"
    results = []
    keywords = ['announced', 'released', 'coming soon', 'TKDN', 'launch', 'review', 'leak']
    brand_filter = ['Samsung', 'Apple', 'iPhone', 'Xiaomi', 'Redmi', 'Poco', 'Infinix', 'iQOO', 'Realme', 'Pixel', 'Asus', 'Rog']
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('div', class_='news-item')
        
        for item in items:
            title_tag = item.find('h3')
            link_tag = item.find('a')
            
            if title_tag and link_tag:
                title = title_tag.text.strip()
                link = "https://www.gsmarena.com/" + link_tag['href']
                
                is_relevant_keyword = any(kw.lower() in title.lower() for kw in keywords)
                is_relevant_brand = any(brand.lower() in title.lower() for brand in brand_filter)
                
                if is_relevant_keyword and is_relevant_brand:
                    results.append({
                        "title": title,
                        "link": link,
                        "source": "GSMArena",
                        "image": None # Gambar dihapus
                    })
                if len(results) >= 5: break
    except Exception as e:
        print(f"Error scraping GSMArena: {e}")
        
    return results

def get_youtube_monitor():
    print("Monitoring YouTube Competitors via RSS...")
    YOUTUBE_RSS = {
        "GadgetIn": "https://www.youtube.com/feeds/videos.xml?channel_id=UCo2Wz_pI_I_Lz5t7i6sCqNw",
        "Jagat Review": "https://www.youtube.com/feeds/videos.xml?channel_id=UCbyVnlQdFIcdViuoPIPK68A",
        "DroidLime": "https://www.youtube.com/feeds/videos.xml?user=droidlime"
    }
    all_videos = []
    for channel_name, url in YOUTUBE_RSS.items():
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                # thumbnail_url = entry.media_thumbnail[0]['url'] if 'media_thumbnail' in entry and entry.media_thumbnail else None
                
                all_videos.append({
                    "title": entry.title,
                    "link": entry.link,
                    "source": channel_name,
                    "image": None # Gambar dihapus
                })
                count += 1
                if count >= 2: break
        except Exception as e:
            print(f"Error monitoring {channel_name}: {e}")
            
    return all_videos

def get_reddit_deals():
    print("Scraping Reddit r/coupons via RSS...")
    url = "https://www.reddit.com/r/coupons/.rss"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        feed = feedparser.parse(response.content)
        deals = []
        keywords = ['100% off', 'free', 'coupon', 'deal', 'promo']
        for entry in feed.entries:
            if any(kw.lower() in entry.title.lower() for kw in keywords):
                deals.append(f"- {entry.title} ([Link]({entry.link}))")
            if len(deals) >= 5: break
        return "\n".join(deals) if deals else "Tidak ada penawaran ditemukan."
    except Exception as e:
        return f"Error Reddit: {str(e)}"

def get_ai_security_news():
    print("Scraping AI Security & LLM Jailbreak Research via Google News RSS...")
    query = "LLM Jailbreak OR Prompt Injection OR AI Adversarial Attack OR Red Teaming AI"
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    results = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        feed = feedparser.parse(response.content)
        for entry in feed.entries:
            results.append({
                "title": entry.title,
                "link": entry.link,
                "source": "Google News (AI Security)",
                "image": None # Gambar dihapus
            })
            if len(results) >= 5: break
    except Exception as e:
        print(f"Error scraping AI Security News: {e}")
    return results

# --- Discord Sender Functions ---

def send_discord_embeds(webhook_url, title, items, color=3447003):
    if not items: return
    embeds = []
    for item in items:
        hooked_title = generate_hook(item['title'])
        embed = {
            "title": hooked_title,
            "url": item['link'],
            "description": f"Sumber: {item['source']}",
            "color": color,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "footer": {"text": "Daily Notifier Bot"},
        }
        # Baris untuk 'image' dihapus sesuai permintaan
        embeds.append(embed)
        
    payload = {
        "username": "Daily Notifier Bot",
        "content": f"**{title}**",
        "embeds": embeds[:10]
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=15)
        response.raise_for_status()
        print(f"Successfully sent {title} to Discord.")
    except Exception as e:
        print(f"Failed to send {title} to Discord: {e}")

def send_discord_text(webhook_url, title, content):
    if not content: return
    payload = {
        "username": "Daily Notifier Bot",
        "content": f"**{title}**\n{content}"
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=15)
        response.raise_for_status()
        print(f"Successfully sent {title} (Text) to Discord.")
    except Exception as e:
        print(f"Failed to send {title} (Text) to Discord: {e}")

def send_to_telegram(token, chat_id, content):
    print("Sending to Telegram...")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": content, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        print("Successfully sent to Telegram.")
    except Exception as e:
        print(f"Failed to send to Telegram: {e}")

# --- Main Logic ---

def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Ambil Data
    google_news_id_text, top_topic_id = get_google_news_id()
    geopolitics = get_geopolitics_news()
    tech = get_tech_news()
    ai_security = get_ai_security_news() # Fitur baru
    youtube = get_youtube_monitor()
    deals = get_reddit_deals()
    
    # 2. Tentukan Topik Utama untuk AI Writer (Safety Net)
    ai_topic = top_topic_id
    ai_persona = "default"
    if not ai_topic and ai_security: # Prioritaskan AI Security jika ada
        ai_topic = ai_security[0]['title']
        ai_persona = "AI_SEC"
    elif not ai_topic and geopolitics:
        ai_topic = geopolitics[0]['title']
    elif not ai_topic and tech:
        ai_topic = tech[0]['title']
    
    # 3. AI Writer
    ai_idea = "Tidak ada topik trending untuk diolah AI."
    if ai_topic:
        ai_idea = get_ai_content_idea(ai_topic, ai_persona)
    
    # 4. Format Laporan Teks (untuk file lokal dan Telegram)
    geo_text = "\n".join([f"- {item['title']} ([Link]({item['link']}))" for item in geopolitics])
    tech_text = "\n".join([f"- {item['title']} ([Link]({item['link']}))" for item in tech])
    ai_sec_text = "\n".join([f"- {item['title']} ([Link]({item['link']}))" for item in ai_security])
    yt_text = "\n".join([f"- {item['source']}: {item['title']} ([Link]({item['link']}))" for item in youtube])
    
    report = f"""
# 🤖 Daily Notification Bot Report
Generated at: {now}

## 🧠 AI Content Idea (Top Topic: {ai_topic or 'N/A'})
{ai_idea}

## 🔥 Sedang Trending di Indonesia
{google_news_id_text}

## 🌍 Geopolitics (Multi-Source)
{geo_text}

## 📱 Tech News (GSMArena Latest Devices - Filtered)
{tech_text}

## 🔒 AI Security & LLM Jailbreak Research
{ai_sec_text}

## 📺 YouTube Monitor
{yt_text}

## 💸 Deals (Reddit r/coupons via RSS)
{deals}

---
*Automated by GitHub Actions*
"""
    
    # Simpan ke file lokal
    with open("latest_report.md", "w") as f:
        f.write(report)
    
    # 5. Kirim Notifikasi
    discord_webhook = os.getenv("DISCORD_WEBHOOK")
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if discord_webhook:
        # AI Writer (Paling Atas)
        send_discord_text(discord_webhook, "🧠 AI Content Idea", f"**Topik Utama:** {ai_topic or 'N/A'}\n\n{ai_idea}")
        time.sleep(1) # Safety Delay
        
        # Kirim Embeds (Visual)
        send_discord_embeds(discord_webhook, "🌍 Geopolitics News", geopolitics, color=16711680)
        time.sleep(1) # Safety Delay
        send_discord_embeds(discord_webhook, "📱 Tech News & Rumors", tech, color=3447003)
        time.sleep(1) # Safety Delay
        send_discord_embeds(discord_webhook, "🔒 AI Security & LLM Jailbreak Research", ai_security, color=5793266) # Warna ungu kebiruan
        time.sleep(1) # Safety Delay
        send_discord_embeds(discord_webhook, "📺 YouTube Competitor Monitor", youtube, color=16711935)
        time.sleep(1) # Safety Delay
        
        # Kirim Teks (Non-Visual)
        send_discord_text(discord_webhook, "🔥 Sedang Trending di Indonesia", google_news_id_text)
        time.sleep(1) # Safety Delay
        send_discord_text(discord_webhook, "💸 Deals & Coupons", deals)
        
    if telegram_token and telegram_chat_id:
        telegram_content = report
        if len(telegram_content) > 4096:
            telegram_content = telegram_content[:4000] + "\n\n... (Konten terpotong)"
        send_to_telegram(telegram_token, telegram_chat_id, telegram_content)

if __name__ == "__main__":
    main()
