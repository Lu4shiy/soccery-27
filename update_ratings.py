import pandas as pd
from sqlalchemy.orm import Session
from main import engine, Player

def update_ratings():
    print("Загрузка CSV файла...")
    try:
        # Читаем файл, который вы перетащили в Codespaces
        df = pd.read_csv("players.csv")
    except FileNotFoundError:
        print("Ошибка: Файл players.csv не найден в корне проекта!")
        return

    # ФИЛЬТР: Оставляем только мужской футбол
    print("Фильтрация женского футбола...")
    df = df[df['gender'] == "Men's Football"]

    # Создаем словарь для быстрого поиска: { "имя_в_нижнем_регистре": (рейтинг, позиция) }
    print("Создание базы данных игроков FC27...")
    fc27_players = {}
    for _, row in df.iterrows():
        rating = int(row['overall_rating'])
        position = str(row['position'])
        
        # Вариант 1: Используем common_name (например, "Vini Jr.")
        if pd.notna(row['common_name']):
            name = str(row['common_name']).lower().strip()
            fc27_players[name] = (rating, position)
            
        # Вариант 2: Используем Имя + Фамилия (например, "Erling Haaland")
        if pd.notna(row['first_name']) and pd.notna(row['last_name']):
            full_name = f"{row['first_name']} {row['last_name']}".lower().strip()
            fc27_players[full_name] = (rating, position)

    # Обновляем нашу базу данных
    print("Подключение к базе данных и обновление...")
    db = Session(engine)
    players_in_db = db.query(Player).all()
    
    updated_count = 0
    not_found_count = 0

    for player in players_in_db:
        db_name = player.name.lower().strip()
        
        # Ищем игрока из базы в словаре FC27
        if db_name in fc27_players:
            new_rating, new_position = fc27_players[db_name]
            player.rating = new_rating
            player.position = new_position
            updated_count += 1
        else:
            not_found_count += 1

    db.commit()
    db.close()
    
    print(f"\nГОТОВО!")
    print(f"Успешно обновлено игроков: {updated_count}")
    print(f"Не найдено в FC27 (имена не совпали): {not_found_count}")

if __name__ == "__main__":
    update_ratings()