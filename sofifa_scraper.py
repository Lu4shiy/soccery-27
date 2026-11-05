import os
import re
import time
import cloudscraper
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, Session
from urllib.parse import quote

# --- НАСТРОЙКА БАЗЫ ДАННЫХ ---
# ВСТАВЬ СВОЮ ССЫЛКУ ИЗ NEON ВМЕСТО ТЕКСТА В КАВЫЧКАХ:
DATABASE_URL = "postgresql://neondb_owner:пароль@ep-сервер.neon.tech/neondb?sslmode=require"

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL)
Base = declarative_base()

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    market_value = Column(Integer)
    wage = Column(Integer)
    contract_until = Column(String)
# ------------------------------

scraper = cloudscraper.create_scraper()

def parse_money(text):
    if not text or not text.startswith('€'): return 0
    text = text.replace('€', '').strip()
    if text.endswith('M'): return int(float(text[:-1]) * 1_000_000)
    if text.endswith('K'): return int(float(text[:-1]) * 1_000)
    return int(float(text))

def parse_contract(contract_text):
    if not contract_text or '~' not in contract_text: return None
    years = re.findall(r'\d{4}', contract_text)
    if len(years) >= 2:
        return f"{int(years[1])}-06-30"
    return None

def scrape_team(team_name):
    print(f"\n🔍 [1/4] Ищем клуб: '{team_name}'...")
    # ИСПРАВЛЕНО: используем quote из urllib
    search_url = f"https://sofifa.com/teams?keyword={quote(team_name)}"
    
    try:
        response = scraper.get(search_url)
        if "Just a moment..." in response.text or "Cloudflare" in response.text:
            print("❌ ОШИБКА: Cloudflare заблокировал запрос. Придется использовать Playwright.")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        team_link = soup.select_one('table tbody tr td a[href^="/team/"]')
        
        if not team_link:
            print(f"❌ Клуб '{team_name}' не найден на SoFIFA. Возможно, название отличается.")
            return
            
        team_url = "https://sofifa.com" + team_link['href']
        print(f"✅ [2/4] Страница клуба найдена: {team_url}")
        
        time.sleep(2)
        team_page = scraper.get(team_url)
        team_soup = BeautifulSoup(team_page.text, 'html.parser')
        
        rows = team_soup.select('table tbody tr')
        if not rows:
            print("❌ Не удалось найти таблицу с игроками на странице.")
            return
            
        print(f"✅ [3/4] Найдено {len(rows)} игроков на SoFIFA. Начинаем сверку с базой...")
        
        db = Session(engine)
        updated = 0
        
        for row in rows:
            try:
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
                    print(f"  🔄 Обновлен: {player.name} | Цена: {value_text} | ЗП: {wage_text} | Контракт: {contract_text}")
                else:
                    print(f"  ⚠️ Игрок '{player_name}' есть на SoFIFA, но НЕ НАЙДЕН в базе Neon.")
                    
            except Exception as e:
                print(f"  ⚠️ Ошибка парсинга строки: {e}")
                
        db.commit()
        db.close()
        print(f"✅ [4/4] УСПЕХ! Обновлено игроков в базе: {updated}")
        
    except Exception as e:
        print(f"❌ Сетевая ошибка: {e}")

if __name__ == "__main__":
    # Сюда впиши клубы (используй их ОФИЦИАЛЬНЫЕ названия, чтобы SoFIFA их нашла)
    clubs_to_update = [
        "FC Bayern München", "Real Madrid", "Manchester City"
    ]
    
    for club in clubs_to_update:
        scrape_team(club)
        print("-" * 30)
        time.sleep(3)