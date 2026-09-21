from datetime import datetime
import os
import feedparser
from dotenv import load_dotenv
import requests
import yfinance as yf

# Load file .env (menggunakan DISCORD_WEBHOOK_URL yang sudah ada)
load_dotenv()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def get_macro_data():
  """Tarik data komoditas dan kurs via yfinance"""
  tickers = {
      "Minyak (WTI)": "CL=F",
      "Minyak (Brent)": "BZ=F",
      "Emas Dunia": "GC=F",
      "Gas Alam": "NG=F",
      "USD/IDR": "USDIDR=X",
  }

  lines = []
  for label, sym in tickers.items():
    try:
      df = yf.download(sym, period="5d", interval="1d", progress=False)
      if len(df) >= 2:
        close_today = float(df["Close"].iloc[-1])
        close_prev = float(df["Close"].iloc[-2])
        change_pct = ((close_today - close_prev) / close_prev) * 100

        sign = "+" if change_pct >= 0 else ""
        if sym == "USDIDR=X":
          val_str = f"Rp{close_today:,.0f}"
        else:
          val_str = f"${close_today:,.2f}"

        lines.append(
            f"• **{label:<14}**: `{val_str}` ({sign}{change_pct:.2f}%)"
        )
    except Exception as e:
      continue
  return (
      "\n".join(lines) if lines else "• Data komoditas belum dapat dimuat."
  )


def get_crypto_data():
  """Tarik harga BTC, ETH, dan trending coin via API publik CoinGecko"""
  lines = []
  try:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true"
    res = requests.get(url, timeout=10).json()

    btc_p = res.get("bitcoin", {}).get("usd", 0)
    btc_c = res.get("bitcoin", {}).get("usd_24h_change", 0)
    sign_btc = "+" if btc_c >= 0 else ""
    lines.append(
        f"• **Bitcoin (BTC)**  : `${btc_p:,.0f}` ({sign_btc}{btc_c:.2f}%)"
    )

    eth_p = res.get("ethereum", {}).get("usd", 0)
    eth_c = res.get("ethereum", {}).get("usd_24h_change", 0)
    sign_eth = "+" if eth_c >= 0 else ""
    lines.append(
        f"• **Ethereum (ETH)** : `${eth_p:,.0f}` ({sign_eth}{eth_c:.2f}%)"
    )

    # Ambil 1 trending coin nomor 1 hari ini
    trend_url = "https://api.coingecko.com/api/v3/search/trending"
    trend_res = requests.get(trend_url, timeout=10).json()
    top_coin = trend_res.get("coins", [])[0]["item"]
    symbol = top_coin.get("symbol", "").upper()
    price_btc = top_coin.get("price_btc", 0)
    lines.append(f"• **Trending Alt**   : **{symbol}** (Rank #{top_coin.get('market_cap_rank', '-')})")
  except Exception as e:
    lines.append("• Data pasar kripto sementara belum tersedia.")

  return "\n".join(lines)


def get_trending_news():
  """Tarik 3 berita terhangat/terpopuler dari RSS feed nasional"""
  feeds = [
      "https://www.antaranews.com/rss/terkini.xml",
      "https://www.cnnindonesia.com/nasional/rss",
  ]

  news_list = []
  for feed_url in feeds:
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
      title = entry.title.strip()
      link = entry.link.strip()
      if title and link and not any(item["link"] == link for item in news_list):
        news_list.append({"title": title, "link": link})
      if len(news_list) >= 3:
        break
    if len(news_list) >= 3:
      break

  if not news_list:
    return "• Berita terkini belum dapat dimuat."

  lines = []
  for idx, item in enumerate(news_list[:3], 1):
    lines.append(f"{idx}. [{item['title']}]({item['link']})")
  return "\n\n".join(lines)


def send_discord():
  if not WEBHOOK_URL:
    print("Error: DISCORD_WEBHOOK_URL tidak ditemukan di file .env")
    return

  now_str = datetime.now().strftime("%d-%m-%Y %H:%M")
  macro_section = get_macro_data()
  crypto_section = get_crypto_data()
  news_section = get_trending_news()

  embed = {
      "title": "🌅 MORNING DIGEST & MARKET RADAR",
      "description": (
          f"Update ringkasan pasar dan berita terkini ({now_str} WIB)\n"
      ),
      "color": 0xF39C12,  # Warna oranye keemasan
      "fields": [
          {
              "name": "🛢️ KOMODITAS & MAKRO",
              "value": macro_section,
              "inline": False,
          },
          {"name": "🪙 PASAR KRIPTO", "value": crypto_section, "inline": False},
          {
              "name": "🔥 3 BERITA TRENDING HARI INI",
              "value": news_section,
              "inline": False,
          },
      ],
      "footer": {
          "text": "Daily Morning Intelligence • Automated by PM2",
          "icon_url": "https://cdn-icons-png.flaticon.com/512/330/330430.png",
      },
  }

  payload = {"embeds": [embed]}
  res = requests.post(WEBHOOK_URL, json=payload)

  if res.status_code in [200, 204]:
    print("Morning briefing berhasil terkirim ke Discord!")
  else:
    print(f"Gagal mengirim: {res.status_code} - {res.text}")


if __name__ == "__main__":
  send_discord()
