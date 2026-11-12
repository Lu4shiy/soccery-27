import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
import random
import json
from main import engine, Club, Player

def restore_original_database():
    db = Session(engine)
    
    print("1. Создаем бэкап всех текущих игроков (включая вашу кастомную команду)...")
    backup_players = []
    for p in db.query(Player).all():
        p_dict = {k: v for k, v in p.__dict__.items() if not k.startswith('_')}
        backup_players.append(p_dict)
        
    print(f"Сохранено в бэкап: {len(backup_players)} игроков.")
    
    print("2. Очищаем таблицу игроков...")
    db.query(Player).delete()
    db.commit()
    
    print("3. Загружаем оригинальных игроков из players.csv...")
    df = pd.read_csv("players.csv")
    df = df[df['gender'] == "Men's Football"]
    df = df[~df['league'].isin(['UEFA Champions League', 'FIFA World Cup', 'European Championship'])]
    
    # Создаем клубы, если их нет
    clubs_data = df[['club', 'league']].drop_duplicates()
    club_map = {}
    for _, row in clubs_data.iterrows():
        if pd.isna(row['club']): continue
        club_name = str(row['club']).strip()
        existing = db.query(Club).filter_by(name=club_name).first()
        if not existing:
            new_club = Club(name=club_name, league=str(row['league']).strip())
            db.add(new_club)
            db.commit()
            db.refresh(new_club)
            club_map[club_name] = new_club.id
        else:
            club_map[club_name] = existing.id
            
    count = 0
    csv_player_ids = set()
    for _, row in df.iterrows():
        if pd.isna(row['club']): continue
        club_name = str(row['club']).strip()
        club_id = club_map.get(club_name)
        if not club_id: continue
        
        name = str(row['common_name']).strip() if pd.notna(row['common_name']) else f"{row['first_name']} {row['last_name']}".strip()
        
        birthdate_str = row.get('birthdate')
        age = 0
        if pd.notna(birthdate_str):
            try:
                age = 2026 - datetime.strptime(birthdate_str, '%d-%m-%Y').year
            except: pass
            
        def get_val(col):
            val = row.get(col)
            return int(val) if pd.notna(val) else 0
            
        pid = int(row['player_id'])
        csv_player_ids.add(pid)
        
        p = Player(
            player_id=pid,
            name=name, position=str(row['position']), overall_rating=int(row['overall_rating']),
            age=age, nationality=str(row['nationality']), club_id=club_id,
            preferred_foot=str(row['preferred_foot']),
            pace=get_val('pace'), shooting=get_val('shooting'), passing=get_val('passing'),
            dribbling=get_val('dribbling'), defending=get_val('defending'), physicality=get_val('physicality'),
            gk_diving=get_val('goalkeeping_diving'), gk_handling=get_val('goalkeeping_handling'),
            gk_kicking=get_val('goalkeeping_kicking'), gk_positioning=get_val('goalkeeping_positioning'),
            gk_reflexes=get_val('goalkeeping_reflexes'),
            potential=int(row['overall_rating']) + random.randint(0, 10)
        )
        db.add(p)
        count += 1
        if count % 1000 == 0:
            db.commit()
    db.commit()
    
    print("4. Восстанавливаем кастомных игроков...")
    restored_custom = 0
    for b in backup_players:
        if b['player_id'] not in csv_player_ids:
            del b['id'] # Удаляем старый ID, чтобы SQLAlchemy выдал новый
            if 'original_data' in b: del b['original_data'] # Будет пересоздан
            db.add(Player(**b))
            restored_custom += 1
    db.commit()
    print(f"Восстановлено кастомных игроков: {restored_custom}")
    
    print("5. Генерируем финансы по вашей формуле...")
    players_with_clubs = db.query(Player, Club).join(Club, Player.club_id == Club.id).all()
    current_year = 2026
    
    for p, club in players_with_clubs:
        ovr = p.overall_rating or 50
        age = p.age or 25
        pos = p.position or ""
        
        if ovr >= 70:
            base_val = ((ovr - 50) ** 3) * 1000
            if ovr >= 85: base_val *= 1.1
        else:
            base_val = ((max(0, ovr - 40)) ** 3) * 30
            if base_val < 5000: base_val = 5000

        l = club.league.lower() if club.league else ""
        if "premier league" in l or "laliga" in l or "la liga" in l: mult_league = 1.5
        elif "bundesliga" in l or "serie a" in l or "ligue 1" in l: mult_league = 1.2
        elif "championship" in l or "eredivisie" in l or "portugal" in l or "mls" in l or "saudi" in l: mult_league = 0.7
        else: mult_league = 0.2

        if "Goalkeeper" in pos: mult_pos = 0.4
        elif "Back" in pos: mult_pos = 1.0
        elif "Midfield" in pos: mult_pos = 1.1
        else: mult_pos = 1.3 

        if age <= 20: mult_age = 1.6
        elif age <= 25: mult_age = 1.2
        elif age <= 28: mult_age = 1.0
        elif age <= 31: mult_age = 0.6
        elif age <= 34: mult_age = 0.25
        else: mult_age = 0.05

        market_value = int(base_val * mult_league * mult_pos * mult_age)
        market_value = max(10000, round(market_value / 10000) * 10000)

        base_wage_k = ((max(60, ovr) - 50) ** 3) * 2
        random.seed(p.id)
        wage_variance = random.uniform(0.85, 1.15)
        wage_pos_mult = 0.7 if "Goalkeeper" in pos else 1.0
        
        wage_k = int(base_wage_k * mult_league * wage_variance * wage_pos_mult)
        wage = max(1, wage_k) * 1000 
        wage = round(wage / 500) * 500

        if age <= 20: years_left = random.randint(4, 5)
        elif age <= 23: years_left = random.randint(3, 4)
        elif age <= 27: years_left = random.randint(2, 4)
        elif age <= 30: years_left = random.randint(2, 3)
        else: years_left = random.randint(1, 2)
            
        contract_until = f"{current_year + years_left}-06-30"

        p.market_value = market_value
        p.wage = wage
        p.contract_until = contract_until
        
    db.commit()
    
    print("6. Фиксируем эталонные данные (original_data)...")
    for p in db.query(Player).all():
        orig = {
            'age': p.age, 'overall_rating': p.overall_rating, 'market_value': p.market_value,
            'wage': p.wage, 'pace': p.pace, 'shooting': p.shooting, 'passing': p.passing,
            'dribbling': p.dribbling, 'defending': p.defending, 'physicality': p.physicality,
            'gk_diving': p.gk_diving, 'gk_handling': p.gk_handling, 'gk_kicking': p.gk_kicking,
            'gk_positioning': p.gk_positioning, 'gk_reflexes': p.gk_reflexes
        }
        p.original_data = json.dumps(orig)
        
    db.commit()
    db.close()
    print("✅ ГОТОВО! База полностью восстановлена. Теперь при сбросе карьеры в игре все вернется к этим правильным значениям.")

if __name__ == "__main__":
    restore_original_database()