import os
import datetime
import json
import requests
from bs4 import BeautifulSoup
import feedparser

# Header User-Agent palsu untuk menghindari pemblokiran
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

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
    trends_section = []
    report_section = []
    is_trends = False
    for line in lines:
        if line.startswith("## 🔥 Sedang Trending di Indonesia"):
            is_trends = True
            continue
        if line.startswith("## 🌍 Geopolitics"):
            is_trends = False
        if is_trends:
            if line.strip() and not line.startswith("#"):
                trends_section.append(line)
        else:
            report_section.append(line)
    embed_trends = {
        "title": "🔥 Sedang Trending di Indonesia",
        "description": "\n".join(trends_section).strip() or "Tidak ada data tren.",
        "color": 16761035,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    embed_report = {
        "title": "🤖 Daily Notification Report",
        "description": "\n".join(report_section)[:4000], 
        "color": 3447003,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    payload = {"username": "Daily Notifier Bot", "embeds": [embed_trends, embed_report]}
    try:
        response = requests.post(webhook_url, json=payload, timeout=15)
        response.raise_for_status()
        print("Successfully sent to Discord.")
    except Exception as e:
        print(f"Failed to send to Discord: {e}")

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

def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trends = get_google_trends()
    geopolitics = get_geopolitics_news()
    tech = get_tech_news()
    deals = get_reddit_deals()
    report = f"""
# 🤖 Daily Notification Bot Report
Generated at: {now}

## 🔥 Sedang Trending di Indonesia
{trends}

## 🌍 Geopolitics (Multi-Source)
{geopolitics}

## 📱 Tech News (GSMArena Latest Devices)
{tech}

## 💸 Deals (Reddit r/coupons via RSS)
{deals}

---
*Automated by GitHub Actions*
"""
    with open("latest_report.md", "w") as f: f.write(report)
    discord_webhook = os.getenv("DISCORD_WEBHOOK")
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    telegram_content = report
    if len(telegram_content) > 4096: telegram_content = telegram_content[:4000] + "\n\n... (Konten terpotong)"
    if discord_webhook: send_to_discord(discord_webhook, report)
    if telegram_token and telegram_chat_id: send_to_telegram(telegram_token, telegram_chat_id, telegram_content)

if __name__ == "__main__":
    main()
