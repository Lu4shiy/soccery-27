import os
import secrets
import subprocess
import sys
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL)
Base = declarative_base()

class Club(Base):
    __tablename__ = "clubs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    league = Column(String, index=True)

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, unique=True)
    name = Column(String, index=True)
    position = Column(String)
    overall_rating = Column(Integer)
    
    # Новые поля, которые вы просили
    age = Column(Integer)
    nationality = Column(String)
    club_id = Column(Integer, ForeignKey("clubs.id"))
    preferred_foot = Column(String)
    
    # Характеристики (для полевых)
    pace = Column(Integer)
    shooting = Column(Integer)
    passing = Column(Integer)
    dribbling = Column(Integer)
    defending = Column(Integer)
    physicality = Column(Integer)
    
    # Характеристики (для вратарей)
    gk_diving = Column(Integer)
    gk_handling = Column(Integer)
    gk_kicking = Column(Integer)
    gk_positioning = Column(Integer)
    gk_reflexes = Column(Integer)

Base.metadata.create_all(bind=engine)

app = FastAPI()
security = HTTPBasic()

def run_seed_script():
    print("Запуск скрипта seed_data.py в фоне...")
    # Запускаем через sys.executable, чтобы использовался питон из виртуального окружения
    result = subprocess.run([sys.executable, "seed_data.py"], capture_output=True, text=True)
    print("Скрипт завершён.")
    print("Вывод (stdout):", result.stdout)
    if result.stderr:
        print("Ошибки (stderr):", result.stderr)

@app.get("/")
def read_root():
    return {"message": "Soccery 27: База данных готова к загрузке!"}

@app.post("/admin/seed")
def trigger_seed(background_tasks: BackgroundTasks, credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "soccery_secret_2026")
    
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    background_tasks.add_task(run_seed_script)
    return {"message": "Загрузка данных из FC27 запущена. Проверьте логи."}