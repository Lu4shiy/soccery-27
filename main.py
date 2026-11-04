import os
import secrets
import subprocess
import sys
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base

# 1. Подключение к базе данных
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL)
Base = declarative_base()

# 2. Модели базы данных
class Club(Base):
    __tablename__ = "clubs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    league = Column(String)

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    position = Column(String)
    rating = Column(Integer)
    club_id = Column(Integer, ForeignKey("clubs.id"))

Base.metadata.create_all(bind=engine)

# 3. Запуск сервера
app = FastAPI()
security = HTTPBasic()

# Функция для запуска скрипта в фоне
def run_seed_script():
    print("Запуск скрипта seed_data.py в фоне...")
    result = subprocess.run([sys.executable, "seed_data.py"], capture_output=True, text=True)
    print("Скрипт завершён.")
    print("Вывод (stdout):", result.stdout)
    if result.stderr:
        print("Ошибки (stderr):", result.stderr)

# Проверка главной страницы
@app.get("/")
def read_root():
    return {"message": "Soccery 27: База данных подключена и таблицы созданы!"}

# Наш секретный путь для загрузки данных (ОБРАТИТЕ ВНИМАНИЕ НА ОТСТУПЫ: они должны быть ровно такими)
@app.post("/admin/seed")
def trigger_seed(background_tasks: BackgroundTasks, credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "soccery_secret_2026")
    
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    background_tasks.add_task(run_seed_script)
    return {"message": "Загрузка данных запущена в фоновом режиме. Проверьте логи через пару минут."}

# ... (ваш существующий код выше) ...

def run_update_ratings():
    print("Запуск скрипта update_ratings.py в фоне...")
    result = subprocess.run([sys.executable, "update_ratings.py"], capture_output=True, text=True)
    print("Скрипт обновления рейтингов завершён.")
    print("Вывод (stdout):", result.stdout)
    if result.stderr:
        print("Ошибки (stderr):", result.stderr)

@app.post("/admin/update-ratings")
def trigger_update_ratings(background_tasks: BackgroundTasks, credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "soccery_secret_2026")
    
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    background_tasks.add_task(run_update_ratings)
    return {"message": "Обновление рейтингов запущено в фоне. Проверьте логи."}