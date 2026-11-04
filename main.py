import os
from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Подключаемся к базе данных
# Берем ссылку, которую вы сохранили на Neon, из настроек Render (Environment Variables)
DATABASE_URL = os.environ.get("DATABASE_URL")

# Небольшая хитрость: Neon иногда выдает ссылку, начинающуюся с postgres://, 
# а SQLAlchemy требует postgresql://. Эта строчка исправляет это на лету.
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Создаем движок базы данных
engine = create_engine(DATABASE_URL)

# Создаем базовый класс для наших таблиц
Base = declarative_base()

# 2. Описываем наши первые таблицы (Модели)
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
    club_id = Column(Integer, ForeignKey("clubs.id")) # Привязка игрока к клубу

# 3. Создаем таблицы в базе данных (если их еще нет)
Base.metadata.create_all(bind=engine)

# 4. Запускаем сам сервер
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Soccery 27: База данных подключена и таблицы созданы!"}