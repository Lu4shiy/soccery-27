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

def get_league_multiplier(league_name):
    """Коэффициент престижа лиги"""
    if not league_name: return 0.15
    l = league_name.lower()
    if "premier league" in l or "laliga" in l or "la liga" in l:
        return 1.5   # АПЛ и ЛаЛига (самые богатые)
    elif "bundesliga" in l or "serie a" in l or "ligue 1" in l:
        return 1.1   # Топ-5
    elif "championship" in l or "eredivisie" in l or "portugal" in l or "mls" in l or "saudi" in l:
        return 0.7   # Средние лиги
    else:
        return 0.15  # Остальные (Индия, Австралия и т.д.)

def generate_finances():
    db = Session(engine)
    # Загружаем игроков вместе с информацией об их лиге
    players_with_clubs = db.query(Player, Club).join(Club, Player.club_id == Club.id).all()
    print(f"📊 Найдено {len(players_with_clubs)} игроков. Генерируем реалистичные финансы...")

    current_year = 2026
    updated = 0

    for p, club in players_with_clubs:
        ovr = p.overall_rating or 50
        age = p.age or 25
        pos = p.position or ""
        
        # 1. РАСЧЕТ СТОИМОСТИ (Market Value)
        # Экспоненциальная кривая: 59 OVR ~ 20к, 75 OVR ~ 3.5млн, 91 OVR ~ 90млн
        base_value = 2000 * (1.3 ** (ovr - 50))
        
        # Коэффициент лиги
        league_mult = get_league_multiplier(club.league)

        # Коэффициент позиции
        if "Goalkeeper" in pos:
            pos_mult = 0.4
        elif "Back" in pos:
            pos_mult = 0.8
        elif "Midfield" in pos:
            pos_mult = 1.0
        else:
            pos_mult = 1.2 # Нападающие

        # Возрастной коэффициент
        if age <= 20:
            age_mult = 1.5
        elif age <= 23:
            age_mult = 1.2
        elif age <= 27:
            age_mult = 1.0
        elif age <= 30:
            age_mult = 0.6
        elif age <= 33:
            age_mult = 0.3
        else:
            age_mult = 0.1

        market_value = int(base_value * league_mult * pos_mult * age_mult)
        
        # Ограничения (минимум 10к, максимум 250кк)
        if market_value < 10000: market_value = 10000
        if market_value > 250000000: market_value = 250000000
        # Округляем до 10 тысяч
        market_value = round(market_value / 10000) * 10000

        # 2. РАСЧЕТ ЗАРПЛАТЫ (Wage в неделю, в долларах)
        # База от рейтинга в кубе
        random.seed(p.id) # Стабильный рандом
        base_wage = ((ovr - 40) ** 3) * 1.5
        wage = int(base_wage * random.uniform(0.8, 1.2))
        
        # Минималка 1000$, округляем до 500
        wage = max(1000, wage)
        wage = round(wage / 500) * 500

        # 3. РАСЧЕТ КОНТРАКТА
        if age <= 20:
            years_left = random.randint(4, 5)
        elif age <= 23:
            years_left = random.randint(3, 4)
        elif age <= 27:
            years_left = random.randint(2, 4)
        elif age <= 30:
            years_left = random.randint(2, 3)
        else:
            years_left = random.randint(1, 2)
            
        end_year = current_year + years_left
        contract_until = f"{end_year}-06-30"

        # Обновляем данные
        p.market_value = market_value
        p.wage = wage
        p.contract_until = contract_until
        updated += 1

    db.commit()
    db.close()
    print(f"✅ УСПЕХ! Обновлено {updated} игроков.")

if __name__ == "__main__":
    generate_finances()