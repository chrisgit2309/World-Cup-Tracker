import gspread
from google.oauth2.service_account import Credentials
import requests
from bs4 import BeautifulSoup
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

GMAIL_USER = 'trackerworldcup@gmail.com'
GMAIL_PASSWORD = 'cgjx hixi cnzn rdlo'
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1avbZ1dWaATRtMib_k6jYj92hubGt4N-KRAMAhMadP04/edit'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def get_subscribers():
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL).sheet1
    return sheet.get_all_records()

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

def scrape_listings():
    URL = 'https://www.fifacollect.info/tickets/world-cup-2026/listings'
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.content, 'lxml')
    table = soup.find('table')
    rows = table.find_all('tr')[1:]
    results = []
    for row in rows:
        cols = [td.get_text(strip=True) for td in row.find_all('td')]
        if len(cols) >= 8:
            match_name = fix_encoding(cols[0])
            match_name = re.sub(r'^M\d+', '', match_name).strip()
            m = re.search(r'(.+?)(January|February|March|April|May|June|July)(\s+\d+,\s+\d{4})', match_name)
            if m:
                match_name = m.group(1).strip()
            sa = parse_price(cols[7])
            cat = cols[3]
            if sa:
                results.append({'match': match_name, 'category': cat, 'starting_at': sa})
    return results

def send_alert_email(to_email, match, category, price, max_price):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'World Cup 2026 Price Alert - ' + match
    msg['From'] = GMAIL_USER
    msg['To'] = to_email
    html = '''<html><body style="font-family:Arial;max-width:600px;margin:auto;padding:20px;background:#f0f0f0">
    <div style="background:#1a1a2e;color:white;padding:20px;border-radius:10px;margin-bottom:20px">
        <h1 style="margin:0;font-size:24px">Price Alert!</h1>
        <p style="color:#9ACD32;margin:5px 0">World Cup 2026 Ticket Tracker</p>
    </div>
    <div style="background:white;padding:20px;border-radius:10px;border-left:4px solid #E8003D">
        <h2 style="color:#1a1a2e">''' + match + '''</h2>
        <p style="font-size:18px">Category: <strong>''' + category + '''</strong></p>
        <p style="font-size:24px;color:#E8003D;font-weight:bold">Current price: $''' + str(price) + '''</p>
        <p style="color:#888">Your target: $''' + str(max_price) + '''</p>
        <a href="https://collect.fifa.com" style="display:inline-block;background:#E8003D;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;margin-top:10px">Buy Now on FIFA Collect</a>
    </div>
    <p style="color:#aaa;font-size:11px;margin-top:20px;text-align:center">World Cup 2026 Ticket Tracker</p>
    </body></html>'''
    msg.attach(MIMEText(html, 'html'))
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())
    print('Alert sent to:', to_email)

def run_alerts():
    print('Checking alerts...', datetime.utcnow().strftime('%H:%M UTC'))
    try:
        subscribers = get_subscribers()
        print('Subscribers:', len(subscribers))
    except Exception as e:
        print('Error reading subscribers:', e)
        return
    try:
        listings = scrape_listings()
        print('Listings:', len(listings))
    except Exception as e:
        print('Error scraping:', e)
        return

    for sub in subscribers:
        email = sub.get('Email Address', '')
        teams = sub.get('Which matches do you want to track?  ', '')
        max_price = sub.get('Maximum price per ticket ($)  ', 0)
        category = sub.get('Ticket category  ', 'Any category')
        if not email or not max_price:
            continue
        try:
            max_price = float(str(max_price).replace('$','').replace(',',''))
        except:
            continue

        matches_alerted = set()
        for listing in listings:
            team_match = any(team.strip().lower() in listing['match'].lower() for team in teams.split(','))
            cat_match = 'Any category' in category or listing['category'].replace(' ','') in category.replace(' ','')
            price_match = listing['starting_at'] <= max_price

            if team_match and cat_match and price_match and listing['match'] not in matches_alerted:
                matches_alerted.add(listing['match'])
                try:
                    send_alert_email(email, listing['match'], listing['category'], listing['starting_at'], max_price)
                except Exception as e:
                    print('Error sending email:', e)

if __name__ == '__main__':
    run_alerts()
