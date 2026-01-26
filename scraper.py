import feedparser
import requests
from bs4 import BeautifulSoup
import datetime

def get_geopolitics_news():
    print("Scraping Geopolitics news...")
    # Using Al Jazeera RSS Feed
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
        # Fallback to first 5 if no keywords found
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
        
        # GSMArena results are usually in a div with class 'makers'
        makers_div = soup.find('div', class_='makers')
        if not makers_div:
            return "No iQOO products found or structure changed."
            
        items = makers_div.find_all('li')
        current_month = datetime.datetime.now().strftime("%B")
        current_year = datetime.datetime.now().strftime("%Y")
        
        results = []
        for item in items:
            name = item.find('span').text
            link = "https://www.gsmarena.com/" + item.find('a')['href']
            results.append(f"- {name} ({link})")
            if len(results) >= 3: # Limit to top 3
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

def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""
# 🤖 Daily Notification Bot Report
Generated at: {now}

## 🌍 Geopolitics (War/Conflict)
{get_geopolitics_news()}

## 📱 Tech (Latest iQOO Smartphones)
{get_iqoo_tech()}

## 💸 Deals (Reddit r/coupons)
{get_reddit_deals()}

---
*Automated by GitHub Actions*
"""
    
    print(report)
    
    # Save to a file for GitHub Actions to potentially use or just log it
    with open("latest_report.md", "w") as f:
        f.write(report)

if __name__ == "__main__":
    main()
