import asyncio
import re
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, Session

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
    club_id = Column(Integer)

class PlayerTemp(Base):
    __tablename__ = "player_transfers_temp"
    player_id = Column(Integer, primary_key=True)
    player_name = Column(String)
    new_market_value = Column(Integer)
    new_wage = Column(Integer)
    new_contract_until = Column(String)
    source = Column(String)

def parse_tm_money(text):
    """Превращает €75.00m в 75000000, €500k в 500000"""
    if not text or '€' not in text: return 0
    text = text.lower().replace('€', '').strip()
    try:
        if text.endswith('m'):
            return int(float(text[:-1]) * 1_000_000)
        if text.endswith('k'):
            return int(float(text[:-1]) * 1_000)
        return int(float(text))
    except:
        return 0

def parse_tm_contract(text):
    """Извлекает дату из 'Jun 30, 2027' -> '2027-06-30'"""
    if not text: return None
    match = re.search(r'(\w{3}) (\d{1,2}), (\d{4})', text)
    if match:
        months = {'Jan':'01', 'Feb':'02', 'Mar':'03', 'Apr':'04', 'May':'05', 'Jun':'06', 
                  'Jul':'07', 'Aug':'08', 'Sep':'09', 'Oct':'10', 'Nov':'11', 'Dec':'12'}
        m = months.get(match.group(1), '06')
        d = match.group(2).zfill(2)
        y = match.group(3)
        return f"{y}-{m}-{d}"
    return None

async def scrape_tm_for_players(club_name):
    print(f"\n🔍 Ищем данные на Transfermarkt для клуба: {club_name}")
    
    db = Session(engine)
    # Для теста берем только 5 игроков (потом уберешь лимит)
    players = db.query(Player).limit(5).all() 
    
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for player in players:
            print(f"  👤 Ищем: {player.name}...")
            try:
                # Ищем игрока через быстрый поиск TM
                search_url = f"https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query={player.name.replace(' ', '+')}"
                await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)

                # Ищем первую ссылку на профиль игрока в результатах
                player_link_el = await page.query_selector('table.items tbody tr td.hauptlink a')
                if not player_link_el:
                    print(f"    ❌ Не найден на TM: {player.name}")
                    continue
                
                profile_url = await player_link_el.get_attribute('href')
                if not profile_url.startswith('http'):
                    profile_url = "https://www.transfermarkt.com" + profile_url
                
                # Переходим на страницу игрока
                await page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)

                # Парсим рыночную стоимость
                mv_el = await page.query_selector('.dataMarktwert a, .marktwert a')
                market_value_text = (await mv_el.inner_text()).strip() if mv_el else ""
                
                # Парсим контракт
                contract_el = await page.query_selector('.dataVertrag a, .vertrag a')
                contract_text = (await contract_el.inner_text()).strip() if contract_el else ""

                val = parse_tm_money(market_value_text)
                ctu = parse_tm_contract(contract_text)
                
                # Расчет ЗП (если нет реальных данных, берем 0.5% от стоимости в неделю)
                wage = int((val * 0.005) / 52) if val > 0 else 0

                if val > 0:
                    print(f"    ✅ {player.name} | Цена: {market_value_text} ({val}) | Контракт: {ctu}")
                    
                    # Пишем во ВРЕМЕННУЮ таблицу!
                    temp_rec = db.query(PlayerTemp).filter_by(player_id=player.id).first()
                    if not temp_rec:
                        temp_rec = PlayerTemp(player_id=player.id)
                        db.add(temp_rec)
                    
                    temp_rec.player_name = player.name
                    temp_rec.new_market_value = val
                    temp_rec.new_wage = wage
                    temp_rec.new_contract_until = ctu
                    temp_rec.source = "Transfermarkt"
                    db.commit()
                else:
                    print(f"    ⚠️ Не удалось прочитать цену для {player.name}")
                
                await page.wait_for_timeout(2000) # Пауза между игроками
                
            except Exception as e:
                print(f"    ❌ Ошибка при парсинге {player.name}: {e}")

        await browser.close()
    db.close()
    print("\n✅ Парсинг завершен. Данные лежат во временной таблице.")

if __name__ == "__main__":
    asyncio.run(scrape_tm_for_players("FC Bayern München"))