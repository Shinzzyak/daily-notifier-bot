import os
import datetime
import json
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
    '🎓 KULIAH GRATIS:', 
    '🤯 FULL FUNDED:', 
    '⚠️ BURUAN DAFTAR:', 
    '🌍 BEASISWA LUAR NEGERI:', 
    '💸 BIAYA 0 RUPIAH:', 
    '🤔 MAU KULIAH GRATIS?'
]

def generate_hook(original_title):
    """Memilih secara acak prefix emosional dan menggabungkannya dengan judul asli."""
    prefix = random.choice(EMOTIONAL_PREFIXES)
    return f"{prefix} {original_title}"

def get_image(url):
    """Mencari meta tag og:image dari URL berita."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        meta_image = soup.find("meta", property="og:image")
        if meta_image:
            return meta_image["content"]
    except Exception as e:
        print(f"Gagal mengambil gambar dari {url}: {e}")
    return None

# --- AI Scholarship Advisor (Groq Integration) ---

def get_ai_scholarship_advisor(scholarship_topic):
    """Menggunakan Groq (Llama 3) untuk memberikan ringkasan dan tips beasiswa."""
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        return "Error: GROQ_API_KEY tidak ditemukan."

    try:
        client = Groq(api_key=groq_api_key)
        
        system_prompt = "Kamu adalah Konsultan Beasiswa Luar Negeri yang ahli. Gaya bahasamu informatif, memotivasi, dan praktis."
        prompt_template = f"""
        Berdasarkan informasi beasiswa berikut: "{scholarship_topic}", buatkan:
        
        🎯 RINGKASAN: (Apa beasiswanya, untuk siapa, dan apa cakupannya).
        📝 SYARAT UTAMA: (Sebutkan 3-4 syarat paling penting).
        ⏳ DEADLINE & JADWAL: (Kapan pendaftaran dibuka/ditutup jika ada).
        💡 TIPS LOLOS: (Berikan 2 tips khusus agar peluang lolos besar).
        
        Gunakan bahasa Indonesia yang santai tapi profesional.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_template}
        ]

        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
        )
        
        return chat_completion.choices[0].message.content.strip()
        
    except Exception as e:
        return f"Error AI Advisor (Groq): {e}"

# --- Scraping Functions ---

def get_mext_scholarship():
    print("Scraping MEXT Scholarship (Embassy of Japan)...")
    url = "https://www.id.emb-japan.go.jp/itpr_id/sch_gakubu.html"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Mencari informasi jadwal pendaftaran
        content = soup.get_text()
        
        # Logika sederhana untuk mendeteksi status pendaftaran
        status = "Belum Diketahui / Cek Link"
        if "Masa Pendaftaran" in content:
            # Mencoba mengekstrak baris pendaftaran
            lines = content.split('\n')
            for line in lines:
                if "Masa Pendaftaran" in line:
                    status = line.strip()
                    break
        
        return {
            "title": "Beasiswa MEXT (Monbukagakusho) - Gakubu (S1)",
            "link": url,
            "source": "Embassy of Japan",
            "status": status,
            "image": "https://www.id.emb-japan.go.jp/img/mext_logo.png" # Placeholder logo
        }
    except Exception as e:
        print(f"Error scraping MEXT: {e}")
        return None

def get_international_scholarships():
    print("Scraping International Scholarships via Google News RSS...")
    # Query untuk beasiswa full funded terbaru
    query = 'scholarship "fully funded" OR "full scholarship" OR "beasiswa penuh" 2025 2026'
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=id&gl=ID&ceid=ID:id"
    results = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        feed = feedparser.parse(response.content)
        for entry in feed.entries:
            results.append({
                "title": entry.title,
                "link": entry.link,
                "source": "Google News (Scholarships)",
                "image": get_image(entry.link)
            })
            if len(results) >= 5: break
    except Exception as e:
        print(f"Error scraping International Scholarships: {e}")
    return results

