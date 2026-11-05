import os
import re
import time
import cloudscraper
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, Session
from urllib.parse import quote
from rapidfuzz import process, fuzz

# --- НАСТРОЙКА БАЗЫ ДАННЫХ ---
DATABASE_URL = "postgresql://neondb_owner:npg_KpNaC4uhstX3@ep-purple-rice-b9sdria3-pooler.c-7.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

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
    print(f"\n🔍 Ищем клуб: '{team_name}'...")
    search_url = f"https://sofifa.com/teams?keyword={quote(team_name)}"
    
    try:
        response = scraper.get(search_url)
        if "Just a moment..." in response.text:
            print("❌ ОШИБКА: Cloudflare заблокировал запрос.")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        team_link = soup.select_one('table tbody tr td a[href^="/team/"]')
        if not team_link:
            print(f"❌ Клуб '{team_name}' не найден.")
            return
            
        team_url = "https://sofifa.com" + team_link['href']
        print(f"✅ Страница клуба: {team_url}")
        
        time.sleep(2)
        team_page = scraper.get(team_url)
        team_soup = BeautifulSoup(team_page.text, 'html.parser')
        rows = team_soup.select('table tbody tr')
        if not rows:
            print("❌ Таблица игроков не найдена.")
            return
            
        print(f"📊 Найдено {len(rows)} игроков. Сверяем с базой...")
        
        db = Session(engine)
        
        # 1. Загружаем всех игроков этого клуба из базы для нечеткого поиска
        # (в реальном коде нужно передать club_id, но для теста ищем по всем игрокам)
        db_players = db.query(Player).all()
        db_names = [p.name for p in db_players]
        
        updated = 0
        not_found = []
        
        for row in rows:
            try:
                name_tag = row.select_one('td[data-col="pn"] a')
                if not name_tag: continue
                sofifa_name = name_tag.text.strip()
                
                val_tag = row.select_one('td[data-col="vl"]')
                wage_tag = row.select_one('td[data-col="wg"]')
                ct_tag = row.select_one('td[data-col="ct"]')
                
                value_text = val_tag.text.strip() if val_tag else ""
                wage_text = wage_tag.text.strip() if wage_tag else ""
                contract_text = ct_tag.text.strip() if ct_tag else ""
                
                # --- ЛОГИКА ПОИСКА ---
                player = None
                
                # 1. Пробуем точное совпадение (без учета регистра)
                for p in db_players:
                    if sofifa_name.lower() in p.name.lower() or p.name.lower() in sofifa_name.lower():
                        player = p
                        break
                
                # 2. Если точного нет, используем нечеткий поиск (Fuzzy)
                if not player:
                    # Ищем лучшее совпадение с порогом схожести 70%
                    match = process.extractOne(sofifa_name, db_names, scorer=fuzz.token_sort_ratio)
                    if match and match[1] >= 70:
                        best_name = match[0]
                        player = next((p for p in db_players if p.name == best_name), None)
                        if player:
                            print(f"  🔍 Нечеткое совпадение: SoFIFA '{sofifa_name}' -> База '{player.name}' ({match[1]}%)")
                
                if player:
                    player.market_value = parse_money(value_text)
                    player.wage = parse_money(wage_text)
                    player.contract_until = parse_contract(contract_text)
                    updated += 1
                    print(f"  ✅ Обновлен: {player.name} | Цена: {value_text} | ЗП: {wage_text}")
                else:
                    not_found.append(sofifa_name)
                    print(f"  ❌ Не найден в базе: '{sofifa_name}'")
                    
            except Exception as e:
                print(f"  ⚠️ Ошибка строки: {e}")
                
        db.commit()
        db.close()
        
        print(f"\n📈 ИТОГ: Обновлено {updated} из {len(rows)}.")
        if not_found:
            print(f"⚠️ Не найдено игроков: {len(not_found)}")
            print("Примеры ненайденных имен (первые 10):", not_found[:10])
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    # Для теста берем один клуб
    scrape_team("FC Bayern München")