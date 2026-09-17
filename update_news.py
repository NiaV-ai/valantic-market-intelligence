#!/usr/bin/env python3
"""
valantic Market Intelligence - Daily News Update
Läuft täglich um 6:00 Uhr via GitHub Actions
Sammelt News und updated das Dashboard
"""

import requests
import json
import os
from datetime import datetime, timedelta
import re

# NewsAPI Key von GitHub Secrets
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY', '')

# Unternehmen nach Beratungsbereich
COMPANIES = {
    'OVERVIEW COMPETITION': [
        'McKinsey', 'Deloitte', 'Boston Consulting Group', 'Accenture',
        'Capgemini', 'PwC', 'EY', 'KPMG', 'Bain & Company', 'Roland Berger'
    ],
    'DATA & AI': [
        'Infomotion', 'b.telligent', 'Dataciders', 'Accenture', 'Deloitte', 'Capgemini'
    ],
    'Cybersecurity ': [
        'Deloitte', 'KPMG', 'EY', 'PwC', 'Accenture', 'IBM', 'HiSolutions'
    ],
    'Insurance': [
        'McKinsey', 'msg.Insurance', 'EY', 'Deloitte', 'PwC', 'Capgemini', 'Allianz'
    ],
    'SERVICENOW': [
        'agineo', 'Deloitte', 'Accenture', 'KPMG', 'EY', 'Capgemini'
    ],
    'TelCo': [
        'Detecon', 'McKinsey', 'Accenture', 'Deloitte', 'PwC', 'EY', 'Vodafone'
    ],
    'LifeScience': [
        'IQVIA', 'Capgemini', 'McKinsey', 'Deloitte', 'EY', 'Accenture'
    ],
    'Anaplan Partner': [
        'valantic', 'Deloitte', 'Accenture', 'PwC', 'EY', 'KPMG'
    ]
}

def get_news_from_newsapi(company, days=3):
    """Sammelt News von NewsAPI"""
    if not NEWSAPI_KEY:
        print(f"❌ NEWSAPI_KEY nicht gesetzt!")
        return []

    try:
        url = 'https://newsapi.org/v2/everything'
        params = {
            'q': f'"{company}" (consulting OR transformation OR AI OR cloud)',
            'sortBy': 'publishedAt',
            'language': 'en',
            'pageSize': 3,
            'apiKey': NEWSAPI_KEY,
            'from': (datetime.utcnow() - timedelta(days=days)).isoformat()
        }
        response = requests.get(url, params=params, timeout=10)
        articles = response.json().get('articles', [])

        news_list = []
        for article in articles:
            # Klassifiziere News-Typ basierend auf Title/Description
            event_type = classify_news_type(article.get('title', ''))

            news_list.append({
                'company': company,
                'title': article.get('title', 'No title'),
                'url': article.get('url', ''),
                'published': article.get('publishedAt', ''),
                'source': article.get('source', {}).get('name', 'Unknown'),
                'eventType': event_type
            })

        return news_list
    except Exception as e:
        print(f"⚠️  NewsAPI Error für {company}: {str(e)}")
        return []

def classify_news_type(text):
    """Klassifiziert News-Typ basierend auf Text"""
    text_lower = text.lower()

    if any(word in text_lower for word in ['acquir', 'buy', 'merg', 'acquisition']):
        return 'M&A'
    elif any(word in text_lower for word in ['mergi', 'fusion', 'join']):
        return 'Fusion'
    elif any(word in text_lower for word in ['appoint', 'leader', 'ceo', 'cto', 'cfo']):
        return 'Leadership'
    elif any(word in text_lower for word in ['partner', 'customer', 'client', 'deal']):
        return 'Großkunde'
    elif any(word in text_lower for word in ['new', 'launch', 'expand', 'release']):
        return 'Portfolio'
    else:
        return 'Portfolio'

def generate_html_data(all_news):
    """Generiert JavaScript-Array für HTML"""

    news_by_area = {}
    for area in COMPANIES.keys():
        news_by_area[area] = []

    for item in all_news:
        # Finde den Bereich für dieses Unternehmen
        for area, companies in COMPANIES.items():
            if item['company'] in companies:
                # Konvertiere zu JavaScript Date
                date_str = item['published']
                try:
                    # Nimm die aktuellste News
                    if not news_by_area[area]:
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        news_item = {
                            'id': len(news_by_area[area]) + 1,
                            'company': item['company'],
                            'area': area,
                            'eventType': item['eventType'],
                            'title': item['title'],
                            'url': item['url'],
                            'date': date_str
                        }
                        news_by_area[area].append(news_item)
                except:
                    pass

    return news_by_area

def update_dashboard():
    """Updated das Dashboard HTML mit neuen News"""

    print(f"🔄 Starte News-Update um {datetime.utcnow().isoformat()}...")

    all_news = []

    # Sammle News für die Top-3 Unternehmen pro Bereich (um API-Limits zu respektieren)
    for area, companies in COMPANIES.items():
        print(f"  📍 {area}...")
        for company in companies[:3]:  # Limit auf 3 pro Bereich
            news = get_news_from_newsapi(company)
            all_news.extend(news)
            print(f"    ✓ {company}: {len(news)} News")

    print(f"\n✅ {len(all_news)} News insgesamt gesammelt!")

    # Lese aktuelles HTML
    try:
        with open('valantic_market_intelligence.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
    except:
        print("❌ Dashboard-Datei nicht gefunden!")
        return False

    # Generiere neue Daten
    news_by_area = generate_html_data(all_news)

    # Erstelle neue companyData JavaScript
    company_data_js = "const companyData = [\n"
    counter = 1

    for area, news_list in news_by_area.items():
        for news in news_list:
            date_str = news['date']
            title_esc = news['title'].replace('"', '\\"')
            search_query = f"{news['company']} {news['title'][:50]}".replace('"', '\\"')

            company_data_js += f"""      {{ id: {counter}, date: new Date('{date_str}'), company: '{news['company']}', area: '{area}', eventType: '{news['eventType']}', title: '{title_esc}', searchQuery: '{search_query}' }},\n"""
            counter += 1

    company_data_js += "    ];"

    # Ersetze alte Daten mit neuen
    pattern = r'const companyData = \[[\s\S]*?\];'
    html_content = re.sub(pattern, company_data_js, html_content)

    # Schreibe neues HTML
    try:
        with open('valantic_market_intelligence.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("✅ Dashboard erfolgreich updated!")
        return True
    except Exception as e:
        print(f"❌ Fehler beim Schreiben: {str(e)}")
        return False

if __name__ == '__main__':
    success = update_dashboard()
    if success:
        print("\n🎉 Update erfolgreich!")
        exit(0)
    else:
        print("\n❌ Update fehlgeschlagen!")
        exit(1)
