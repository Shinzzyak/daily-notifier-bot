import os
import datetime
import json
import requests
from bs4 import BeautifulSoup
import feedparser
import random

# Header User-Agent palsu untuk menghindari pemblokiran
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- Fitur Baru: Hook Generator ---
EMOTIONAL_PREFIXES = [
    '🔥 BREAKING:', 
    '🤯 GILA:', 
    '⚠️ WAJIB TAU:', 
    '📱 UPDATE PENTING:', 
    '💸 DISKON GEDE:', 
    '🤔 MENDING MANA?'
]

def generate_hook(original_title):
    prefix = random.choice(EMOTIONAL_PREFIXES)
    return f"{prefix} {original_title}"
# ---------------------------------

def get_google_trends():
    print("Scraping Google Trends for Indonesia via RSS...")
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=ID"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        feed = feedparser.parse(response.content)
        trends_list = []
        for entry in feed.entries:
            trends_list.append(f"- {entry.title}")
            if len(trends_list) >= 5: break
        return "\n".join(trends_list) if trends_list else "Tidak ada tren harian yang ditemukan saat ini."
    except Exception as e:
        return f"Error scraping Google Trends: {str(e)}"

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
            source_news = []
            for entry in feed.entries:
                if any(keyword.lower() in entry.title.lower() for keyword in keywords):
                    source_news.append(f"- {entry.title} ([Link]({entry.link}))")
                if len(source_news) >= 3: break
            all_news.append(f"**{source_name}**:")
            all_news.extend(source_news if source_news else ["- Tidak ada berita relevan."])
        except Exception as e:
            all_news.append(f"**{source_name}**: Error: {str(e)}")
    return "\n".join(all_news)

def get_tech_news():
    print("Scraping GSMArena for latest device news...")
    url = "https://www.gsmarena.com/news.php3"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('div', class_='news-item')
        results = []
        keywords = ['announced', 'released', 'coming soon', 'TKDN', 'launch', 'review', 'leak']
        for item in items:
            title_tag = item.find('h3')
            link_tag = item.find('a')
            if title_tag and link_tag:
                title = title_tag.text.strip()
                if any(kw.lower() in title.lower() for kw in keywords):
                    results.append(f"- {title} ([Link](https://www.gsmarena.com/{link_tag['href']}))")
                if len(results) >= 5: break
        return "\n".join(results) if results else "Tidak ada berita terbaru ditemukan."
    except Exception as e:
        return f"Error GSMArena: {str(e)}"

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
            channel_videos = []
            for entry in feed.entries:
                channel_videos.append(f"- {entry.title} ([Link]({entry.link}))")
                if len(channel_videos) >= 2: break
            all_videos.append(f"**{channel_name}**:")
            all_videos.extend(channel_videos if channel_videos else ["- Tidak ada video baru ditemukan."])
        except Exception as e:
            all_videos.append(f"**{channel_name}**: Error: {str(e)}")
    return "\n".join(all_videos)

def get_reddit_deals():
    print("Scraping Reddit r/coupons via RSS...")
    url = "https://www.reddit.com/r/coupons/.rss"
    try:
        feed = feedparser.parse(url)
        deals = []
        keywords = ['100% off', 'free', 'coupon', 'deal', 'promo']
        for entry in feed.entries:
            if any(kw.lower() in entry.title.lower() for kw in keywords):
                deals.append(f"- {entry.title} ([Link]({entry.link}))")
            if len(deals) >= 5: break
        return "\n".join(deals) if deals else "Tidak ada penawaran ditemukan."
    except Exception as e:
        return f"Error Reddit: {str(e)}"

def send_to_discord(webhook_url, content):
    print("Sending to Discord...")
    lines = content.split('\n')
    trends_section, geopolitics_section, tech_section, youtube_section, deals_section = [], [], [], [], []
    current_section = None
    for line in lines:
        if line.startswith("## 🔥 Sedang Trending"): current_section = trends_section
        elif line.startswith("## 🌍 Geopolitics"): current_section = geopolitics_section
        elif line.startswith("## 📱 Tech News"): current_section = tech_section
        elif line.startswith("## 📺 YouTube Monitor"): current_section = youtube_section
        elif line.startswith("## 💸 Deals"): current_section = deals_section
        elif current_section is not None and line.strip() and not line.startswith("#"): current_section.append(line)

    def apply_hooks(section_lines):
        hooked = []
        for line in section_lines:
            if line.startswith("- "):
                parts = line[2:].split('([Link](')
                title = parts[0].strip()
                link = parts[1] if len(parts) > 1 else ''
                hooked.append(f"- {generate_hook(title)} ([Link]({link}" if link else f"- {generate_hook(title)}")
            else: hooked.append(line)
        return hooked

    geopolitics_section = apply_hooks(geopolitics_section)
    tech_section = apply_hooks(tech_section)
    youtube_section = apply_hooks(youtube_section)
    
    embed_research = {
        "title": "🔥 Riset Konten & Tren Harian",
        "description": f"**Sedang Trending di Indonesia**\n" + "\n".join(trends_section).strip() + 
                       f"\n\n**YouTube Competitor Monitor**\n" + "\n".join(youtube_section).strip(),
        "color": 16761035, "timestamp": datetime.datetime.utcnow().isoformat()
    }
    embed_report = {
        "title": "🤖 Daily Notification Report",
        "description": f"**Geopolitics (Multi-Source)**\n" + "\n".join(geopolitics_section).strip() + 
                       f"\n\n**Tech News (GSMArena Latest Devices)**\n" + "\n".join(tech_section).strip() +
                       f"\n\n**Deals (Reddit r/coupons via RSS)**\n" + "\n".join(deals_section).strip(),
        "color": 3447003, "timestamp": datetime.datetime.utcnow().isoformat()
    }
    payload = {"username": "Daily Notifier Bot", "embeds": [embed_research, embed_report]}
    try:
        response = requests.post(webhook_url, json=payload, timeout=15)
        response.raise_for_status()
        print("Successfully sent to Discord.")
    except Exception as e: print(f"Failed to send to Discord: {e}")

def send_to_telegram(token, chat_id, content):
    print("Sending to Telegram...")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": content, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        print("Successfully sent to Telegram.")
    except Exception as e: print(f"Failed to send to Telegram: {e}")

def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trends, geopolitics, tech, youtube, deals = get_google_trends(), get_geopolitics_news(), get_tech_news(), get_youtube_monitor(), get_reddit_deals()
    report = f"""
# 🤖 Daily Notification Bot Report
Generated at: {now}

## 🔥 Sedang Trending di Indonesia
{trends}

## 🌍 Geopolitics (Multi-Source)
{geopolitics}

## 📱 Tech News (GSMArena Latest Devices)
{tech}

## 📺 YouTube Monitor
{youtube}

## 💸 Deals (Reddit r/coupons via RSS)
{deals}

---
*Automated by GitHub Actions*
"""
    with open("latest_report.md", "w") as f: f.write(report)
    discord_webhook, telegram_token, telegram_chat_id = os.getenv("DISCORD_WEBHOOK"), os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    telegram_content = report
    if len(telegram_content) > 4096: telegram_content = telegram_content[:4000] + "\n\n... (Konten terpotong)"
    if discord_webhook: send_to_discord(webhook_url=discord_webhook, content=report)
    if telegram_token and telegram_chat_id: send_to_telegram(telegram_token, telegram_chat_id, telegram_content)

if __name__ == "__main__":
    main()
