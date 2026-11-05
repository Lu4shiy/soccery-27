import asyncio
import re
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, Session
from rapidfuzz import fuzz

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
    club_id = Column(Integer) # Добавили для фильтрации
    market_value = Column(Integer)
    wage = Column(Integer)
    contract_until = Column(String)

class Club(Base):
    __tablename__ = "clubs"
    id = Column(Integer, primary_key=True)
    name = Column(String)

def parse_money(text):
    if not text or '€' not in text: return 0
    text = text.replace('€', '').replace(',', '').strip()
    # Берем только первую часть, если там вдруг пробелы (например "€31K")
    text = text.split()[0] if text else ""
    try:
        if text.endswith('M'): return int(float(text[:-1]) * 1_000_000)
        if text.endswith('K'): return int(float(text[:-1]) * 1_000)
        return int(float(text))
    except:
        return 0

def parse_contract(contract_text):
    if not contract_text: return None
    years = re.findall(r'\b(20\d{2})\b', contract_text)
    if years:
        return f"{int(years[-1])}-06-30" # Берем последний год из строки
    return None

# Умное сравнение имен
def is_name_match(sofifa_name, db_name):
    s_name = sofifa_name.lower().replace('.', '').replace('-', ' ').strip()
    d_name = db_name.lower().replace('.', '').replace('-', ' ').strip()
    
    s_parts = s_name.split()
    d_parts = d_name.split()
    
    if not s_parts or not d_parts: return False
    
    s_last = s_parts[-1]
    d_last = d_parts[-1]
    
    # Фамилии должны совпадать
    if fuzz.ratio(s_last, d_last) < 80:
        return False
        
    # Если имя сокращено (например, "a davies"), проверяем первую букву
    if len(s_parts) > 1 and len(s_parts[0]) == 1:
        return d_parts[0].startswith(s_parts[0])
        
    # Если оба полные, проверяем общую схожесть
    return fuzz.token_sort_ratio(s_name, d_name) > 80

async def scrape_team_playwright(team_name):
    print(f"\n🔍 Запускаем браузер для клуба: '{team_name}'...")
    
    db = Session(engine)
    # 1. Находим клуб в базе, чтобы отфильтровать игроков
    club = db.query(Club).filter(Club.name.ilike(f"%{team_name}%")).first()
    if club:
        db_players = db.query(Player).filter(Player.club_id == club.id).all()
        print(f"📋 В базе найдено {len(db_players)} игроков этого клуба.")
    else:
        db_players = db.query(Player).all()
        print(f"⚠️ Клуб не найден в базе по имени, ищем по всем игрокам ({len(db_players)}).")

    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await context.new_page()

        search_url = f"https://sofifa.com/teams?keyword={team_name}"
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000) 
            await page.wait_for_selector('table tbody tr', timeout=15000)
        except Exception as e:
            print(f"❌ Cloudflare не пропустил. Ошибка: {e}")
            await browser.close()
            return

        team_link = await page.query_selector('table tbody tr td a[href^="/team/"]')
        if not team_link:
            print(f"❌ Клуб '{team_name}' не найден на SoFIFA.")
            await browser.close()
            return
        
        team_url = "https://sofifa.com" + await team_link.get_attribute("href")
        await page.goto(team_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        
        try:
            await page.wait_for_selector('table tbody tr', timeout=15000)
        except Exception:
            print("❌ Таблица игроков не появилась.")
            await browser.close()
            return

        rows = await page.query_selector_all('table.table-hover.persist-area tbody tr')
        if not rows:
            rows = await page.query_selector_all('table tbody tr')

        print(f"📊 Считано {len(rows)} игроков с SoFIFA. Обновляем...")
        
        updated = 0

        for row in rows:
            try:
                name_el = await row.query_selector('td.col-name a')
                if not name_el: continue
                sofifa_name = (await name_el.inner_text()).strip()
                if not sofifa_name: continue

                # Ищем все ячейки td в строке
                tds = await row.query_selector_all('td')
                value_text = ""
                wage_text = ""
                contract_text = ""
                
                # Перебираем ячейки, чтобы найти цену, ЗП и контракт
                for td in tds:
                    text = (await td.inner_text()).strip()
                    if not text: continue
                    
                    if '€' in text:
                        if not value_text: value_text = text
                        elif not wage_text: wage_text = text
                    
                    # Контракт содержит 4-значный год (например, 2027) и не является ценой
                    if '€' not in text and re.search(r'\b(20\d{2})\b', text):
                        if not contract_text: contract_text = text

                # Ищем игрока в отфильтрованном списке клуба
                player = None
                for p in db_players:
                    if is_name_match(sofifa_name, p.name):
                        player = p
                        break

                if player:
                    player.market_value = parse_money(value_text)
                    player.wage = parse_money(wage_text)
                    player.contract_until = parse_contract(contract_text)
                    updated += 1
                    print(f"  ✅ {player.name} <- {sofifa_name} | {value_text} | {wage_text} | {contract_text}")
                else:
                    print(f"  ❌ Нет в базе: '{sofifa_name}'")
            except Exception as e:
                pass

        db.commit()
        db.close()
        print(f"\n📈 ИТОГ: Обновлено {updated} из {len(rows)}.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_team_playwright("FC Bayern München"))