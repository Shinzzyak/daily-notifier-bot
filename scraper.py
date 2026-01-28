import os
import datetime
import requests
from bs4 import BeautifulSoup
import feedparser
import random
import time
import json
from groq import Groq

# --- KONFIGURASI ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
HISTORY_FILE = 'history.json'

# --- 1. MEMORY SYSTEM (Agar tidak bahas berita basi) ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    # Simpan 50 berita terakhir saja agar file tidak bengkak
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history[-50:], f, indent=4)

# --- 2. PERPLEXITY RESEARCHER (Otak Kiri/Pencari Fakta) ---
def research_with_perplexity(topic):
    """Mencari fakta mendalam tentang topik menggunakan Perplexity."""
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        return None # Lanjut tanpa riset jika key tidak ada

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Prompt Riset
    payload = {
        "model": "sonar-pro", # Model Online yang hemat & pintar
        "messages": [
            {
                "role": "system",
                "content": "Kamu adalah Jurnalis Investigasi. Cari fakta valid, angka spesifik, kronologi, dan kontroversi dari topik ini. JANGAN berikan saran. Fokus ke data mentah."
            },
            {
                "role": "user",
                "content": f"Riset topik ini: {topic}"
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"Perplexity Error: {response.text}")
            return None
    except Exception as e:
        print(f"Perplexity Exception: {e}")
        return None

# --- 3. GROQ WRITER (Otak Kanan/Penulis Kreatif) ---
def generate_content_strategy(topic, category='GENERAL'):
    """Menulis strategi konten berdasarkan hasil riset Perplexity."""
    
    # A. Lakukan Riset Dulu
    print(f"🕵️ Sedang meriset: {topic}...")
    research_data = research_with_perplexity(topic)
    
    # Jika Perplexity gagal/habis kuota, pakai data judul saja
    context_data = research_data if research_data else f"Judul Berita: {topic} (Maaf, riset mendalam gagal, kembangkan dari judul ini)."

    # B. Siapkan Groq
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        return "Error: GROQ_API_KEY missing."

    client = Groq(api_key=groq_api_key)

    # C. Tentukan Persona (Tech vs General)
    if category == 'TECH':
        system_prompt = f"""
        Kamu adalah Tech Reviewer 'Savage' (Ala GadgetIn/MKBHD).
        Data Riset: {context_data}
        
        Tugas: Buat konten review gadget/teknologi.
        Gaya Bahasa: Santai, teknis tapi mudah dimengerti, objektif.
        
        OUTPUT WAJIB (Markdown):
        1. 📱 TIKTOK (60s): Hook (Masalah/Kelebihan utama) -> Spesifikasi Dewa vs Sunat -> Kesimpulan (Worth it/Gak?).
        2. 🐦 TWITTER/X: Utas pendek membandingkan dengan kompetitor.
        3. 💰 MARKET INSIGHT: Prediksi harga jual kembali (resale value) & saran beli (Tunggu turun harga atau beli sekarang?).
        """
    else:
        system_prompt = f"""
        Kamu adalah Senior News Anchor & Analis Media Sosial.
        Data Riset: {context_data}
        
        Tugas: Buat paket berita lengkap.
        Gaya Bahasa: Berwibawa, Tajam, Investigatif (Ala Breaking News).
        
        OUTPUT WAJIB (Markdown):
        1. 📺 TIKTOK (News Style): Headline -> Kronologi Fakta (3 Poin) -> Pertanyaan Kritis untuk Audiens.
        2. 🐦 TWITTER/X (Jurnalistik): Thread investigasi 3-5 tweet (Data & Angka).
        3. 📰 INSTAGRAM (Editorial): Caption mendalam + Analisa Hukum/Sosial singkat + 10 Hashtag.
        4. 🗣️ NETIZEN SIMULATOR: Prediksi komentar Pro vs Kontra.
        """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Buatkan strategi konten sekarang."}
            ],
            temperature=0.7,
            max_tokens=2048 # Token diperbesar agar output tidak terpotong
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error Groq: {e}"

# --- 4. SCRAPERS (Pengumpul Data) ---
def get_trending_indo(history):
    # Menggunakan Google News RSS (Lebih stabil dari Pytrends)
    url = "https://news.google.com/rss?ceid=ID:id&hl=id&gl=ID"
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if entry.title not in history:
                history.append(entry.title) # Tandai sudah dibahas
                return entry.title, entry.link
        return None, None
    except:
        return None, None

def get_tech_news(history):
    # Ambil dari GSMArena / TechCrunch RSS
    url = "https://www.gsmarena.com/rss-news-reviews.php3"
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if entry.title not in history:
                # Filter keyword HP populer
                if any(x in entry.title.lower() for x in ['samsung', 'apple', 'xiaomi', 'pixel', 'infinix']):
                    history.append(entry.title)
                    return entry.title, entry.link
        return None, None
    except:
        return None, None

# --- 5. UTILITY DISCORD ---
def send_discord(webhook_url, title, content, color=3447003):
    if not content: return
    # Potong content jika terlalu panjang (Discord limit 4096 chars)
    if len(content) > 4000: content = content[:4000] + "..."
    
    embed = {
        "title": title,
        "description": content,
        "color": color,
        "footer": {"text": "Powered by Perplexity & Groq Llama 3"}
    }
    payload = {"username": "News AI Bot", "embeds": [embed]}
    requests.post(webhook_url, json=payload)

# --- MAIN LOGIC ---
def main():
    print("🤖 Bot Starting...")
    history = load_history()
    discord_url = os.getenv("DISCORD_WEBHOOK")
    
    reports = []
    
    # A. Cek Berita Umum (Trending Indo)
    topic_indo, link_indo = get_trending_indo(history)
    if topic_indo:
        print(f"Found News: {topic_indo}")
        content = generate_content_strategy(topic_indo, category='GENERAL')
        reports.append(("🇮🇩 Trending Indonesia", f"**Topik:** {topic_indo}\n[Baca Sumber]({link_indo})\n\n{content}", 16711680))
    else:
        print("No new General News.")

    # B. Cek Berita Tech
    topic_tech, link_tech = get_tech_news(history)
    if topic_tech:
        print(f"Found Tech: {topic_tech}")
        content = generate_content_strategy(topic_tech, category='TECH')
        reports.append(("📱 Tech Update", f"**Topik:** {topic_tech}\n[Baca Sumber]({link_tech})\n\n{content}", 3447003))
    else:
        print("No new Tech News.")

    # C. Kirim & Simpan
    if reports:
        for title, text, color in reports:
            if discord_url: send_discord(discord_url, title, text, color)
        save_history(history)
        print("✅ Done! Laporan terkirim & History disimpan.")
    else:
        print("💤 Tidak ada berita baru yang belum dibahas.")

if __name__ == "__main__":
    main()
