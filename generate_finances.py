import random
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, Session
import datetime

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
    overall_rating = Column(Integer)
    age = Column(Integer)
    market_value = Column(Integer)
    wage = Column(Integer)
    contract_until = Column(String)

def generate_finances():
    db = Session(engine)
    players = db.query(Player).all()
    print(f"📊 Найдено {len(players)} игроков. Генерируем финансы...")

    current_year = 2026
    updated = 0

    for p in players:
        ovr = p.overall_rating or 50
        age = p.age or 25

        # 1. РАСЧЕТ СТОИМОСТИ (Market Value)
        # Базовая стоимость от рейтинга (кубическая зависимость)
        # OVR 90 = ~150 млн, OVR 80 = ~50 млн, OVR 70 = ~10 млн, OVR 60 = ~1 млн
        base_value = ((ovr - 40) ** 3) * 60 
        
        # Возрастной коэффициент
        if age <= 20:
            age_mult = 1.8   # Огромный потенциал
        elif age <= 23:
            age_mult = 1.4   # Пик роста стоимости
        elif age <= 27:
            age_mult = 1.0   # Прайм
        elif age <= 30:
            age_mult = 0.6   # Начало спада
        elif age <= 33:
            age_mult = 0.3   # Ветераны
        else:
            age_mult = 0.1   # Завершение карьеры

        market_value = int(base_value * age_mult)
        
        # Минимальная цена 50к, чтобы не было нулей
        if market_value < 50000: market_value = 50000
        # Округляем до 100 тысяч
        market_value = round(market_value / 100000) * 100000

        # 2. РАСЧЕТ ЗАРПЛАТЫ (Wage в неделю)
        # Берем корень от стоимости и добавляем разброс
        random.seed(p.id) # Делаем генерацию стабильной для каждого игрока
        base_wage = (market_value ** 0.5) / 10
        wage = int(base_wage * random.uniform(0.8, 1.2))
        
        # ЗП в тысячах, минималка 1к
        wage = max(1000, wage)
        # Округляем до 500
        wage = round(wage / 500) * 500

        # 3. РАСЧЕТ КОНТРАКТА
        if age <= 23:
            years_left = random.randint(3, 5)
        elif age <= 29:
            years_left = random.randint(2, 4)
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