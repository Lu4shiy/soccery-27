import random
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, Session

# --- НАСТРОЙКА БАЗЫ ДАННЫХ ---
DATABASE_URL = "postgresql://neondb_owner:npg_KpNaC4uhstX3@ep-purple-rice-b9sdria3-pooler.c-7.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL)
Base = declarative_base()

class Club(Base):
    __tablename__ = "clubs"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    league = Column(String)

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    position = Column(String)
    overall_rating = Column(Integer)
    age = Column(Integer)
    club_id = Column(Integer, ForeignKey("clubs.id"))
    market_value = Column(Integer)
    wage = Column(Integer)
    contract_until = Column(String)

def generate_finances():
    db = Session(engine)
    players_with_clubs = db.query(Player, Club).join(Club, Player.club_id == Club.id).all()
    print(f"📊 Найдено {len(players_with_clubs)} игроков. Генерируем реалистичные финансы...")

    current_year = 2026
    updated = 0

    for p, club in players_with_clubs:
        ovr = p.overall_rating or 50
        age = p.age or 25
        pos = p.position or ""
        
        # --- 1. РАСЧЕТ СТОИМОСТИ ---
        if ovr >= 70:
            base_val = ((ovr - 50) ** 3) * 1000
            if ovr >= 85: base_val *= 1.1
        else:
            # Игроки ниже 70 рейтинга стоят копейки
            base_val = ((max(0, ovr - 40)) ** 3) * 30
            if base_val < 5000: base_val = 5000

        # Коэффициент лиги (АПЛ/ЛаЛига дороже)
        l = club.league.lower() if club.league else ""
        if "premier league" in l or "laliga" in l or "la liga" in l: mult_league = 1.5
        elif "bundesliga" in l or "serie a" in l or "ligue 1" in l: mult_league = 1.2
        elif "championship" in l or "eredivisie" in l or "portugal" in l or "mls" in l or "saudi" in l: mult_league = 0.7
        else: mult_league = 0.2 # Остальные (Индия и т.д.)

        # Позиция (Вратари дешевле, нападающие дороже)
        if "Goalkeeper" in pos: mult_pos = 0.4
        elif "Back" in pos: mult_pos = 1.0
        elif "Midfield" in pos: mult_pos = 1.1
        else: mult_pos = 1.3 

        # Возраст (Пик 21-25 лет)
        if age <= 20: mult_age = 1.6
        elif age <= 25: mult_age = 1.2
        elif age <= 28: mult_age = 1.0
        elif age <= 31: mult_age = 0.6
        elif age <= 34: mult_age = 0.25
        else: mult_age = 0.05

        market_value = int(base_val * mult_league * mult_pos * mult_age)
        market_value = max(10000, market_value)
        market_value = round(market_value / 10000) * 10000

        # --- 2. РАСЧЕТ ЗАРПЛАТЫ (в тыс. $) ---
        # База от рейтинга
        base_wage_k = ((max(60, ovr) - 50) ** 3) * 2
        random.seed(p.id)
        wage_variance = random.uniform(0.85, 1.15)
        
        # Вратари получают меньше
        wage_pos_mult = 0.7 if "Goalkeeper" in pos else 1.0
        
        # Считаем ЗП в тысячах (например, 150 = 150 тыс. $)
        wage_k = int(base_wage_k * mult_league * wage_variance * wage_pos_mult)
        wage = max(1, wage_k) * 1000 # Сохраняем в базу как 150000
        wage = round(wage / 500) * 500

        # --- 3. РАСЧЕТ КОНТРАКТА ---
        if age <= 20: years_left = random.randint(4, 5)
        elif age <= 23: years_left = random.randint(3, 4)
        elif age <= 27: years_left = random.randint(2, 4)
        elif age <= 30: years_left = random.randint(2, 3)
        else: years_left = random.randint(1, 2)
            
        end_year = current_year + years_left
        contract_until = f"{end_year}-06-30"

        p.market_value = market_value
        p.wage = wage
        p.contract_until = contract_until
        updated += 1

    db.commit()
    db.close()
    print(f"✅ УСПЕХ! Обновлено {updated} игроков.")

if __name__ == "__main__":
    generate_finances()