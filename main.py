import os
import json
import secrets
import subprocess
import sys
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, List

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy import (
    create_engine, Column, Integer, String, ForeignKey, DateTime, func, Float
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
    stars = Column(Float, default=3.0)


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

    market_value = Column(Integer, default=0)
    wage = Column(Integer, default=0)
    contract_until = Column(String, nullable=True)

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

    # === НОВЫЕ ПОЛЯ ===
    alt_positions = Column(String, default="[]")  # JSON-список альтернативных позиций
    training_program_id = Column(Integer, ForeignKey("training_programs.id"), nullable=True)
    training_started_at = Column(DateTime, nullable=True)


class Manager(Base):
    __tablename__ = "managers"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    first_name = Column(String)
    club_id = Column(Integer, ForeignKey("clubs.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    coach_name = Column(String, nullable=True)
    coach_nationality = Column(String, nullable=True)
    coach_age = Column(Integer, nullable=True)
    negotiation_difficulty = Column(String, nullable=True)
    extra_budget = Column(Integer, nullable=True)
    is_setup_complete = Column(Integer, default=0)


class Tactic(Base):
    __tablename__ = "tactics"
    id = Column(Integer, primary_key=True, index=True)
    manager_id = Column(Integer, ForeignKey("managers.id"), index=True, unique=True)
    formation = Column(String, default="4-3-3 (Линия)")
    starting_xi = Column(String, default="[]")
    captain_id = Column(Integer, nullable=True)
    free_kick_taker_id = Column(Integer, nullable=True)
    corner_taker_id = Column(Integer, nullable=True)
    penalty_taker_id = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TrainingProgram(Base):
    __tablename__ = "training_programs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    duration_weeks = Column(Integer)
    position_focus = Column(String, nullable=True)  # если задано — открывает эту позицию
    stat_boosts = Column(String, default="{}")  # JSON: {stat: +value}
    ovr_boost = Column(Integer, default=0)


Base.metadata.create_all(bind=engine)

# === Инициализация программ тренировок (один раз) ===
def seed_training_programs():
    db = Session(engine)
    try:
        if db.query(TrainingProgram).count() == 0:
            programs = [
                # Быстрые (недели)
                TrainingProgram(name="Скоростная работа", description="Спринты и ускорения. +2 к скорости.",
                                duration_weeks=2, stat_boosts=json.dumps({"pace": 2})),
                TrainingProgram(name="Ударная техника", description="Отработка ударов. +2 к удару.",
                                duration_weeks=3, stat_boosts=json.dumps({"shooting": 2})),
                TrainingProgram(name="Пас в движении", description="Быстрые комбинации. +2 к пасу.",
                                duration_weeks=3, stat_boosts=json.dumps({"passing": 2})),
                TrainingProgram(name="Дриблинг 1-в-1", description="Обводка и контроль мяча. +2 к дриблингу.",
                                duration_weeks=4, stat_boosts=json.dumps({"dribbling": 2})),
                TrainingProgram(name="Оборонительная стойка", description="Отбор и позиционная игра. +2 к защите.",
                                duration_weeks=4, stat_boosts=json.dumps({"defending": 2})),
                TrainingProgram(name="Физическая мощь", description="Работа в зале. +2 к физике.",
                                duration_weeks=4, stat_boosts=json.dumps({"physicality": 2})),
                # Средние (месяцы)
                TrainingProgram(name="Комплексная работа", description="Всестороннее развитие. +3 к OVR.",
                                duration_weeks=12, ovr_boost=3, stat_boosts=json.dumps({"pace": 1, "shooting": 1, "passing": 1, "dribbling": 1, "defending": 1, "physicality": 1})),
                TrainingProgram(name="Освоение новой позиции (лёгкая)", description="Открывает смежную позицию.",
                                duration_weeks=16, position_focus="adjacent"),
                TrainingProgram(name="Освоение новой позиции (сложная)", description="Открывает дальнюю позицию.",
                                duration_weeks=32, position_focus="far"),
                # Долгие (год+)
                TrainingProgram(name="Фундаментальная переподготовка", description="Смена амплуа. Открывает любую позицию.",
                                duration_weeks=80, position_focus="any"),
                TrainingProgram(name="Воспитание лидера", description="Капитанские качества. +5 к OVR, +2 пас, +2 физика.",
                                duration_weeks=52, ovr_boost=5, stat_boosts=json.dumps({"passing": 2, "physicality": 2})),
            ]
            for p in programs:
                db.add(p)
            db.commit()
    finally:
        db.close()

seed_training_programs()


# === Штрафы за позицию ===
# Ключ: (родная_позиция_группа, целевая_позиция) -> штраф
# Используем упрощённую матрицу на основе групп и конкретных позиций.
POSITION_GROUPS = {
    "GK": ["GK"],
    "DEF": ["CB", "LB", "RB", "LWB", "RWB"],
    "MID": ["CDM", "CM", "CAM", "LM", "RM"],
    "ATT": ["LW", "RW", "ST", "CF"],
}

# Точные штрафы для конкретных пар (родная -> целевая)
# Если пары нет, используется штраф по группам.
POSITION_PENALTY = {
    # CM
    ("CM", "CDM"): 4,
    ("CM", "CAM"): 4,
    ("CM", "LM"): 6,
    ("CM", "RM"): 6,
    ("CM", "CB"): 10,
    ("CM", "LB"): 11,
    ("CM", "RB"): 11,
    ("CM", "ST"): 8,
    ("CM", "LW"): 9,
    ("CM", "RW"): 9,
    ("CM", "GK"): 45,
    # CDM
    ("CDM", "CM"): 3,
    ("CDM", "CAM"): 6,
    ("CDM", "CB"): 7,
    ("CDM", "LB"): 8,
    ("CDM", "RB"): 8,
    ("CDM", "LM"): 8,
    ("CDM", "RM"): 8,
    ("CDM", "ST"): 12,
    ("CDM", "GK"): 45,
    # CAM
    ("CAM", "CM"): 3,
    ("CAM", "CDM"): 6,
    ("CAM", "ST"): 5,
    ("CAM", "LW"): 6,
    ("CAM", "RW"): 6,
    ("CAM", "LM"): 7,
    ("CAM", "RM"): 7,
    ("CAM", "CB"): 15,
    ("CAM", "GK"): 45,
    # ST
    ("ST", "CF"): 1,
    ("ST", "CAM"): 7,
    ("ST", "LW"): 5,
    ("ST", "RW"): 5,
    ("ST", "CM"): 10,
    ("ST", "CDM"): 14,
    ("ST", "CB"): 18,
    ("ST", "GK"): 48,
    # LW
    ("LW", "LM"): 3,
    ("LW", "RW"): 2,
    ("LW", "ST"): 5,
    ("LW", "CAM"): 6,
    ("LW", "CM"): 9,
    ("LW", "LB"): 7,
    ("LW", "RB"): 12,
    ("LW", "CB"): 15,
    ("LW", "GK"): 47,
    # RW (симметрично LW)
    ("RW", "RM"): 3,
    ("RW", "LW"): 2,
    ("RW", "ST"): 5,
    ("RW", "CAM"): 6,
    ("RW", "CM"): 9,
    ("RW", "RB"): 7,
    ("RW", "LB"): 12,
    ("RW", "CB"): 15,
    ("RW", "GK"): 47,
    # CB
    ("CB", "CDM"): 7,
    ("CB", "LB"): 4,
    ("CB", "RB"): 4,
    ("CB", "CM"): 12,
    ("CB", "CAM"): 16,
    ("CB", "ST"): 20,
    ("CB", "GK"): 40,
    # LB
    ("LB", "LWB"): 2,
    ("LB", "CB"): 4,
    ("LB", "RB"): 5,
    ("LB", "LM"): 4,
    ("LB", "CM"): 11,
    ("LB", "CDM"): 9,
    ("LB", "CAM"): 15,
    ("LB", "ST"): 20,
    ("LB", "GK"): 45,
    # RB (симметрично LB)
    ("RB", "RWB"): 2,
    ("RB", "CB"): 4,
    ("RB", "LB"): 5,
    ("RB", "RM"): 4,
    ("RB", "CM"): 11,
    ("RB", "CDM"): 9,
    ("RB", "CAM"): 15,
    ("RB", "ST"): 20,
    ("RB", "GK"): 45,
    # GK
    ("GK", "CB"): 40,
    ("GK", "CM"): 45,
    ("GK", "ST"): 48,
    # LWB/RWB (аналогично LB/RB)
    ("LWB", "LB"): 2,
    ("LWB", "LM"): 3,
    ("LWB", "CB"): 5,
    ("RWB", "RB"): 2,
    ("RWB", "RM"): 3,
    ("RWB", "CB"): 5,
    # LM
    ("LM", "LW"): 3,
    ("LM", "CM"): 5,
    ("LM", "CAM"): 6,
    ("LM", "LB"): 4,
    ("LM", "CDM"): 9,
    ("LM", "ST"): 9,
    ("LM", "CB"): 14,
    ("LM", "GK"): 45,
    # RM (симметрично LM)
    ("RM", "RW"): 3,
    ("RM", "CM"): 5,
    ("RM", "CAM"): 6,
    ("RM", "RB"): 4,
    ("RM", "CDM"): 9,
    ("RM", "ST"): 9,
    ("RM", "CB"): 14,
    ("RM", "GK"): 45,
}

# Штрафы по группам (если точной пары нет)
GROUP_PENALTY = {
    ("MID", "MID"): 5,
    ("MID", "DEF"): 12,
    ("MID", "ATT"): 9,
    ("MID", "GK"): 45,
    ("DEF", "MID"): 11,
    ("DEF", "DEF"): 4,
    ("DEF", "ATT"): 18,
    ("DEF", "GK"): 42,
    ("ATT", "MID"): 8,
    ("ATT", "DEF"): 16,
    ("ATT", "ATT"): 3,
    ("ATT", "GK"): 47,
    ("GK", "DEF"): 40,
    ("GK", "MID"): 45,
    ("GK", "ATT"): 48,
}


def normalize_pos(pos: str) -> str:
    if not pos:
        return "CM"
    p = pos.upper()
    mapping = {
        "GOALKEEPER": "GK", "GK": "GK",
        "LEFT BACK": "LB", "LB": "LB", "LWB": "LWB", "LEFT WING BACK": "LWB",
        "RIGHT BACK": "RB", "RB": "RB", "RWB": "RWB", "RIGHT WING BACK": "RWB",
        "CENTRE-BACK": "CB", "CENTER-BACK": "CB", "CB": "CB",
        "CENTRAL DEFENSIVE MIDFIELD": "CDM", "CDM": "CDM",
        "CENTRAL MIDFIELD": "CM", "CM": "CM",
        "CENTRAL ATTACKING MIDFIELD": "CAM", "CAM": "CAM",
        "LEFT MIDFIELD": "LM", "LM": "LM",
        "RIGHT MIDFIELD": "RM", "RM": "RM",
        "LEFT WING": "LW", "LW": "LW",
        "RIGHT WING": "RW", "RW": "RW",
        "STRIKER": "ST", "ST": "ST", "CENTRE-FORWARD": "CF", "CF": "CF",
    }
    for k, v in mapping.items():
        if k in p:
            return v
    return "CM"


def group_of(pos: str) -> str:
    for g, positions in POSITION_GROUPS.items():
        if pos in positions:
            return g
    return "MID"


def position_penalty(native_pos: str, target_pos: str, alt_positions: list) -> int:
    """Возвращает штраф к OVR (0, если позиция родная или альтернативная)."""
    native = normalize_pos(native_pos)
    target = normalize_pos(target_pos)
    if native == target:
        return 0
    # Если позиция есть в альтернативных — штрафа нет
    alts = [normalize_pos(a) for a in alt_positions]
    if target in alts:
        return 0
    # Точный штраф
    key = (native, target)
    if key in POSITION_PENALTY:
        return POSITION_PENALTY[key]
    # Штраф по группам
    ng = group_of(native)
    tg = group_of(target)
    return GROUP_PENALTY.get((ng, tg), 20)


# === Эффективный OVR ===
def effective_overall(player: Player, slot_pos: str) -> int:
    alts = json.loads(player.alt_positions or "[]")
    pen = position_penalty(player.position, slot_pos, alts)
    return max(1, player.overall_rating - pen)


# === Применение завершённой тренировки ===
def apply_training_if_done(player: Player, db: Session) -> bool:
    if not player.training_program_id or not player.training_started_at:
        return False
    prog = db.query(TrainingProgram).filter_by(id=player.training_program_id).first()
    if not prog:
        return False
    end_date = player.training_started_at + timedelta(weeks=prog.duration_weeks)
    if datetime.utcnow() < end_date:
        return False
    # Применяем эффекты
    if prog.stat_boosts:
        boosts = json.loads(prog.stat_boosts)
        for stat, val in boosts.items():
            if hasattr(player, stat):
                setattr(player, stat, (getattr(player, stat) or 0) + val)
    if prog.ovr_boost:
        player.overall_rating = (player.overall_rating or 50) + prog.ovr_boost
    if prog.position_focus:
        # Логика добавления альтернативной позиции
        alts = json.loads(player.alt_positions or "[]")
        native = normalize_pos(player.position)
        if prog.position_focus == "any":
            # Открываем случайную дальнюю позицию
            all_pos = ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LM", "RM", "LW", "RW", "ST"]
            candidates = [p for p in all_pos if p != native and p not in alts]
            if candidates:
                alts.append(random.choice(candidates))
        elif prog.position_focus == "far":
            # Открываем позицию из другой группы
            ng = group_of(native)
            candidates = [p for p in ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LM", "RM", "LW", "RW", "ST"]
                          if p != native and p not in alts and group_of(p) != ng]
            if candidates:
                alts.append(random.choice(candidates))
        else:  # adjacent
            # Смежная позиция
            adjacent_map = {
                "CM": ["CDM", "CAM", "LM", "RM"],
                "CDM": ["CM", "CB"],
                "CAM": ["CM", "ST", "LW", "RW"],
                "ST": ["CF", "CAM", "LW", "RW"],
                "LW": ["LM", "ST", "RW"],
                "RW": ["RM", "ST", "LW"],
                "CB": ["CDM", "LB", "RB"],
                "LB": ["LWB", "CB", "LM"],
                "RB": ["RWB", "CB", "RM"],
                "LM": ["LW", "CM", "LB"],
                "RM": ["RW", "CM", "RB"],
                "GK": [],
            }
            candidates = [p for p in adjacent_map.get(native, []) if p not in alts]
            if candidates:
                alts.append(random.choice(candidates))
        player.alt_positions = json.dumps(alts)
    # Очищаем тренировку
    player.training_program_id = None
    player.training_started_at = None
    db.commit()
    return True


app = FastAPI()
security = HTTPBasic()


def run_seed_script():
    result = subprocess.run([sys.executable, "seed_data.py"], capture_output=True, text=True)
    print("Вывод (stdout):", result.stdout)


@app.get("/")
def read_root():
    return {"message": "Soccery 27 API"}


@app.post("/admin/seed")
def trigger_seed(background_tasks: BackgroundTasks, credentials: HTTPBasicCredentials = Depends(security)):
    if not (secrets.compare_digest(credentials.username, "admin") and secrets.compare_digest(credentials.password, "soccery_secret_2026")):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    background_tasks.add_task(run_seed_script)
    return {"message": "Загрузка данных запущена."}


@app.get("/api/clubs")
def get_clubs():
    db = Session(engine)
    try:
        rows = (
            db.query(
                Club.id, Club.name, Club.league, Club.stars,
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
                "id": r.id, "name": r.name, "league": r.league, "stars": r.stars or 3.0,
                "players": int(r.players or 0), "avg_ovr": round(float(r.avg_ovr), 1) if r.avg_ovr else 0,
            }
            for r in rows
        ]
    finally:
        db.close()


@app.get("/api/manager/{telegram_id}")
def get_manager(telegram_id: str):
    db = Session(engine)
    try:
        m = db.query(Manager).filter_by(telegram_id=telegram_id).first()
        if not m: return {"has_club": False}
        club = db.query(Club).filter_by(id=m.club_id).first()
        if not club: return {"has_club": False}
        return {
            "has_club": True, "club_id": club.id, "club_name": club.name,
            "league": club.league, "stars": club.stars or 3.0,
            "is_setup_complete": bool(m.is_setup_complete)
        }
    finally:
        db.close()


class SelectClubRequest(BaseModel):
    telegram_id: str
    first_name: Optional[str] = None
    club_id: int


@app.post("/api/select-club")
def select_club(req: SelectClubRequest):
    db = Session(engine)
    try:
        club = db.query(Club).filter_by(id=req.club_id).first()
        if not club: raise HTTPException(status_code=404, detail="Клуб не найден")
        taken = db.query(Manager).filter(Manager.club_id == req.club_id, Manager.telegram_id != req.telegram_id).first()
        if taken: raise HTTPException(status_code=409, detail="Клуб занят")
        existing = db.query(Manager).filter_by(telegram_id=req.telegram_id).first()
        if existing:
            existing.club_id = req.club_id
            existing.first_name = req.first_name or existing.first_name
            existing.is_setup_complete = 0
        else:
            db.add(Manager(telegram_id=req.telegram_id, first_name=req.first_name or "", club_id=req.club_id, is_setup_complete=0))
        db.commit()
        return {"status": "ok", "club_name": club.name, "league": club.league}
    finally:
        db.close()


class SaveSettingsRequest(BaseModel):
    telegram_id: str
    coach_name: str
    coach_nationality: str
    coach_age: int
    negotiation_difficulty: str
    extra_budget: int


@app.post("/api/save-settings")
def save_settings(req: SaveSettingsRequest):
    db = Session(engine)
    try:
        m = db.query(Manager).filter_by(telegram_id=req.telegram_id).first()
        if not m: raise HTTPException(status_code=404, detail="Менеджер не найден")
        m.coach_name = req.coach_name
        m.coach_nationality = req.coach_nationality
        m.coach_age = req.coach_age
        m.negotiation_difficulty = req.negotiation_difficulty
        m.extra_budget = req.extra_budget
        m.is_setup_complete = 1
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()


@app.delete("/api/reset-club/{telegram_id}")
def reset_club(telegram_id: str):
    db = Session(engine)
    try:
        manager = db.query(Manager).filter_by(telegram_id=telegram_id).first()
        if manager:
            db.query(Tactic).filter_by(manager_id=manager.id).delete()
            db.delete(manager)
            db.commit()
        return {"status": "ok"}
    finally:
        db.close()


@app.get("/api/clubs/{club_id}/players")
def get_club_players(club_id: int):
    db = Session(engine)
    try:
        players = db.query(Player).filter(Player.club_id == club_id).order_by(Player.overall_rating.desc()).all()
        result = []
        for p in players:
            # Применяем тренировки, если завершились
            apply_training_if_done(p, db)
            alts = json.loads(p.alt_positions or "[]")
            result.append({
                "id": p.id, "name": p.name, "position": p.position, "age": p.age,
                "overall": p.overall_rating, "nationality": p.nationality,
                "market_value": p.market_value or 0,
                "wage": p.wage or 0,
                "contract_until": p.contract_until,
                "alt_positions": alts,
                "pace": p.pace or 50, "shooting": p.shooting or 50, "passing": p.passing or 50,
                "dribbling": p.dribbling or 50, "defending": p.defending or 50, "physicality": p.physicality or 50,
                "gk_diving": p.gk_diving or 10, "gk_handling": p.gk_handling or 10,
                "gk_kicking": p.gk_kicking or 10, "gk_positioning": p.gk_positioning or 10,
                "gk_reflexes": p.gk_reflexes or 10
            })
        return result
    finally:
        db.close()


# === ТРЕНИРОВКИ ===

@app.get("/api/training-programs")
def get_training_programs():
    db = Session(engine)
    try:
        programs = db.query(TrainingProgram).all()
        return [
            {
                "id": p.id, "name": p.name, "description": p.description,
                "duration_weeks": p.duration_weeks,
                "position_focus": p.position_focus,
                "stat_boosts": json.loads(p.stat_boosts or "{}"),
                "ovr_boost": p.ovr_boost,
            }
            for p in programs
        ]
    finally:
        db.close()


class StartTrainingRequest(BaseModel):
    player_id: int
    program_id: int


@app.post("/api/player/start-training")
def start_training(req: StartTrainingRequest):
    db = Session(engine)
    try:
        player = db.query(Player).filter_by(id=req.player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Игрок не найден")
        if player.training_program_id:
            raise HTTPException(status_code=400, detail="Игрок уже на тренировке")
        prog = db.query(TrainingProgram).filter_by(id=req.program_id).first()
        if not prog:
            raise HTTPException(status_code=404, detail="Программа не найдена")
        player.training_program_id = prog.id
        player.training_started_at = datetime.utcnow()
        db.commit()
        end_date = player.training_started_at + timedelta(weeks=prog.duration_weeks)
        return {
            "status": "ok",
            "program_name": prog.name,
            "end_date": end_date.isoformat(),
        }
    finally:
        db.close()


@app.get("/api/player/{player_id}/training-status")
def training_status(player_id: int):
    db = Session(engine)
    try:
        player = db.query(Player).filter_by(id=player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Игрок не найден")
        # Проверяем завершение
        apply_training_if_done(player, db)
        if not player.training_program_id:
            return {"active": False}
        prog = db.query(TrainingProgram).filter_by(id=player.training_program_id).first()
        if not prog:
            return {"active": False}
        end_date = player.training_started_at + timedelta(weeks=prog.duration_weeks)
        weeks_left = max(0, (end_date - datetime.utcnow()).days // 7)
        return {
            "active": True,
            "program_name": prog.name,
            "weeks_left": weeks_left,
            "end_date": end_date.isoformat(),
        }
    finally:
        db.close()


# === ТАКТИКА ===

@app.get("/api/tactics/{telegram_id}")
def get_tactics(telegram_id: str):
    db = Session(engine)
    try:
        m = db.query(Manager).filter_by(telegram_id=telegram_id).first()
        if not m:
            raise HTTPException(status_code=404, detail="Менеджер не найден")
        t = db.query(Tactic).filter_by(manager_id=m.id).first()
        if not t:
            return {
                "formation": "4-3-3 (Линия)",
                "starting_xi": [],
                "captain_id": None,
                "free_kick_taker_id": None,
                "corner_taker_id": None,
                "penalty_taker_id": None,
            }
        try:
            xi = json.loads(t.starting_xi or "[]")
        except Exception:
            xi = []
        return {
            "formation": t.formation or "4-3-3 (Линия)",
            "starting_xi": xi,
            "captain_id": t.captain_id,
            "free_kick_taker_id": t.free_kick_taker_id,
            "corner_taker_id": t.corner_taker_id,
            "penalty_taker_id": t.penalty_taker_id,
        }
    finally:
        db.close()


class SaveTacticsRequest(BaseModel):
    telegram_id: str
    formation: str
    starting_xi: List[Optional[int]]
    captain_id: Optional[int] = None
    free_kick_taker_id: Optional[int] = None
    corner_taker_id: Optional[int] = None
    penalty_taker_id: Optional[int] = None


@app.post("/api/tactics")
def save_tactics(req: SaveTacticsRequest):
    db = Session(engine)
    try:
        m = db.query(Manager).filter_by(telegram_id=req.telegram_id).first()
        if not m:
            raise HTTPException(status_code=404, detail="Менеджер не найден")
        t = db.query(Tactic).filter_by(manager_id=m.id).first()
        if not t:
            t = Tactic(manager_id=m.id)
            db.add(t)
        t.formation = req.formation
        t.starting_xi = json.dumps(req.starting_xi)
        t.captain_id = req.captain_id
        t.free_kick_taker_id = req.free_kick_taker_id
        t.corner_taker_id = req.corner_taker_id
        t.penalty_taker_id = req.penalty_taker_id
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()


# --- TELEGRAM БОТ ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    web_app = types.WebAppInfo(url="https://soccery-27.onrender.com/app")
    keyboard = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="⚽️ Открыть Soccery 27", web_app=web_app)]], resize_keyboard=True)
    await message.answer("Добро пожаловать в Soccery 27!", reply_markup=keyboard)


async def start_bot():
    await dp.start_polling(bot)


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())


# --- РАЗДАЧА ---
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/app")
def read_index():
    return FileResponse("static/index.html")