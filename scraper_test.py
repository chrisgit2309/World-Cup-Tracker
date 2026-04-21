import requests
from bs4 import BeautifulSoup
import re

def parse_price(text):
    match = re.search(r'\$[\d,]+\.?\d*', text)
    return match.group(0) if match else 'N/A'

r = requests.get(
    'https://www.fifacollect.info/tickets/world-cup-2026/listings',
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
)
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
            'category': cols[3],
            'face_value': parse_price(cols[4]),
            'last_sale': parse_price(cols[6]),
            'starting_at': parse_price(cols[7])
        })

brazil = [r for r in results if 'Brazil' in r['match'] and 'Morocco' in r['match']]
print('=== BRAZIL VS MOROCCO ===')
for r in brazil:
    print(r['category'], '| Face:', r['face_value'], '| Ultimo:', r['last_sale'], '| Desde:', r['starting_at'])

print('Total partidos:', len(results))