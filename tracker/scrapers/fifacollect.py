import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
URL = 'https://www.fifacollect.info/tickets/world-cup-2026/listings'

def parse_price(text):
    match = re.search(r'\$[\d,]+\.?\d*', text)
    if not match:
        return None
    return float(match.group(0).replace('$','').replace(',',''))

def scrape():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, 'lxml')
    table = soup.find('table')
    rows = table.find_all('tr')[1:]
    results = []
    for row in rows:
        cols = [td.get_text(strip=True) for td in row.find_all('td')]
        if len(cols) >= 8:
            results.append({
                'match': cols[0],
                'location': cols[1],
                'round': cols[2],
                'category': cols[3],
                'face_value': parse_price(cols[4]),
                'last_sale': parse_price(cols[6]),
                'starting_at': parse_price(cols[7]),
                'scraped_at': datetime.utcnow().isoformat()
            })
    return results

if __name__ == '__main__':
    data = scrape()
    print('Total listings:', len(data))
    brazil = [d for d in data if 'Brazil' in d['match']]
    for d in brazil:
        print(d['match'], d['category'], d['starting_at'])