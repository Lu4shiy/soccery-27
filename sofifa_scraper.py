import re
import cloudscraper
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, Session
from rapidfuzz import process, fuzz

# --- БАЗА ДАННЫХ ---
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

def scrape_bayern():
    # Прямая ссылка на страницу Баварии
    team_url = "https://sofifa.com/team/21/"
    print(f"🔍 Загружаем напрямую: {team_url}")
    
    try:
        response = scraper.get(team_url)
        if "Just a moment..." in response.text:
            print("❌ Cloudflare заблокировал прямой запрос.")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('table tbody tr')
        
        if not rows:
            print("❌ Таблица игроков не найдена (возможно, структура изменилась или это страница-заглушка).")
            return
            
        print(f"📊 Найдено {len(rows)} строк. Начинаем анализ первой строки...")
        
        # Выводим HTML первой строки, чтобы понять структуру
        print("\n--- HTML ПЕРВОЙ СТРОКИ ---")
        print(rows[0].prettify()[:800]) # Первые 800 символов для просмотра
        print("--------------------------\n")
        
        db = Session(engine)
        db_players = db.query(Player).all()
        db_names = [p.name for p in db_players]
        
        updated = 0
        
        for row in rows:
            try:
                # Ищем имя в любом теге <a> внутри ячейки
                name_a = row.select_one('td.col-name a')
                if not name_a:
                    name_a = row.select_one('a[href*="/player/"]')
                    
                if not name_a: continue
                sofifa_name = name_a.get_text(strip=True)
                if not sofifa_name: continue
                
                # Ищем данные по атрибуту data-col (у SoFIFA они плавают, пробуем разные варианты)
                val_tag = row.select_one('td[data-col="vl"]') or row.select_one('td[data-col="value"]')
                wage_tag = row.select_one('td[data-col="wg"]') or row.select_one('td[data-col="wage"]')
                ct_tag = row.select_one('td[data-col="tt"]') or row.select_one('td[data-col="ct"]')
                
                value_text = val_tag.get_text(strip=True) if val_tag else ""
                wage_text = wage_tag.get_text(strip=True) if wage_tag else ""
                contract_text = ct_tag.get_text(strip=True) if ct_tag else ""
                
                # Сопоставление
                player = None
                for p in db_players:
                    if sofifa_name.lower() in p.name.lower() or p.name.lower() in sofifa_name.lower():
                        player = p
                        break
                
                if not player:
                    match = process.extractOne(sofifa_name, db_names, scorer=fuzz.token_sort_ratio)
                    if match and match[1] >= 60: 
                        best_name = match[0]
                        player = next((p for p in db_players if p.name == best_name), None)

                if player:
                    player.market_value = parse_money(value_text)
                    player.wage = parse_money(wage_text)
                    player.contract_until = parse_contract(contract_text)
                    updated += 1
                    print(f"  ✅ {player.name} | Цена: {value_text} | ЗП: {wage_text} | Контракт: {contract_text}")
                else:
                    print(f"  ❌ Нет в базе: {sofifa_name} (SoFIFA: {value_text})")
                    
            except Exception as e:
                pass
                
        db.commit()
        db.close()
        print(f"\n📈 ИТОГ: Обновлено {updated} из {len(rows)}.")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    scrape_bayern()