import os
import requests
from sqlalchemy.orm import Session
from main import engine, Base, Club, Player  # Импортируем наши модели из main.py

# Базовый URL для бесплатного API TheSportsDB
BASE_URL = "https://www.thesportsdb.com/api/v1/json/3"

def get_teams_from_league(league_name: str):
    """Ищет все команды в указанной лиге."""
    # Поиск лиги по названию
    search_url = f"{BASE_URL}/search_all_leagues.php?s=Soccer&c={league_name}"
    response = requests.get(search_url)
    if response.status_code != 200:
        print(f"Не удалось найти лигу {league_name}")
        return []

    leagues = response.json().get('countries')
    if not leagues:
        return []

    league_id = leagues[0]['idLeague']
    # Получение всех команд в лиге
    teams_url = f"{BASE_URL}/lookup_all_teams.php?id={league_id}"
    teams_response = requests.get(teams_url)
    return teams_response.json().get('teams', [])

def get_players_from_team(team_id: str):
    """Получает список игроков для указанной команды."""
    # Примечание: эндпоинт для игроков может быть ограничен, но для базового списка этого достаточно
    players_url = f"{BASE_URL}/lookup_all_players.php?id={team_id}"
    response = requests.get(players_url)
    return response.json().get('player', [])

def seed_database():
    """Основная функция для заполнения базы данных."""
    db = Session(engine)

    # Список лиг, которые мы хотим загрузить (для примера берем несколько)
    leagues_to_load = ["English Premier League", "Spanish La Liga", "Italian Serie A"]

    for league_name in leagues_to_load:
        print(f"Загрузка данных для лиги: {league_name}")
        teams = get_teams_from_league(league_name)

        for team_data in teams:
            # Проверяем, нет ли уже такой команды в базе
            existing_club = db.query(Club).filter_by(name=team_data['strTeam']).first()
            if not existing_club:
                new_club = Club(
                    name=team_data['strTeam'],
                    league=team_data['strLeague']
                )
                db.add(new_club)
                db.commit()
                db.refresh(new_club)  # Обновляем объект, чтобы получить его ID
                print(f"  Добавлен клуб: {new_club.name}")

                # Загружаем игроков для этой команды
                players = get_players_from_team(team_data['idTeam'])
                for player_data in players:
                    # Проверка на существующего игрока, чтобы избежать дублей
                    existing_player = db.query(Player).filter_by(name=player_data['strPlayer']).first()
                    if not existing_player:
                        new_player = Player(
                            name=player_data['strPlayer'],
                            position=player_data.get('strPosition', 'Unknown'),
                            rating=player_data.get('intRating', 70),  # Пример рейтинга
                            club_id=new_club.id
                        )
                        db.add(new_player)
                        print(f"    Добавлен игрок: {new_player.name}")

        db.commit()  # Сохраняем все изменения для текущей лиги

    db.close()
    print("Загрузка данных завершена!")

if __name__ == "__main__":
    # Создаем таблицы (если их еще нет) перед заполнением
    Base.metadata.create_all(bind=engine)
    seed_database()