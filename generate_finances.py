import random
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, Session

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
    position = Column(String)
    overall_rating = Column(Integer)
    age = Column(Integer)
    market_value = Column(Integer)
    wage = Column(Integer)
    contract_until = Column(String)

def generate_finances():
    db = Session(engine)
    players = db.query(Player).all()
    print(f"📊 Найдено {len(players)} игроков. Генерируем реалистичные финансы...")

    current_year = 2026
    updated = 0

    for p in players:
        ovr = p.overall_rating or 50
        age = p.age or 25
        pos = p.position or ""

        # 1. РАСЧЕТ СТОИМОСТИ (Market Value)
        # Степень 4 делает топов нереально дорогими (OVR 91 = ~130млн базы)
        base_value = ((ovr - 40) ** 4) * 20 
        
        # Коэффициент позиции
        if "Goalkeeper" in pos:
            pos_mult = 0.4  # Вратари дешевле
        elif "Back" in pos:
            pos_mult = 0.8  # Защитники
        elif "Midfield" in pos:
            pos_mult = 1.0  # Полузащита
        else:
            pos_mult = 1.25 # Нападающие и Вингеры (самые дорогие)

        # Возрастной коэффициент
        if age <= 20:
            age_mult = 1.6   # Огромный потенциал (молодые дороже)
        elif age <= 23:
            age_mult = 1.3   
        elif age <= 27:
            age_mult = 1.0   # Пик
        elif age <= 30:
            age_mult = 0.6   # Начало спада
        elif age <= 33:
            age_mult = 0.3   
        else:
            age_mult = 0.1   # Ветераны

        market_value = int(base_value * age_mult * pos_mult)
        
        # Минимальная цена 50к, чтобы не было нулей
        if market_value < 50000: market_value = 50000
        # Округляем до 100 тысяч
        market_value = round(market_value / 100000) * 100000

        # 2. РАСЧЕТ ЗАРПЛАТЫ (Wage в неделю, в долларах)
        # Берем рейтинг в степени 3.5 и делим на 30
        random.seed(p.id) # Чтобы разброс был стабильным при перезапуске
        base_wage = (ovr ** 3.5) / 30
        # Добавляем разброс от 0.85 до 1.15 (чтобы у игроков с одинаковым рейтингом была разная ЗП)
        wage = int(base_wage * random.uniform(0.85, 1.15))
        
        # Минималка 2к в неделю
        wage = max(2000, wage)
        # Округляем до 1000
        wage = round(wage / 1000) * 1000

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