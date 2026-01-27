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

def get_geopolitics_news():
    print("Scraping Geopolitics news from multiple sources...")
    
    # Daftar sumber RSS Geopolitik
    RSS_SOURCES = {
        "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "Google News (Geopolitics)": "https://news.google.com/rss/search?q=geopolitics"
    }
    
    all_news = []
    keywords = ['war', 'conflict', 'military', 'battle', 'army', 'attack', 'strike', 'geopolitics', 'tension']
    
    for source_name, url in RSS_SOURCES.items():
        try:
            # Menggunakan requests untuk mendapatkan konten RSS dengan headers
            response = requests.get(url, headers=HEADERS, timeout=15)
            feed = feedparser.parse(response.content)
            
            source_news = []
            for entry in feed.entries:
                title = entry.title
                link = entry.link
                
                # Filter berdasarkan kata kunci
                if any(keyword.lower() in title.lower() for keyword in keywords):
                    source_news.append(f"- {title} ([Link]({link}))")
                
                if len(source_news) >= 3: # Ambil 3 berita teratas dari setiap sumber
                    break
            
            if source_news:
                all_news.append(f"**{source_name}**:")
                all_news.extend(source_news)
            else:
                all_news.append(f"**{source_name}**: Tidak ada berita yang relevan ditemukan.")
                
        except Exception as e:
            all_news.append(f"**{source_name}**: Error scraping: {str(e)}")
            
    return "\n".join(all_news)

def get_tech_news():
    print("Scraping GSMArena for latest device news...")
    url = "https://www.gsmarena.com/news.php3"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Targetkan div yang berisi daftar berita
        # Struktur GSMArena menggunakan div dengan class 'news-item'
        items = soup.find_all('div', class_='news-item')
        if not items:
            return "Struktur GSMArena berubah atau tidak ada daftar berita."
        results = []
        keywords = ['announced', 'released', 'coming soon', 'TKDN', 'launch', 'review']
        
        for item in items:
            title_tag = item.find('h3')
            link_tag = item.find('a')
            
            if title_tag and link_tag:
                title = title_tag.text.strip()
                link = "https://www.gsmarena.com/" + link_tag['href']
                
                # Filter berdasarkan kata kunci
                if any(keyword.lower() in title.lower() for keyword in keywords):
                    results.append(f"- {title} ([Link]({link}))")
                
                if len(results) >= 5: # Ambil 5 berita teratas
                    break
        
        return "\n".join(results) if results else "Tidak ada berita perangkat terbaru yang relevan ditemukan."
    except Exception as e:
        return f"Error scraping GSMArena: {str(e)}"

def get_reddit_deals():
    print("Scraping Reddit r/coupons via RSS...")
    # Menggunakan RSS Feed yang lebih stabil
    url = "https://www.reddit.com/r/coupons/.rss"
    
    try:
        # Menggunakan feedparser langsung untuk RSS
        feed = feedparser.parse(url)
        
        deals = []
        keywords = ['100% off', 'free subscription', 'free', 'off', 'coupon', 'deal', 'promo']
        
        for entry in feed.entries:
            title = entry.title
            link = entry.link
            
            if any(kw.lower() in title.lower() for kw in keywords):
                deals.append(f"- {title} ([Link]({link}))")
            
            if len(deals) >= 5:
                break
                
        return "\n".join(deals) if deals else "Tidak ada penawaran spesifik yang relevan ditemukan baru-baru ini."
    except Exception as e:
        return f"Error scraping Reddit: {str(e)}"

def send_to_discord(webhook_url, content):
    print("Sending to Discord...")
    payload = {
        "username": "Daily Notifier Bot",
        "embeds": [
            {
                "title": "🤖 Daily Notification Report",
                "description": content[:4000], 
                "color": 3447003,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        ]
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=15)
        response.raise_for_status()
        print("Successfully sent to Discord.")
    except Exception as e:
        print(f"Failed to send to Discord: {e}")

def send_to_telegram(token, chat_id, content):
    print("Sending to Telegram...")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": content,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        print("Successfully sent to Telegram.")
    except Exception as e:
        print(f"Failed to send to Telegram: {e}")

def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    geopolitics = get_geopolitics_news()
    tech = get_tech_news()
    deals = get_reddit_deals()
    
    report = f"""
# 🤖 Daily Notification Bot Report
Generated at: {now}

## 🌍 Geopolitics (Multi-Source)
{geopolitics}

## 📱 Tech News (GSMArena Latest Devices)
{tech}

## 💸 Deals (Reddit r/coupons via RSS)
{deals}

---
*Automated by GitHub Actions*
"""
    
    # Simpan ke file lokal
    with open("latest_report.md", "w") as f:
        f.write(report)
    
    # Cek pengiriman notifikasi
    discord_webhook = os.getenv("DISCORD_WEBHOOK")
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    # Pastikan report tidak terlalu panjang untuk Telegram (max 4096 chars)
    telegram_content = report
    if len(telegram_content) > 4096:
        telegram_content = telegram_content[:4000] + "\n\n... (Konten terpotong karena batas Telegram)"
        
    if discord_webhook:
        send_to_discord(discord_webhook, report)
    
    if telegram_token and telegram_chat_id:
        send_to_telegram(telegram_token, telegram_chat_id, telegram_content)

if __name__ == "__main__":
    main()
