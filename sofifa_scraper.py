import asyncio
import re
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, Session
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
        # Запускаем браузер с реалистичным User-Agent
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"] # Скрываем, что это робот
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        # Применяем Stealth (маскировку)
        await stealth_async(page)
        print("🛡️ Stealth-режим активирован.")

        search_url = f"https://sofifa.com/teams?keyword={team_name}"
        print(f"🔗 Переходим на поиск: {search_url}")
        
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            # Даем Cloudflare 5 секунд, чтобы проверить браузер и пропустить нас
            print("⏳ Ждем прохождения защиты Cloudflare (5 сек)...")
            await page.wait_for_timeout(5000) 
            
            # Ждем появления таблицы
            await page.wait_for_selector('table tbody tr', timeout=15000)
        except Exception as e:
            print(f"❌ Таблица поиска не появилась. Cloudflare снова блокирует. Ошибка: {e}")
            await browser.close()
            return

        # Ищем ссылку на клуб
        team_link = await page.query_selector('table tbody tr td a[href^="/team/"]')
        if not team_link:
            print(f"❌ Клуб '{team_name}' не найден на SoFIFA.")
            await browser.close()
            return
        
        team_url = "https://sofifa.com" + await team_link.get_attribute("href")
        print(f"✅ Страница клуба: {team_url}")
        
        # Переходим на страницу клуба
        await page.goto(team_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000) # Пауза перед парсингом
        
        try:
            await page.wait_for_selector('table tbody tr', timeout=15000)
        except Exception:
            print("❌ Таблица игроков не появилась.")
            await browser.close()
            return

        # Собираем строки таблицы
        rows = await page.query_selector_all('table.table-hover.persist-area tbody tr')
        if not rows:
            rows = await page.query_selector_all('table tbody tr')

        print(f"📊 Найдено {len(rows)} строк. Сверяем с базой...")
        
        db = Session(engine)
        db_players = db.query(Player).all()
        db_names = [p.name for p in db_players]
        updated = 0

        for row in rows:
            try:
                # Имя игрока
                name_el = await row.query_selector('td.col-name a')
                if not name_el: continue
                sofifa_name = (await name_el.inner_text()).strip()
                if not sofifa_name: continue

                # Цена, зарплата, контракт
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
            except Exception as e:
                pass

        db.commit()
        db.close()
        print(f"\n📈 ИТОГ: Обновлено {updated} из {len(rows)}.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_team_playwright("FC Bayern München"))