def get_scholarship_tab_news():
    print("Scraping ScholarshipTab for Fully Funded opportunities...")
    url = "https://www.scholarshiptab.com/fully-funded"
    results = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Mencari link beasiswa di halaman fully funded
        items = soup.find_all('h2') # Biasanya judul beasiswa ada di h2
        for item in items:
            link_tag = item.find('a')
            if link_tag:
                title = link_tag.text.strip()
                link = link_tag['href']
                if not link.startswith('http'):
                    link = "https://www.scholarshiptab.com" + link
                
                results.append({
                    "title": title,
                    "link": link,
                    "source": "ScholarshipTab",
                    "image": None
                })
            if len(results) >= 5: break
    except Exception as e:
        print(f"Error scraping ScholarshipTab: {e}")
    return results

# --- Discord Sender Functions ---

def send_discord_embeds(webhook_url, title, items, color=3066993):
    if not items: return
    embeds = []
    for item in items:
        hooked_title = generate_hook(item['title'])
        description = f"Sumber: {item['source']}"
        if 'status' in item:
            description += f"\n**Status/Jadwal:** {item['status']}"
            
        embed = {
            "title": hooked_title,
            "url": item['link'],
            "description": description,
            "color": color,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "footer": {"text": "Scholarship Tracker Bot"},
        }
        if item.get('image'):
            embed["image"] = {"url": item['image']}
        embeds.append(embed)
        
    payload = {
        "username": "Scholarship Tracker Bot",
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
        "username": "Scholarship Tracker Bot",
        "content": f"**{title}**\n{content}"
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=15)
        response.raise_for_status()
        print(f"Successfully sent {title} (Text) to Discord.")
    except Exception as e:
        print(f"Failed to send {title} (Text) to Discord: {e}")

# --- Main Logic ---

def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Ambil Data
    mext = get_mext_scholarship()
    intl_scholarships = get_international_scholarships()
    tab_scholarships = get_scholarship_tab_news()
    
    # 2. AI Advisor (Gunakan MEXT atau beasiswa pertama sebagai input)
    advisor_topic = ""
    if mext:
        advisor_topic = f"{mext['title']} - {mext['status']}"
    elif intl_scholarships:
        advisor_topic = intl_scholarships[0]['title']
    
    ai_advice = "Tidak ada informasi beasiswa untuk dianalisis AI."
    if advisor_topic:
        ai_advice = get_ai_scholarship_advisor(advisor_topic)
    
    # 3. Format Laporan Teks (Lokal)
    report = f"""
# 🎓 Scholarship Tracker Report
Generated at: {now}

## 🧠 AI Scholarship Advisor
{ai_advice}

## 🇯🇵 Beasiswa MEXT Jepang (Special Monitor)
- **Judul:** {mext['title'] if mext else 'N/A'}
- **Link:** {mext['link'] if mext else 'N/A'}
- **Status:** {mext['status'] if mext else 'N/A'}

## 🌍 Beasiswa Internasional Terbaru (Full Funded)
"""
    for item in intl_scholarships:
        report += f"- {item['title']} ([Link]({item['link']}))\n"
        
    report += "\n## 📚 Peluang Beasiswa Lainnya (ScholarshipTab)\n"
    for item in tab_scholarships:
        report += f"- {item['title']} ([Link]({item['link']}))\n"
        
    report += "\n--- \n*Automated by GitHub Actions*"
    
    with open("latest_report.md", "w") as f:
        f.write(report)
    
    # 4. Kirim Notifikasi
    discord_webhook = os.getenv("DISCORD_WEBHOOK")
    
    if discord_webhook:
        # AI Advisor
        send_discord_text(discord_webhook, "🧠 AI Scholarship Advisor", ai_advice)
        time.sleep(1)
        
        # MEXT Special
        if mext:
            send_discord_embeds(discord_webhook, "🇯🇵 Beasiswa MEXT Jepang", [mext], color=15158332)
            time.sleep(1)
            
        # International
        send_discord_embeds(discord_webhook, "🌍 Beasiswa Internasional (Full Funded)", intl_scholarships, color=3066993)
        time.sleep(1)
        
        # ScholarshipTab
        send_discord_embeds(discord_webhook, "📚 Peluang Beasiswa Lainnya", tab_scholarships, color=1752220)

if __name__ == "__main__":
    main()
