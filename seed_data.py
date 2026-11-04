import os
import time
import requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from main import engine, Base, Club, Player

# Загружаем ключ из файла .env
load_dotenv()
API_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN")
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_TOKEN}

# Словарь: ID турнира на football-data.org -> Название для нашей базы
COMPETITIONS = {
    # Топ-5 (уже загружены)
    "PL": "English Premier League",
    "PD": "Spanish La Liga",
    "SA": "Italian Serie A",
    "BL1": "German Bundesliga",
    "FL1": "French Ligue 1",
    
    # Новые европейские лиги
    "PPL": "Portuguese Liga",       # Португалия
    "DED": "Dutch Eredivisie",      # Нидерланды
    "BSA": "Belgian Pro League",    # Бельгия
    "TR1": "Turkish Süper Lig",     # Турция
    
    # Вторые дивизионы (Все лиги Англии, Испании, Италии, Германии, Франции)
    "ELC": "English Championship",  # Англия (2-й дивизион)
    "SP2": "Spanish Segunda",       # Испания (2-й дивизион)
    "SB": "Italian Serie B",        # Италия (2-й дивизион)
    "BL2": "German 2. Bundesliga",  # Германия (2-й дивизион)
    "FL2": "French Ligue 2",        # Франция (2-й дивизион)
    
    # Америка
    "MLS": "Major League Soccer"    # США
}

def get_teams_from_competition(competition_code: str):
    """Получает все команды для указанного турнира."""
    url = f"{BASE_URL}/competitions/{competition_code}/teams"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"Ошибка при загрузке команд для {competition_code}: {response.status_code}")
        print(response.text)
        return []
    
    return response.json().get('teams', [])

def get_players_from_team(team_id: int):
    """Получает состав команды по её ID."""
    url = f"{BASE_URL}/teams/{team_id}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        return []
    
    team_data = response.json()
    return team_data.get('squad', [])

def seed_database():
    db = Session(engine)
    
    for comp_code, comp_name in COMPETITIONS.items():
        print(f"\n--- Загрузка данных для: {comp_name} ---")
        teams = get_teams_from_competition(comp_code)
        
        for team_data in teams:
            team_name = team_data.get('name')
            team_id = team_data.get('id')
            if not team_name or not team_id:
                continue
            
            # Проверяем, есть ли уже такой клуб в базе
            existing_club = db.query(Club).filter_by(name=team_name).first()
            if not existing_club:
                new_club = Club(name=team_name, league=comp_name)
                db.add(new_club)
                db.commit()
                db.refresh(new_club)
                print(f"  Добавлен клуб: {new_club.name}")
                
                # Загружаем игроков
                players = get_players_from_team(team_id)
                for player_data in players:
                    player_name = player_data.get('name')
                    if not player_name:
                        continue
                    
                    existing_player = db.query(Player).filter_by(name=player_name).first()
                    if not existing_player:
                        new_player = Player(
                            name=player_name,
                            position=player_data.get('position', 'Unknown'),
                            rating=70, # У football-data.org нет рейтинга в бесплатной версии, ставим базовый
                            club_id=new_club.id
                        )
                        db.add(new_player)
                        print(f"    Добавлен игрок: {new_player.name}")
                
                db.commit()
                
                # ВАЖНО: Пауза 6.5 секунд, чтобы не превысить лимит 10 запросов в минуту
                print("  Ожидание 6.5 секунд (лимит API)...")
                time.sleep(6.5)
            else:
                print(f"  Клуб {team_name} уже есть в базе, пропускаем.")
    
    db.close()
    print("\nЗагрузка данных завершена!")

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    seed_database()