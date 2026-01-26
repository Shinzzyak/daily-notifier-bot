import feedparser
import requests
from bs4 import BeautifulSoup
import datetime
import os
import json

def get_geopolitics_news():
    print("Scraping Geopolitics news...")
    url = "https://www.aljazeera.com/xml/rss/all.xml"
    feed = feedparser.parse(url)
    
    news_list = []
    keywords = ['war', 'conflict', 'military', 'battle', 'army']
    
    for entry in feed.entries:
        title = entry.title
        if any(keyword.lower() in title.lower() for keyword in keywords):
            news_list.append(f"- {title} ({entry.link})")
        if len(news_list) >= 5:
            break
            
    if not news_list:
        for entry in feed.entries[:5]:
            news_list.append(f"- {entry.title} ({entry.link})")
            
    return "\n".join(news_list)

def get_iqoo_tech():
    print("Scraping GSMArena for iQOO...")
    url = "https://www.gsmarena.com/results.php3?sQuickSearch=yes&sName=iQOO"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        makers_div = soup.find('div', class_='makers')
        if not makers_div:
            return "No iQOO products found or structure changed."
            
        items = makers_div.find_all('li')
        results = []
        for item in items:
            name = item.find('span').text
            link = "https://www.gsmarena.com/" + item.find('a')['href']
            results.append(f"- {name} ({link})")
            if len(results) >= 3:
                break
        
        return "\n".join(results) if results else "No recent iQOO products found."
    except Exception as e:
        return f"Error scraping GSMArena: {str(e)}"

def get_reddit_deals():
    print("Scraping Reddit r/coupons...")
    url = "https://www.reddit.com/r/coupons/new/.json"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        posts = data['data']['children']
        
        deals = []
        keywords = ['100% off', 'free subscription', 'free', 'off']
        
        for post in posts:
            title = post['data']['title']
            link = "https://www.reddit.com" + post['data']['permalink']
            if any(kw.lower() in title.lower() for kw in keywords):
                deals.append(f"- {title} ({link})")
            if len(deals) >= 5:
                break
                
        return "\n".join(deals) if deals else "No specific 100% off deals found recently."
    except Exception as e:
        return f"Error scraping Reddit: {str(e)}"

def send_to_discord(webhook_url, content):
    print("Sending to Discord...")
    payload = {
        "username": "Daily Notifier Bot",
        "embeds": [
            {
                "title": "🤖 Daily Notification Report",
                "description": content,
                "color": 3447003,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        ]
    }
    try:
        response = requests.post(webhook_url, json=payload)
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
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Successfully sent to Telegram.")
    except Exception as e:
        print(f"Failed to send to Telegram: {e}")

def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    geopolitics = get_geopolitics_news()
    tech = get_iqoo_tech()
    deals = get_reddit_deals()
    
    report = f"""
# 🤖 Daily Notification Bot Report
Generated at: {now}

## 🌍 Geopolitics (War/Conflict)
{geopolitics}

## 📱 Tech (Latest iQOO Smartphones)
{tech}

## 💸 Deals (Reddit r/coupons)
{deals}

---
*Automated by GitHub Actions*
"""
    
    # Save to file
    with open("latest_report.md", "w") as f:
        f.write(report)
    
    # Check for notifications
    discord_webhook = os.getenv("DISCORD_WEBHOOK")
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if discord_webhook:
        send_to_discord(discord_webhook, report)
    
    if telegram_token and telegram_chat_id:
        send_to_telegram(telegram_token, telegram_chat_id, report)
    elif telegram_token and not telegram_chat_id:
        print("TELEGRAM_TOKEN found but TELEGRAM_CHAT_ID is missing.")

if __name__ == "__main__":
    main()
