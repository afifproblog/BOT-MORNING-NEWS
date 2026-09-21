from datetime import datetime
import os
import feedparser
from dotenv import load_dotenv
import requests
import yfinance as yf

load_dotenv()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def get_coal_price():
  """Tarik proxy batu bara global via yfinance (Peabody Energy - Raksasa Coal Dunia)"""
  try:
    df = yf.download("BTU", period="5d", interval="1d", progress=False)
    if len(df) >= 2:
      close_series = df["Close"].dropna().values.flatten()
      if len(close_series) >= 2:
        close_today = float(close_series[-1])
        close_prev = float(close_series[-2])
        change_pct = ((close_today - close_prev) / close_prev) * 100
        sign = "+" if change_pct >= 0 else ""
        return f"`COAL (BTU)` : **${close_today:.2f}** ({sign}{change_pct:.2f}%)"
  except Exception:
    pass
  return None


def get_macro_data():
  """Tarik komoditas & makro ala Stockbit"""
  lines = []

  # 1. Masukkan COAL (Peabody Energy Proxy) di posisi paling atas
  coal_line = get_coal_price()
  if coal_line:
    lines.append(coal_line)

  # 2. Komoditas lainnya via yfinance
  items = [
      ("CPO/PALM", "ZL=F", "USc/lb"),
      ("BRENT", "BZ=F", "$"),
      ("OIL (WTI)", "CL=F", "$"),
      ("GOLD", "GC=F", "$"),
      ("SILVER", "SI=F", "$"),
      ("COPPER", "HG=F", "$"),
      ("GAS", "NG=F", "$"),
      ("USD/IDR", "USDIDR=X", "Rp"),
  ]

  for label, sym, curr in items:
    try:
      df = yf.download(sym, period="5d", interval="1d", progress=False)
      if len(df) >= 2:
        close_series = df["Close"].dropna().values.flatten()
        if len(close_series) >= 2:
          close_today = float(close_series[-1])
          close_prev = float(close_series[-2])
          change_pct = ((close_today - close_prev) / close_prev) * 100

          sign = "+" if change_pct >= 0 else ""
          if curr == "Rp":
            val_str = f"Rp{close_today:,.0f}"
          elif curr == "USc/lb":
            val_str = f"{close_today:.2f}¢"
          else:
            val_str = f"${close_today:,.2f}"

          lines.append(f"`{label:<10}` : **{val_str}** ({sign}{change_pct:.2f}%)")
    except Exception:
      continue

  return (
      "\n".join(lines) if lines else "• Data komoditas belum dapat dimuat."
  )


def get_crypto_data():
  """Tarik harga BTC, ETH, dan Top 3 Trending Coins lengkap dengan % 24h"""
  lines = []
  try:
    headers = {"accept": "application/json", "User-Agent": "Mozilla/5.0"}

    # 1. Tarik BTC & ETH
    url_p = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true"
    res_p = requests.get(url_p, headers=headers, timeout=10).json()

    btc_p = res_p.get("bitcoin", {}).get("usd", 0)
    btc_c = res_p.get("bitcoin", {}).get("usd_24h_change", 0)
    sign_btc = "+" if btc_c >= 0 else ""
    lines.append(
        f"`BTC       ` : **${btc_p:,.0f}** ({sign_btc}{btc_c:.2f}%)"
    )

    eth_p = res_p.get("ethereum", {}).get("usd", 0)
    eth_c = res_p.get("ethereum", {}).get("usd_24h_change", 0)
    sign_eth = "+" if eth_c >= 0 else ""
    lines.append(f"`ETH       ` : **${eth_p:,.0f}** ({sign_eth}{eth_c:.2f}%)")

    # 2. Tarik Top 3 Trending Coins
    url_t = "https://api.coingecko.com/api/v3/search/trending"
    res_t = requests.get(url_t, headers=headers, timeout=10).json()
    trending_coins = res_t.get("coins", [])[:3]

    lines.append("\n**Trending Searches (24h):**")
    for coin_obj in trending_coins:
      item = coin_obj.get("item", {})
      symbol = item.get("symbol", "").upper()
      data = item.get("data", {})

      price = data.get("price", 0)
      if isinstance(price, (int, float)):
        price_str = f"${price:,.4f}" if price < 1 else f"${price:,.2f}"
      else:
        price_str = str(price)

      change_24h = (
          data.get("price_change_percentage_24h", {}).get("usd", 0) or 0
      )
      sign_t = "+" if change_24h >= 0 else ""
      lines.append(
          f"• **{symbol:<6}** : {price_str} ({sign_t}{change_24h:.2f}%)"
      )
  except Exception:
    lines.append("• Data pasar kripto sementara belum tersedia.")

  return "\n".join(lines)


def get_trending_news():
  """Tarik 5 berita terhangat/viral terkini"""
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
      if len(news_list) >= 5:
        break
    if len(news_list) >= 5:
      break

  if not news_list:
    return "• Berita terkini belum dapat dimuat."

  lines = []
  for idx, item in enumerate(news_list[:5], 1):
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
      "description": f"Update ringkasan market & berita terkini ({now_str} WIB)\n",
      "color": 0x2ECC71,
      "fields": [
          {
              "name": "📊 COMMODITIES & CURRENCY",
              "value": macro_section,
              "inline": False,
          },
          {"name": "🪙 CRYPTO MARKET", "value": crypto_section, "inline": False},
          {
              "name": "🔥 5 BERITA TRENDING TERHANGAT",
              "value": news_section,
              "inline": False,
          },
      ],
      "footer": {
          "text": "Daily Market Intelligence • Automated by PM2",
          "icon_url": "https://assets.stickpng.com/images/5842f1f0a6515b1e0ad75b11.png",
      },
  }

  payload = {"embeds": [embed]}
  res = requests.post(WEBHOOK_URL, json=payload)

  if res.status_code in [200, 204]:
    print("Morning briefing berhasil terkirim!")
  else:
    print(f"Gagal mengirim: {res.status_code} - {res.text}")


if __name__ == "__main__":
  send_discord()
