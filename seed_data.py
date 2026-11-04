import os
import requests
from sqlalchemy.orm import Session
from main import engine, Base, Club, Player

BASE_URL = "https://www.thesportsdb.com/api/v1/json/3"

# Словарь, который связывает название лиги с её страной
LEAGUE_COUNTRIES = {
    "English Premier League": "England",
    "Spanish La Liga": "Spain",
    "Italian Serie A": "Italy"
}

def get_teams_from_league(league_name: str, country: str):
    """Ищет все команды в указанной лиге и стране."""
    # 1. Ищем лиги в указанной стране
    search_url = f"{BASE_URL}/search_all_leagues.php?c={country}&s=Soccer"
    response = requests.get(search_url)
    if response.status_code != 200:
        print(f"Ошибка сети при поиске лиги {league_name}")
        return []

    leagues = response.json().get('countries')  # Ключ ответа именно 'countries'
    if not leagues:
        print(f"В стране {country} не найдено лиг.")
        return []

    # 2. Ищем нужную лигу по названию среди найденных
    target_league = None
    for league in leagues:
        if league.get('strLeague') == league_name:
            target_league = league
            break

    if not target_league:
        print(f"Лига '{league_name}' не найдена в стране {country}.")
        return []

    league_id = target_league['idLeague']
    print(f"Найдена лига: {league_name} (ID: {league_id})")

    # 3. Получаем все команды для этой лиги
    teams_url = f"{BASE_URL}/lookup_all_teams.php?id={league_id}"
    teams_response = requests.get(teams_url)
    return teams_response.json().get('teams', [])

def get_players_from_team(team_id: str):
    """Получает список игроков для указанной команды."""
    players_url = f"{BASE_URL}/lookup_all_players.php?id={team_id}"
    response = requests.get(players_url)
    return response.json().get('player', [])

def seed_database():
    """Основная функция для заполнения базы данных."""
    db = Session(engine)

    # Используем словарь для перебора лиг и их стран
    for league_name, country in LEAGUE_COUNTRIES.items():
        print(f"\n--- Загрузка данных для лиги: {league_name} ---")
        teams = get_teams_from_league(league_name, country)

        for team_data in teams:
            team_name = team_data.get('strTeam')
            if not team_name:
                continue

            existing_club = db.query(Club).filter_by(name=team_name).first()
            if not existing_club:
                new_club = Club(
                    name=team_name,
                    league=team_data.get('strLeague', league_name)
                )
                db.add(new_club)
                db.commit()
                db.refresh(new_club)
                print(f"  Добавлен клуб: {new_club.name}")

                # Загружаем игроков
                players = get_players_from_team(team_data['idTeam'])
                for player_data in players:
                    player_name = player_data.get('strPlayer')
                    if not player_name:
                        continue

                    existing_player = db.query(Player).filter_by(name=player_name).first()
                    if not existing_player:
                        new_player = Player(
                            name=player_name,
                            position=player_data.get('strPosition', 'Unknown'),
                            rating=player_data.get('intRating', 70),
                            club_id=new_club.id
                        )
                        db.add(new_player)
                        print(f"    Добавлен игрок: {new_player.name}")

        db.commit()  # Сохраняем изменения для текущей лиги

    db.close()
    print("\nЗагрузка данных завершена!")

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    seed_database()