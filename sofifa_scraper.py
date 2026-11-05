import asyncio
import re
from playwright.async_api import async_playwright
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

async def scrape_team_playwright(team_name):
    print(f"\n🔍 Запускаем браузер для клуба: '{team_name}'...")
    
    async with async_playwright() as p:
        # Запускаем Chromium в фоновом режиме
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 1. Поиск клуба через страницу поиска SoFIFA
        search_url = f"https://sofifa.com/teams?keyword={team_name}"
        print(f"🔗 Переходим на поиск: {search_url}")
        await page.goto(search_url, wait_until="networkidle", timeout=60000)
        
        # Ждём появления таблицы (если Cloudflare пропустит)
        try:
            await page.wait_for_selector('table tbody tr', timeout=15000)
        except Exception:
            print("❌ Таблица поиска не появилась. Возможно, Cloudflare всё ещё блокирует.")
            await browser.close()
            return

        # Берём ссылку на первый клуб из результатов
        team_link = await page.query_selector('table tbody tr td a[href^="/team/"]')
        if not team_link:
            print(f"❌ Клуб '{team_name}' не найден на SoFIFA.")
            await browser.close()
            return
        
        team_url = "https://sofifa.com" + await team_link.get_attribute("href")
        print(f"✅ Страница клуба: {team_url}")
        
        # 2. Переходим на страницу клуба
        await page.goto(team_url, wait_until="networkidle", timeout=60000)
        
        try:
            await page.wait_for_selector('table tbody tr', timeout=15000)
        except Exception:
            print("❌ Таблица игроков не появилась.")
            await browser.close()
            return

        # 3. Парсим строки таблицы (используем селектор, который нашёлся в рабочих примерах[reference:1])
        rows = await page.query_selector_all('table.table-hover.persist-area tbody tr')
        if not rows:
            # Пробуем более общий селектор, если таблица имеет другой класс
            rows = await page.query_selector_all('table tbody tr')

        print(f"📊 Найдено {len(rows)} строк. Сверяем с базой...")
        
        db = Session(engine)
        db_players = db.query(Player).all()
        db_names = [p.name for p in db_players]
        updated = 0

        for row in rows:
            # Имя игрока
            name_el = await row.query_selector('td.col-name a')
            if not name_el: continue
            sofifa_name = (await name_el.inner_text()).strip()
            if not sofifa_name: continue

            # Цена, зарплата, контракт — ищем по `data-col` или по позиции
            val_el = await row.query_selector('td[data-col="vl"]')
            wage_el = await row.query_selector('td[data-col="wg"]')
            ct_el = await row.query_selector('td[data-col="tt"]')

            value_text = (await val_el.inner_text()).strip() if val_el else ""
            wage_text = (await wage_el.inner_text()).strip() if wage_el else ""
            contract_text = (await ct_el.inner_text()).strip() if ct_el else ""

            # Сопоставление имен
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
                        print(f"  🔍 Нечёткое: '{sofifa_name}' -> '{player.name}' ({match[1]:.0f}%)")

            if player:
                player.market_value = parse_money(value_text)
                player.wage = parse_money(wage_text)
                player.contract_until = parse_contract(contract_text)
                updated += 1
                print(f"  ✅ {player.name} | Цена: {value_text} | ЗП: {wage_text} | Контракт: {contract_text}")
            else:
                print(f"  ❌ Нет в базе: '{sofifa_name}'")

        db.commit()
        db.close()
        print(f"\n📈 ИТОГ: Обновлено {updated} из {len(rows)}.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_team_playwright("FC Bayern München"))