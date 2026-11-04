import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from main import engine, Base, Club, Player

def seed_from_csv():
    db = Session(engine)
    
    print("Чтение players.csv...")
    df = pd.read_csv("players.csv")
    
    # 1. Фильтр: только мужской футбол
    df = df[df['gender'] == "Men's Football"]
    
    # 2. Исключаем ЛЧ и турниры сборных (на случай, если они там есть)
    exclude_leagues = ['UEFA Champions League', 'FIFA World Cup', 'European Championship']
    df = df[~df['league'].isin(exclude_leagues)]
    
    print("Создание клубов и лиг...")
    # Создаем клубы, чтобы у них были ID
    clubs_data = df[['club', 'league']].drop_duplicates()
    club_map = {}
    
    for _, row in clubs_data.iterrows():
        if pd.isna(row['club']): continue
        club_name = str(row['club']).strip()
        league_name = str(row['league']).strip()
        
        existing = db.query(Club).filter_by(name=club_name).first()
        if not existing:
            new_club = Club(name=club_name, league=league_name)
            db.add(new_club)
            db.commit()
            db.refresh(new_club)
            club_map[club_name] = new_club.id
        else:
            club_map[club_name] = existing.id
            
    print(f"Добавлено клубов: {len(club_map)}")
    
    print("Добавление игроков (это займет около минуты)...")
    count = 0
    for _, row in df.iterrows():
        if pd.isna(row['club']): continue
        club_name = str(row['club']).strip()
        club_id = club_map.get(club_name)
        if not club_id: continue
        
        # Имя (используем common_name, если есть, иначе имя+фамилия)
        if pd.notna(row['common_name']):
            name = str(row['common_name']).strip()
        else:
            name = f"{row['first_name']} {row['last_name']}".strip()
            
        # Считаем возраст из даты рождения (формат DD-MM-YYYY)
        birthdate_str = row.get('birthdate')
        age = 0
        if pd.notna(birthdate_str):
            try:
                birthdate = datetime.strptime(birthdate_str, '%d-%m-%Y')
                age = 2026 - birthdate.year # Считаем возраст на текущий год игры
            except:
                pass
        
        # Безопасное извлечение характеристик (чтобы не было ошибок, если ячейка пустая)
        def get_val(col):
            val = row.get(col)
            return int(val) if pd.notna(val) else 0

        new_player = Player(
            player_id=int(row['player_id']),
            name=name,
            position=str(row['position']),
            overall_rating=int(row['overall_rating']),
            age=age,
            nationality=str(row['nationality']),
            club_id=club_id,
            preferred_foot=str(row['preferred_foot']),
            pace=get_val('pace'),
            shooting=get_val('shooting'),
            passing=get_val('passing'),
            dribbling=get_val('dribbling'),
            defending=get_val('defending'),
            physicality=get_val('physicality'),
            gk_diving=get_val('goalkeeping_diving'),
            gk_handling=get_val('goalkeeping_handling'),
            gk_kicking=get_val('goalkeeping_kicking'),
            gk_positioning=get_val('goalkeeping_positioning'),
            gk_reflexes=get_val('goalkeeping_reflexes')
        )
        db.add(new_player)
        count += 1
        
        # Сохраняем пачками по 1000, чтобы не перегружать память
        if count % 1000 == 0:
            db.commit()
            print(f"Добавлено {count} игроков...")
    
    db.commit()
    db.close()
    print(f"ГОТОВО! Успешно загружено {count} игроков и {len(club_map)} клубов.")

if __name__ == "__main__":
    seed_from_csv()