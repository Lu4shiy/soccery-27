import os
import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime
from sqlalchemy.orm import Session
from main import engine, Player, Club

# Заголовки, чтобы SoFIFA не думала, что мы бот
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def parse_money(text):
    """Превращает '€17M' в 17000000, '€37K' в 37000"""
    if not text or not text.startswith('€'): return 0
    text = text.replace('€', '').strip()
    if text.endswith('M'): return int(float(text[:-1]) * 1_000_000)
    if text.endswith('K'): return int(float(text[:-1]) * 1_000)
    return int(float(text))

def parse_contract(contract_text):
    """Парсит '2024 ~ 2027' и возвращает дату окончания '2027-06-30'"""
    if not contract_text or '~' not in contract_text: return None
    # Извлекаем год окончания (второй год)
    years = re.findall(r'\d{4}', contract_text)
    if len(years) >= 2:
        end_year = int(years[1])
        # В футболе контракт обычно истекает 30 июня
        return f"{end_year}-06-30"
    return None

def scrape_team(team_name):
    """Ищет клуб на SoFIFA и парсит его состав"""
    print(f"🔍 Ищем клуб: {team_name}...")
    
    # 1. Ищем клуб через глобальный поиск SoFIFA
    search_url = f"https://sofifa.com/teams?keyword={requests.utils.quote(team_name)}"
    response = requests.get(search_url, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Ищем ссылку на первый найденный клуб в таблице
    team_link = soup.select_one('table tbody tr td a[href^="/team/"]')
    if not team_link:
        print(f"❌ Клуб '{team_name}' не найден на SoFIFA.")
        return False
        
    team_url = "https://sofifa.com" + team_link['href']
    print(f"✅ Найдена страница: {team_url}")
    
    # 2. Загружаем страницу клуба
    time.sleep(1) # Пауза, чтобы не забанил Cloudflare
    team_page = requests.get(team_url, headers=HEADERS)
    team_soup = BeautifulSoup(team_page.text, 'html.parser')
    
    # 3. Ищем таблицу с игроками
    rows = team_soup.select('table tbody tr')
    if not rows:
        print("❌ Не удалось найти таблицу с игроками.")
        return False
        
    print(f"📊 Найдено {len(rows)} строк. Обновляем базу...")
    
    db = Session(engine)
    updated_count = 0
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 8: continue
        
        try:
            # Извлекаем имя игрока
            name_tag = cols[1].find('a')
            player_name = name_tag.text.strip() if name_tag else cols[1].text.strip()
            
            # Извлекаем данные по колонкам (индексы могут меняться, берем по тексту)
            # Колонки: 0-флаг, 1-имя, 2-возраст, 3-рейтинг, 4-потенциал, 5-контракт, 6-зарплата, 7-стоимость
            contract_text = cols[5].text.strip()
            wage_text = cols[6].text.strip()
            value_text = cols[7].text.strip()
            
            # Ищем игрока в нашей базе
            player = db.query(Player).filter(Player.name.ilike(f"%{player_name}%")).first()
            
            if player:
                player.wage = parse_money(wage_text)
                player.market_value = parse_money(value_text)
                player.contract_until = parse_contract(contract_text)
                updated_count += 1
                print(f"  🔄 {player_name}: ЗП {player.wage}, Цена {player.market_value}, Контракт до {player.contract_until}")
            else:
                # Если в базе нет (например, имя отличается), пропускаем
                pass
                
        except Exception as e:
            print(f"  ⚠️ Ошибка при парсинге строки: {e}")
            continue
            
    db.commit()
    db.close()
    print(f"✅ Готово! Обновлено игроков: {updated_count}")
    return True

if __name__ == "__main__":
    # Список клубов, которые нужно обновить (можешь добавить все)
    clubs_to_update = [
        "Real Madrid", "Manchester City", "FC Barcelona", 
        "Bayern Munich", "Paris Saint-Germain", "Arsenal"
    ]
    
    for club in clubs_to_update:
        scrape_team(club)
        print("-" * 30)
        time.sleep(2) # Пауза между клубами