import asyncio
import re
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async  # <-- ИМПОРТ БИБЛИОТЕКИ
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, Session
from rapidfuzz import process, fuzz

# ... (ваша настройка БД и модели Player без изменений) ...

async def scrape_team_playwright(team_name):
    print(f"\n🔍 Запускаем браузер для клуба: '{team_name}'...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # --- ПРИМЕНЯЕМ STEALTH ---
        await stealth_async(page)
        print("🛡️ Stealth-режим активирован.")

        search_url = f"https://sofifa.com/teams?keyword={team_name}"
        print(f"🔗 Переходим на поиск: {search_url}")
        
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            # Даем Cloudflare время на проверку и рендеринг
            await page.wait_for_timeout(5000) 
            
            # Ждем появления таблицы с результатами
            await page.wait_for_selector('table tbody tr', timeout=15000)
        except Exception as e:
            print(f"❌ Таблица поиска не появилась. Ошибка: {e}")
            await browser.close()
            return

        team_link = await page.query_selector('table tbody tr td a[href^="/team/"]')
        if not team_link:
            print(f"❌ Клуб '{team_name}' не найден на SoFIFA.")
            await browser.close()
            return
        
        team_url = "https://sofifa.com" + await team_link.get_attribute("href")
        print(f"✅ Страница клуба: {team_url}")
        
        await page.goto(team_url, wait_until="domcontentloaded", timeout=60000)
        
        try:
            await page.wait_for_selector('table tbody tr', timeout=15000)
        except Exception:
            print("❌ Таблица игроков не появилась.")
            await browser.close()
            return

        rows = await page.query_selector_all('table.table-hover.persist-area tbody tr')
        if not rows:
            rows = await page.query_selector_all('table tbody tr')

        print(f"📊 Найдено {len(rows)} строк. Сверяем с базой...")
        
        # ... (остальная логика сопоставления и обновления БД без изменений) ...
        # ... (не забудьте добавить await browser.close() в конце) ...

if __name__ == "__main__":
    asyncio.run(scrape_team_playwright("FC Bayern München"))