import os
import secrets
import subprocess
import sys
import asyncio
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy import (
    create_engine, Column, Integer, String, ForeignKey, DateTime, func
)
from sqlalchemy.orm import declarative_base, Session

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

    age = Column(Integer)
    nationality = Column(String)
    club_id = Column(Integer, ForeignKey("clubs.id"))
    preferred_foot = Column(String)

    pace = Column(Integer)
    shooting = Column(Integer)
    passing = Column(Integer)
    dribbling = Column(Integer)
    defending = Column(Integer)
    physicality = Column(Integer)

    gk_diving = Column(Integer)
    gk_handling = Column(Integer)
    gk_kicking = Column(Integer)
    gk_positioning = Column(Integer)
    gk_reflexes = Column(Integer)


# НОВОЕ: таблица менеджеров (кто какой клуб взял)
class Manager(Base):
    __tablename__ = "managers"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    first_name = Column(String)
    club_id = Column(Integer, ForeignKey("clubs.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

app = FastAPI()
security = HTTPBasic()


def run_seed_script():
    print("Запуск скрипта seed_data.py в фоне...")
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


# ============ НОВЫЕ API ДЛЯ ФРОНТЕНДА ============

@app.get("/api/clubs")
def get_clubs():
    """Возвращает все клубы + количество игроков и средний рейтинг."""
    db = Session(engine)
    try:
        rows = (
            db.query(
                Club.id, Club.name, Club.league,
                func.count(Player.id).label("players"),
                func.avg(Player.overall_rating).label("avg_ovr"),
            )
            .outerjoin(Player, Player.club_id == Club.id)
            .group_by(Club.id)
            .order_by(Club.league, Club.name)
            .all()
        )
        return [
            {
                "id": r.id,
                "name": r.name,
                "league": r.league,
                "players": int(r.players or 0),
                "avg_ovr": round(float(r.avg_ovr), 1) if r.avg_ovr else 0,
            }
            for r in rows
        ]
    finally:
        db.close()


@app.get("/api/manager/{telegram_id}")
def get_manager(telegram_id: str):
    """Есть ли у пользователя уже выбранный клуб."""
    db = Session(engine)
    try:
        m = db.query(Manager).filter_by(telegram_id=telegram_id).first()
        if not m:
            return {"has_club": False}
        club = db.query(Club).filter_by(id=m.club_id).first()
        if not club:
            return {"has_club": False}
        return {
            "has_club": True,
            "club_id": club.id,
            "club_name": club.name,
            "league": club.league,
        }
    finally:
        db.close()


class SelectClubRequest(BaseModel):
    telegram_id: str
    first_name: Optional[str] = None
    club_id: int


@app.post("/api/select-club")
def select_club(req: SelectClubRequest):
    """Сохраняет выбор клуба за менеджером."""
    db = Session(engine)
    try:
        club = db.query(Club).filter_by(id=req.club_id).first()
        if not club:
            raise HTTPException(status_code=404, detail="Клуб не найден")

        taken = db.query(Manager).filter(
            Manager.club_id == req.club_id,
            Manager.telegram_id != req.telegram_id,
        ).first()
        if taken:
            raise HTTPException(status_code=409, detail="Этот клуб уже занят другим менеджером")

        existing = db.query(Manager).filter_by(telegram_id=req.telegram_id).first()
        if existing:
            existing.club_id = req.club_id
            existing.first_name = req.first_name or existing.first_name
        else:
            db.add(Manager(
                telegram_id=req.telegram_id,
                first_name=req.first_name or "",
                club_id=req.club_id,
            ))
        db.commit()
        return {"status": "ok", "club_name": club.name, "league": club.league}
    finally:
        db.close()


# ============ TELEGRAM БОТ ============

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    web_app = types.WebAppInfo(url="https://soccery-27.onrender.com/app")
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="⚽️ Открыть Soccery 27", web_app=web_app)]],
        resize_keyboard=True,
    )
    await message.answer(
        "Добро пожаловать в Soccery 27! Нажми на кнопку ниже, чтобы начать.",
        reply_markup=keyboard,
    )


async def start_bot():
    await dp.start_polling(bot)


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())


# ============ РАЗДАЧА ФРОНТЕНДА ============

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/app")
def read_index():
    return FileResponse("static/index.html")