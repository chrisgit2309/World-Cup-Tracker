import requests
from bs4 import BeautifulSoup
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import json
import sqlite3
import os
import sys

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
URL = 'https://www.fifacollect.info/tickets/world-cup-2026/listings'

GMAIL_USER = 'tu_email@gmail.com'
GMAIL_PASSWORD = 'tu_app_password'
SUBSCRIBERS = ['suscriptor1@email.com']

DB_PATH = 'data/prices.db'

def init_db():
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match TEXT, category TEXT, city TEXT,
        face_value REAL, starting_at REAL, premium INTEGER,
        scraped_at TEXT
    )''')
    conn.commit()
    conn.close()

def save_prices(listings):
    conn = sqlite3.connect(DB_PATH)
    now = datetime.utcnow().isoformat()
    for l in listings:
        conn.execute('''INSERT INTO prices (match, category, city, face_value, starting_at, premium, scraped_at)
            VALUES (?,?,?,?,?,?,?)''',
            (l['match'], l['category'], l['city'], l['face_value'], l['starting_at'], l['premium'], now))
    conn.commit()
    conn.close()

def get_trend(match, category, current_price):
    conn = sqlite3.connect(DB_PATH)
    prev = conn.execute('''SELECT starting_at FROM prices
        WHERE match=? AND category=?
        ORDER BY scraped_at DESC LIMIT 1 OFFSET 1''', (match, category)).fetchone()
    conn.close()
    if not prev:
        return 'new', 0
    diff = current_price - prev[0]
    if diff > 0:
        return 'up', diff
    elif diff < 0:
        return 'down', diff
    return 'same', 0

def parse_price(text):
    match = re.search(r'\$[\d,]+\.?\d*', text)
    if not match:
        return None
    return float(match.group(0).replace('$','').replace(',',''))

def fix_encoding(text):
    try:
        return text.encode('latin-1').decode('utf-8')
    except:
        return text

def clean_match(text):
    text = fix_encoding(text)
    text = re.sub(r'^M\d+', '', text).strip()
    match = re.search(r'(.+?)(January|February|March|April|May|June|July)(\s+\d+,\s+\d{4})', text)
    if match:
        return match.group(1).strip(), match.group(2) + match.group(3)
    return text.strip(), ''

def clean_location(text):
    text = fix_encoding(text)
    parts = re.split(r'(?<=[a-z])(?=[A-Z])', text, 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return text, ''

def extract_teams(match_name):
    if ' vs. ' in match_name:
        parts = match_name.split(' vs. ')
        t1 = re.sub(r'^[A-Z0-9]+\s+', '', parts[0]).strip()
        t2 = parts[1].strip()
        if len(t1) > 2 and not re.match(r'^[0-9A-Z]{1,3}$', t1):
            return [t1, t2]
    return []

def scrape():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.content, 'lxml')
    table = soup.find('table')
    rows = table.find_all('tr')[1:]
    results = []
    scraped_at = datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')
    for row in rows:
        cols = [td.get_text(strip=True) for td in row.find_all('td')]
        tds = row.find_all('td')
        if len(cols) >= 8:
            match_name, match_date = clean_match(cols[0])
            city, stadium = clean_location(cols[1])
            fv = parse_price(cols[4])
            sa = parse_price(cols[7])
            if not fv or not sa:
                continue
            pct = round(((sa - fv) / fv) * 100)
            buy_link = 'https://collect.fifa.com'
            for td in tds:
                for a in td.find_all('a', href=True):
                    href = a.get('href','')
                    if 'collect.fifa.com' in href:
                        buy_link = href
                        break
            trend, diff = get_trend(match_name, cols[3], sa)
            results.append({
                'match': match_name,
                'date': match_date,
                'city': city,
                'stadium': stadium,
                'round': cols[2],
                'category': cols[3],
                'face_value': fv,
                'starting_at': sa,
                'premium': pct,
                'buy_link': buy_link,
                'scraped_at': scraped_at,
                'trend': trend,
                'trend_diff': round(diff, 2)
            })
    return results

def build_interactive_html(listings, scraped_at):
    data_json = json.dumps(listings, ensure_ascii=False)
    cities = sorted(set(l['city'] for l in listings))
    rounds = sorted(set(l['round'] for l in listings))
    teams_set = set()
    for l in listings:
        for t in extract_teams(l['match']):
            if t:
                teams_set.add(fix_encoding(t))
    teams = sorted(teams_set)
    dates = sorted(set(l['date'] for l in listings if l['date']))

    city_options = '<option value="">--</option>' + ''.join('<option value="' + c + '">' + c + '</option>' for c in cities)
    team_options = '<option value="">--</option>' + ''.join('<option value="' + t + '">' + t + '</option>' for t in teams)
    date_options = '<option value="">--</option>' + ''.join('<option value="' + d + '">' + d + '</option>' for d in dates)
    round_options = '<option value="">--</option>' + ''.join('<option value="' + r + '">' + r + '</option>' for r in rounds)

    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>World Cup 2026 Ticket Tracker</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Inter', sans-serif; background: #0a0a0a; color: #fff; min-height: 100vh; }

/* HERO HEADER */
.hero {
  background: #0a0a0a;
  position: relative;
  overflow: hidden;
  padding: 0;
  margin-bottom: 24px;
}
.hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 15% 50%, #7B2FBE 0%, transparent 45%),
    radial-gradient(circle at 85% 20%, #E8003D 0%, transparent 45%),
    radial-gradient(circle at 80% 80%, #9ACD32 0%, transparent 35%);
  opacity: 0.85;
}
.hero-shapes {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.shape {
  position: absolute;
  border-radius: 50%;
  opacity: 0.15;
}
.shape-1 { width: 400px; height: 400px; background: #E8003D; top: -100px; right: -50px; }
.shape-2 { width: 300px; height: 300px; background: #7B2FBE; bottom: -80px; left: -60px; }
.shape-3 { width: 200px; height: 200px; background: #9ACD32; top: 20px; left: 40%; }
.hero-content {
  position: relative;
  z-index: 2;
  padding: 32px 24px 28px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}
.hero-left { flex: 1; }
.hero-badge {
  display: inline-block;
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.3);
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #fff;
  margin-bottom: 10px;
}
.hero h1 {
  font-family: 'Bebas Neue', sans-serif;
  font-size: clamp(32px, 6vw, 56px);
  line-height: 1;
  color: #fff;
  letter-spacing: 1px;
  margin-bottom: 8px;
}
.hero h1 span { color: #9ACD32; }
.hero p { color: rgba(255,255,255,0.7); font-size: 13px; }
.hero-right { display: flex; flex-direction: column; gap: 10px; align-items: flex-end; }
.lang-toggle { display: flex; gap: 6px; }
.lang-btn { padding: 6px 14px; border: 1px solid rgba(255,255,255,0.3); border-radius: 20px; background: transparent; color: white; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.2s; }
.lang-btn.active { background: #E8003D; border-color: #E8003D; }
.update-badge {
  background: rgba(0,0,0,0.4);
  border: 1px solid rgba(255,255,255,0.15);
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 11px;
  color: rgba(255,255,255,0.7);
  text-align: right;
}
.update-badge strong { color: #9ACD32; display: block; font-size: 12px; }

/* SECTIONS */
.container { max-width: 1400px; margin: 0 auto; padding: 0 20px 40px; }
.section { background: #161616; border: 1px solid #2a2a2a; border-radius: 12px; padding: 16px 18px; margin-bottom: 14px; }
.section-title { font-size: 13px; font-weight: 700; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }

/* DISCLAIMER */
.disclaimer { border-left: 3px solid #f39c12; }
.disclaimer .section-title { color: #f39c12; }
.disclaimer-text { font-size: 12px; color: #aaa; line-height: 1.7; }
.disclaimer-text ul { padding-left: 16px; margin-top: 6px; }
.disclaimer-text li { margin-bottom: 3px; }
.disclaimer-text .ok { color: #9ACD32; }
.disclaimer-text .warn { color: #f39c12; }

/* SEATS */
.seats { border-left: 3px solid #3498db; }
.seats .section-title { color: #3498db; }
.seats-text { font-size: 12px; color: #aaa; line-height: 1.7; }

/* FILTERS */
.filters { display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }
.filter-group { display: flex; flex-direction: column; gap: 4px; }
.filter-group label { font-size: 10px; font-weight: 700; color: #666; text-transform: uppercase; letter-spacing: 1px; }
select, input[type=number] { padding: 8px 12px; border: 1px solid #2a2a2a; border-radius: 8px; font-size: 13px; background: #0f0f0f; color: #fff; min-width: 130px; }
select:focus, input:focus { outline: none; border-color: #E8003D; }
.btn { padding: 8px 16px; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 700; transition: all 0.2s; }
.btn-reset { background: #E8003D; color: white; }
.btn-reset:hover { background: #c0392b; }
.btn-bestdeal { background: #9ACD32; color: #000; }
.btn-bestdeal:hover { background: #7db520; }

/* ALERTS */
.alerts { border-left: 3px solid #f39c12; }
.alerts .section-title { color: #f39c12; }
.alert-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }
.btn-alert { background: #f39c12; color: #000; font-weight: 700; }
.alerts-list { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 8px; }
.alert-tag { background: rgba(243,156,18,0.15); border: 1px solid #f39c12; padding: 4px 10px; border-radius: 20px; font-size: 12px; display: flex; align-items: center; gap: 6px; color: #f39c12; }
.alert-tag .remove { cursor: pointer; color: #E8003D; font-weight: bold; }

/* WHATSAPP */
.wa-section { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.wa-section p { font-size: 13px; color: #888; flex: 1; }
.btn-wa { background: #25d366; color: #000; font-weight: 700; }
.btn-wa:hover { background: #1da851; }

/* STATS */
.stats { display: flex; gap: 12px; flex-wrap: wrap; }
.stat-card { background: #161616; border: 1px solid #2a2a2a; padding: 14px 18px; border-radius: 12px; flex: 1; min-width: 120px; }
.stat-card .number { font-family: 'Bebas Neue', sans-serif; font-size: 36px; color: #fff; line-height: 1; }
.stat-card .number.green { color: #9ACD32; }
.stat-card .number.red { color: #E8003D; }
.stat-card .number.orange { color: #f39c12; }
.stat-card .label { font-size: 11px; color: #555; margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }

/* TABLE */
.table-wrap { background: #161616; border: 1px solid #2a2a2a; border-radius: 12px; overflow: hidden; margin-top: 14px; }
table { width: 100%; border-collapse: collapse; }
thead tr { background: linear-gradient(135deg, #E8003D, #7B2FBE); }
th { padding: 12px 14px; text-align: left; font-size: 12px; font-weight: 700; cursor: pointer; user-select: none; white-space: nowrap; letter-spacing: 0.5px; text-transform: uppercase; color: rgba(255,255,255,0.9); }
th:hover { background: rgba(255,255,255,0.1); }
td { padding: 10px 14px; border-bottom: 1px solid #1f1f1f; font-size: 13px; vertical-align: middle; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #1a1a1a; }
.match-name { font-weight: 600; color: #fff; }
.match-date { font-size: 11px; color: #555; margin-top: 2px; }
.match-round { font-size: 10px; color: #444; margin-top: 1px; }
.scraped-time { font-size: 10px; color: #333; margin-top: 2px; }
.price-high { color: #E8003D; font-weight: 700; }
.price-low { color: #9ACD32; font-weight: 700; }
.prem-high { color: #E8003D; font-weight: 700; }
.prem-low { color: #9ACD32; font-weight: 700; }
.cat { background: rgba(123,47,190,0.3); border: 1px solid #7B2FBE; padding: 3px 8px; border-radius: 5px; font-size: 11px; font-weight: 700; color: #c084fc; }
.trend-up { color: #E8003D; font-size: 12px; font-weight: 600; }
.trend-down { color: #9ACD32; font-size: 12px; font-weight: 600; }
.trend-same { color: #444; font-size: 12px; }
.trend-new { color: #3498db; font-size: 12px; font-weight: 600; }
.btn-buy { display: inline-block; padding: 5px 12px; background: #E8003D; color: white; border-radius: 6px; font-size: 12px; font-weight: 700; text-decoration: none; transition: all 0.2s; }
.btn-buy:hover { background: #9ACD32; color: #000; }
.alert-match td { background: rgba(243,156,18,0.05) !important; }
.no-results { text-align: center; padding: 50px; color: #444; font-size: 14px; }
.footer { font-size: 11px; color: #333; margin-top: 20px; text-align: center; line-height: 2; }

/* SOCCER BALL PATTERN */
body::before {
  content: '';
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image: radial-gradient(circle, #ffffff08 1px, transparent 1px);
  background-size: 30px 30px;
  pointer-events: none;
  z-index: 0;
}
.container { position: relative; z-index: 1; }
.hero { position: relative; z-index: 1; }
</style>
</head>
<body>

<div class="hero">
  <div class="hero-bg"></div>
  <div class="hero-shapes">
    <div class="shape shape-1"></div>
    <div class="shape shape-2"></div>
    <div class="shape shape-3"></div>
  </div>
  <div class="hero-content">
    <div class="hero-left">
      <div class="hero-badge">FIFA World Cup 2026</div>
      <h1>TICKET <span>TRACKER</span><br>WORLD CUP 2026</h1>
      <p data-en="Live prices from FIFA Collect official marketplace" data-es="Precios en vivo del marketplace oficial de FIFA Collect">Live prices from FIFA Collect official marketplace</p>
    </div>
    <div class="hero-right">
      <div class="lang-toggle">
        <button class="lang-btn active" onclick="setLang('en')">EN</button>
        <button class="lang-btn" onclick="setLang('es')">ES</button>
      </div>
      <div class="update-badge">
        <span data-en="Last updated" data-es="Ultima actualizacion">Last updated</span>
        <strong>''' + scraped_at + '''</strong>
        <span style="font-size:10px;color:#555" data-en="Prices may vary — always verify on FIFA Collect" data-es="Precios pueden variar — verifica siempre en FIFA Collect">Prices may vary — always verify on FIFA Collect</span>
      </div>
    </div>
  </div>
</div>

<div class="container">

<div class="section disclaimer">
  <div class="section-title">&#9888; <span data-en="What is FIFA Collect?" data-es="Que es FIFA Collect?">What is FIFA Collect?</span></div>
  <div class="disclaimer-text">
    <span data-en="FIFA Collect is the OFFICIAL FIFA marketplace where tickets are sold as digital collectibles that are also valid as real match entry tickets." data-es="FIFA Collect es el marketplace OFICIAL de FIFA donde los tickets se venden como coleccionables digitales que tambien son validos como entradas reales al partido.">FIFA Collect is the OFFICIAL FIFA marketplace where tickets are sold as digital collectibles that are also valid as real match entry tickets.</span>
    <ul>
      <li><span class="ok">OK</span> <span data-en="100% official — operated directly by FIFA" data-es="100% oficial — operado directamente por FIFA">100% official — operated directly by FIFA</span></li>
      <li><span class="ok">OK</span> <span data-en="Ticket delivered via the FIFA World Cup 2026 App" data-es="Ticket entregado via la App oficial FIFA World Cup 2026">Ticket delivered via the FIFA World Cup 2026 App</span></li>
      <li><span class="warn">NOTE</span> <span data-en="Prices shown are approximate — always verify on FIFA Collect before buying" data-es="Los precios mostrados son aproximados — siempre verifica en FIFA Collect antes de comprar">Prices shown are approximate — always verify on FIFA Collect before buying</span></li>
      <li><span class="warn">NOTE</span> <span data-en="Listings sell fast — prices update periodically, not in real time" data-es="Los listings se venden rapido — precios se actualizan periodicamente, no en tiempo real">Listings sell fast — prices update periodically, not in real time</span></li>
    </ul>
  </div>
</div>

<div class="section seats">
  <div class="section-title">&#128186; <span data-en="About seat assignment" data-es="Sobre la asignacion de asientos">About seat assignment</span></div>
  <div class="seats-text">
    <span data-en="When buying on FIFA Collect you purchase a CATEGORY (CAT1, CAT2, etc.) that defines your stadium zone — not a specific seat. FIFA assigns your exact seat 24-48 hours before the match. CAT1 = best zones near the field. CAT2 = mid-tier. CAT3/4 = upper tiers." data-es="Al comprar en FIFA Collect adquiris una CATEGORIA (CAT1, CAT2, etc.) que define tu zona en el estadio, no un asiento especifico. FIFA asigna tu asiento exacto 24-48 horas antes del partido. CAT1 = mejores zonas cerca del campo. CAT2 = intermedias. CAT3/4 = tribunas altas.">When buying on FIFA Collect you purchase a CATEGORY (CAT1, CAT2, etc.) that defines your stadium zone — not a specific seat. FIFA assigns your exact seat 24-48 hours before the match. CAT1 = best zones near the field. CAT2 = mid-tier. CAT3/4 = upper tiers.</span>
  </div>
</div>

<div class="section">
  <div class="section-title" data-en="Filters" data-es="Filtros">Filters</div>
  <div class="filters">
    <div class="filter-group">
      <label data-en="City" data-es="Ciudad">City</label>
      <select id="filterCity" onchange="applyFilters()">''' + city_options + '''</select>
    </div>
    <div class="filter-group">
      <label data-en="Team" data-es="Equipo">Team</label>
      <select id="filterTeam" onchange="applyFilters()">''' + team_options + '''</select>
    </div>
    <div class="filter-group">
      <label data-en="Date" data-es="Fecha">Date</label>
      <select id="filterDate" onchange="applyFilters()">''' + date_options + '''</select>
    </div>
    <div class="filter-group">
      <label data-en="Round" data-es="Ronda">Round</label>
      <select id="filterRound" onchange="applyFilters()">''' + round_options + '''</select>
    </div>
    <div class="filter-group">
      <label data-en="Category" data-es="Categoria">Category</label>
      <select id="filterCat" onchange="applyFilters()">
        <option value="">--</option>
        <option value="CAT1">CAT1</option>
        <option value="CAT2">CAT2</option>
        <option value="CAT3">CAT3</option>
        <option value="CAT4">CAT4</option>
      </select>
    </div>
    <div class="filter-group">
      <label data-en="Max Price ($)" data-es="Precio max ($)">Max Price ($)</label>
      <input type="number" id="filterMaxPrice" placeholder="e.g. 1000" oninput="applyFilters()" style="min-width:110px">
    </div>
    <button class="btn btn-bestdeal" onclick="showBestDeals()" data-en="Best Deals" data-es="Mejores Deals">Best Deals</button>
    <button class="btn btn-reset" onclick="resetFilters()" data-en="Reset" data-es="Limpiar">Reset</button>
  </div>
</div>

<div class="section alerts">
  <div class="section-title">&#128276; <span data-en="Price Alerts" data-es="Alertas de Precio">Price Alerts</span></div>
  <div class="alert-row">
    <div class="filter-group">
      <label data-en="Team" data-es="Equipo">Team</label>
      <select id="alertMatch">''' + team_options + '''</select>
    </div>
    <div class="filter-group">
      <label data-en="Max Price ($)" data-es="Precio max ($)">Max Price ($)</label>
      <input type="number" id="alertPrice" placeholder="500" style="min-width:100px">
    </div>
    <div class="filter-group">
      <label data-en="Category" data-es="Categoria">Category</label>
      <select id="alertCat">
        <option value="">Any</option>
        <option value="CAT1">CAT1</option>
        <option value="CAT2">CAT2</option>
        <option value="CAT3">CAT3</option>
        <option value="CAT4">CAT4</option>
      </select>
    </div>
    <button class="btn btn-alert" onclick="addAlert()" data-en="+ Add Alert" data-es="+ Agregar Alerta">+ Add Alert</button>
  </div>
  <div class="alerts-list" id="alertsList"></div>
</div>

<div class="section wa-section">
  <p data-en="Get instant email alerts when prices drop for your matches — $2.99 for the entire World Cup" data-es="Recibe alertas por email cuando bajen los precios — $2.99 por todo el Mundial">Get instant email alerts when prices drop for your matches — $2.99 for the entire World Cup</p>
  <a href="https://ko-fi.com/s/672a1f9296" target="_blank" class="btn" style="background:#E8003D;color:white;text-decoration:none;padding:8px 16px;border-radius:8px;font-weight:700;font-size:13px" data-en="Get Alerts $2.99" data-es="Obtener Alertas $2.99">Get Alerts $2.99</a>
</div>
<div class="section wa-section">
  <p data-en="Share today's best deals with your WhatsApp group" data-es="Compartí los mejores deals de hoy con tu grupo de WhatsApp">Share today's best deals with your WhatsApp group</p>
  <button class="btn btn-wa" onclick="shareWhatsApp()" data-en="Share on WhatsApp" data-es="Compartir por WhatsApp">Share on WhatsApp</button>
</div>

<div class="stats">
  <div class="stat-card"><div class="number" id="statTotal">0</div><div class="label" data-en="Listings" data-es="Listings">Listings</div></div>
  <div class="stat-card"><div class="number green" id="statMin">-</div><div class="label" data-en="Lowest Price" data-es="Precio mas bajo">Lowest Price</div></div>
  <div class="stat-card"><div class="number" id="statAvg">-</div><div class="label" data-en="Average Price" data-es="Precio promedio">Average Price</div></div>
  <div class="stat-card"><div class="number" id="statMatches">0</div><div class="label" data-en="Matches" data-es="Partidos">Matches</div></div>
  <div class="stat-card"><div class="number orange" id="statAlerts">0</div><div class="label" data-en="Active Alerts" data-es="Alertas activas">Active Alerts</div></div>
</div>

<div class="table-wrap">
  <table id="ticketTable">
    <thead>
      <tr>
        <th onclick="sortTable('match')" data-en="Match" data-es="Partido">Match</th>
        <th onclick="sortTable('city')" data-en="Location" data-es="Ciudad">Location</th>
        <th onclick="sortTable('category')" data-en="Cat" data-es="Cat">Cat</th>
        <th onclick="sortTable('face_value')" data-en="Face Value" data-es="Valor Face">Face Value</th>
        <th onclick="sortTable('starting_at')" data-en="Starting At" data-es="Desde">Starting At</th>
        <th onclick="sortTable('premium')" data-en="Premium" data-es="Premium">Premium</th>
        <th data-en="Trend" data-es="Tendencia">Trend</th>
        <th data-en="Buy" data-es="Comprar">Buy</th>
      </tr>
    </thead>
    <tbody id="tableBody"></tbody>
  </table>
  <div id="noResults" class="no-results" style="display:none" data-en="No listings found." data-es="Sin resultados.">No listings found.</div>
</div>

<div class="footer">
  <p data-en="Prices scraped periodically from fifacollect.info — may not reflect real-time availability. Always verify on FIFA Collect before purchasing. Not affiliated with FIFA." data-es="Precios obtenidos periodicamente de fifacollect.info — pueden no reflejar disponibilidad en tiempo real. Siempre verifica en FIFA Collect antes de comprar. No afiliado con FIFA.">
    Prices scraped periodically from fifacollect.info — may not reflect real-time availability. Always verify on FIFA Collect before purchasing. Not affiliated with FIFA.
  </p>
</div>

</div>

<script>
const DATA = ''' + data_json + ''';
let sortKey = 'starting_at';
let sortAsc = true;
let filtered = [...DATA];
let alerts = [];
let currentLang = 'en';

function setLang(lang) {
  currentLang = lang;
  document.querySelectorAll('[data-en]').forEach(el => {
    if (el.children.length === 0) {
      el.textContent = lang === 'es' ? el.dataset.es : el.dataset.en;
    }
  });
  document.querySelectorAll('th[data-en]').forEach(el => {
    el.textContent = lang === 'es' ? el.dataset.es : el.dataset.en;
  });
  document.querySelectorAll('.btn[data-en]').forEach(el => {
    el.textContent = lang === 'es' ? el.dataset.es : el.dataset.en;
  });
  document.querySelectorAll('.lang-btn').forEach(btn => btn.classList.remove('active'));
  event.target.classList.add('active');
  renderTable();
}

function trendHTML(trend, diff) {
  if (trend === 'new') return '<span class="trend-new">NEW</span>';
  if (trend === 'up') return '<span class="trend-up">UP +$' + Math.abs(diff).toFixed(0) + '</span>';
  if (trend === 'down') return '<span class="trend-down">DOWN -$' + Math.abs(diff).toFixed(0) + '</span>';
  return '<span class="trend-same">-</span>';
}

function applyFilters() {
  const city = document.getElementById('filterCity').value;
  const team = document.getElementById('filterTeam').value;
  const date = document.getElementById('filterDate').value;
  const cat = document.getElementById('filterCat').value;
  const round = document.getElementById('filterRound').value;
  const maxPrice = parseFloat(document.getElementById('filterMaxPrice').value) || Infinity;
  filtered = DATA.filter(l => {
    if (city && l.city !== city) return false;
    if (team && !l.match.includes(team)) return false;
    if (date && l.date !== date) return false;
    if (cat && l.category !== cat) return false;
    if (round && l.round !== round) return false;
    if (l.starting_at > maxPrice) return false;
    return true;
  });
  sortTable(sortKey, true);
}

function showBestDeals() {
  resetFilters(false);
  filtered = [...DATA].sort((a,b) => a.premium - b.premium);
  sortKey = 'premium';
  sortAsc = true;
  renderTable();
}

function sortTable(key, keepDir=false) {
  if (!keepDir) sortAsc = (sortKey === key) ? !sortAsc : true;
  sortKey = key;
  filtered.sort((a, b) => {
    let av = a[key], bv = b[key];
    if (typeof av === 'string') return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    return sortAsc ? av - bv : bv - av;
  });
  renderTable();
}

function isAlerted(l) {
  return alerts.some(a => {
    if (a.team && !l.match.includes(a.team)) return false;
    if (a.cat && l.category !== a.cat) return false;
    return l.starting_at <= a.price;
  });
}

function renderTable() {
  const tbody = document.getElementById('tableBody');
  const noResults = document.getElementById('noResults');
  const table = document.getElementById('ticketTable');
  if (filtered.length === 0) {
    table.style.display = 'none';
    noResults.style.display = 'block';
  } else {
    table.style.display = 'table';
    noResults.style.display = 'none';
  }
  const buyText = currentLang === 'es' ? 'Comprar' : 'Buy';
  tbody.innerHTML = filtered.map(l => {
    const priceClass = l.premium > 0 ? 'price-high' : 'price-low';
    const premClass = l.premium > 0 ? 'prem-high' : 'prem-low';
    const premSign = l.premium > 0 ? '+' : '';
    const alertClass = isAlerted(l) ? 'alert-match' : '';
    const alertIcon = isAlerted(l) ? '[!] ' : '';
    return '<tr class="' + alertClass + '">' +
      '<td><div class="match-name">' + alertIcon + l.match + '</div>' +
      '<div class="match-date">' + l.date + '</div>' +
      '<div class="match-round">' + l.round + '</div>' +
      '<div class="scraped-time">Updated: ' + l.scraped_at + '</div></td>' +
      '<td>' + l.city + '<br><small style="color:#444">' + l.stadium + '</small></td>' +
      '<td><span class="cat">' + l.category + '</span></td>' +
      '<td style="color:#888">$' + l.face_value.toLocaleString() + '</td>' +
      '<td class="' + priceClass + '">$' + l.starting_at.toLocaleString() + '</td>' +
      '<td class="' + premClass + '">' + premSign + l.premium + '%</td>' +
      '<td>' + trendHTML(l.trend, l.trend_diff) + '</td>' +
      '<td><a href="' + l.buy_link + '" target="_blank" class="btn-buy">' + buyText + '</a></td>' +
      '</tr>';
  }).join('');
  const prices = filtered.map(l => l.starting_at);
  document.getElementById('statTotal').textContent = filtered.length;
  document.getElementById('statMin').textContent = prices.length ? '$' + Math.min(...prices).toLocaleString() : '-';
  document.getElementById('statAvg').textContent = prices.length ? '$' + Math.round(prices.reduce((a,b)=>a+b,0)/prices.length).toLocaleString() : '-';
  document.getElementById('statMatches').textContent = new Set(filtered.map(l=>l.match)).size;
  document.getElementById('statAlerts').textContent = alerts.length;
}

function addAlert() {
  const team = document.getElementById('alertMatch').value;
  const price = parseFloat(document.getElementById('alertPrice').value);
  const cat = document.getElementById('alertCat').value;
  if (!team || !price) { alert('Select a team and enter a max price'); return; }
  alerts.push({ team, price, cat });
  renderAlerts();
  renderTable();
}

function removeAlert(i) {
  alerts.splice(i, 1);
  renderAlerts();
  renderTable();
}

function renderAlerts() {
  document.getElementById('alertsList').innerHTML = alerts.map((a,i) =>
    '<div class="alert-tag">' + a.team + (a.cat ? ' ' + a.cat : '') + ' under $' + a.price +
    ' <span class="remove" onclick="removeAlert(' + i + ')">x</span></div>'
  ).join('');
  document.getElementById('statAlerts').textContent = alerts.length;
}

function shareWhatsApp() {
  const nl = String.fromCharCode(10);
  const h1 = 'Mira este tracker GRATUITO de precios de tickets para el Mundial 2026:';
  const h2 = 'Check out this FREE World Cup 2026 ticket price tracker:';
  const f1 = 'Filtra por partido, ciudad y categoria. Precios actualizados cada 10 minutos.';
  const f2 = 'Filter by match, city and category. Prices updated every 10 minutes.';
  const header = currentLang === 'es' ? h1 : h2;
  const footer = currentLang === 'es' ? f1 : f2;
  const link = 'https://worldcuptracker2026.netlify.app';
  const msg = header + nl + nl + link + nl + nl + footer;
  window.open('https://wa.me/?text=' + encodeURIComponent(msg), '_blank');
}

function resetFilters(render=true) {
  ['filterCity','filterTeam','filterDate','filterCat','filterRound'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('filterMaxPrice').value = '';
  filtered = [...DATA];
  if (render) sortTable('starting_at', true);
}

renderAlerts();
applyFilters();
</script>
</body>
</html>'''
    return html

def send_email(html):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'World Cup 2026 Tickets - Daily Update ' + datetime.utcnow().strftime('%b %d')
    msg['From'] = GMAIL_USER
    msg['To'] = ', '.join(SUBSCRIBERS)
    msg.attach(MIMEText(html, 'html'))
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, SUBSCRIBERS, msg.as_string())
    print('Email enviado a:', SUBSCRIBERS)

if __name__ == '__main__':
    print('Iniciando...')
    init_db()
    print('Scraping fifacollect...')
    listings = scrape()
    print('Listings encontrados:', len(listings))
    print('Guardando precios historicos...')
    save_prices(listings)
    scraped_at = datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')
    html = build_interactive_html(listings, scraped_at)
    with open('preview_email.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('Listo. Abri preview_email.html en Chrome')
    # send_email(html)