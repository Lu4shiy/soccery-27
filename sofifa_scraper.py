import cloudscraper
from bs4 import BeautifulSoup
import time
import re
from sqlalchemy.orm import Session
from main import engine, Player

# Создаем сессию, которая обходит Cloudflare
scraper = cloudscraper.create_scraper()

def parse_money(text):
    """Превращает '€17M' в 17000000, '€37K' в 37000"""
    if not text or not text.startswith('€'): return 0
    text = text.replace('€', '').strip()
    if text.endswith('M'): return int(float(text[:-1]) * 1_000_000)
    if text.endswith('K'): return int(float(text[:-1]) * 1_000)
    return int(float(text))

def parse_contract(contract_text):
    """Парсит '2024 ~ 2027' и возвращает '2027-06-30'"""
    if not contract_text or '~' not in contract_text: return None
    years = re.findall(r'\d{4}', contract_text)
    if len(years) >= 2:
        return f"{int(years[1])}-06-30"
    return None

def scrape_team(team_name):
    print(f"🔍 Ищем клуб: {team_name}...")
    search_url = f"https://sofifa.com/teams?keyword={scraper.utils.quote(team_name)}"
    
    try:
        response = scraper.get(search_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        team_link = soup.select_one('table tbody tr td a[href^="/team/"]')
        
        if not team_link:
            print(f"❌ Клуб '{team_name}' не найден.")
            return False
            
        team_url = "https://sofifa.com" + team_link['href']
        print(f"✅ Страница: {team_url}")
        
        time.sleep(2)
        team_page = scraper.get(team_url)
        team_soup = BeautifulSoup(team_page.text, 'html.parser')
        
        # Ищем таблицу игроков
        rows = team_soup.select('table tbody tr')
        if not rows:
            print("❌ Нет таблицы игроков. Возможно, блок Cloudflare.")
            return False
            
        print(f"📊 Найдено {len(rows)} игроков. Обновляем базу...")
        
        db = Session(engine)
        updated = 0
        
        for row in rows:
            try:
                # Ищем данные по data-col (надежнее, чем по индексам)
                name_tag = row.select_one('td[data-col="pn"] a')
                if not name_tag: continue
                player_name = name_tag.text.strip()
                
                val_tag = row.select_one('td[data-col="vl"]')
                wage_tag = row.select_one('td[data-col="wg"]')
                ct_tag = row.select_one('td[data-col="ct"]')
                
                value_text = val_tag.text.strip() if val_tag else ""
                wage_text = wage_tag.text.strip() if wage_tag else ""
                contract_text = ct_tag.text.strip() if ct_tag else ""
                
                player = db.query(Player).filter(Player.name.ilike(f"%{player_name}%")).first()
                if player:
                    player.market_value = parse_money(value_text)
                    player.wage = parse_money(wage_text)
                    player.contract_until = parse_contract(contract_text)
                    updated += 1
                    print(f"  🔄 {player_name}: {value_text}, {wage_text}, до {player.contract_until}")
            except Exception as e:
                pass
                
        db.commit()
        db.close()
        print(f"✅ Обновлено: {updated}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сети: {e}")
        return False

if __name__ == "__main__":
    # Сюда можешь вписать нужные клубы
    clubs_to_update = [
        "FC Bayern München", "Real Madrid", "Manchester City", 
        "Arsenal", "FC Barcelona", "Paris Saint-Germain"
    ]
    
    for club in clubs_to_update:
        scrape_team(club)
        print("-" * 30)
        time.sleep(3)