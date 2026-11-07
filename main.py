import os
import json
import secrets
import subprocess
import sys
import asyncio
import random
import unicodedata
from datetime import datetime, timedelta
from typing import Optional, List

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy import (
    create_engine, Column, Integer, String, ForeignKey, DateTime, func, Float, text
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

# --- МОДЕЛИ ---
class Club(Base):
    __tablename__ = "clubs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    league = Column(String, index=True)
    stars = Column(Float, default=3.0)
    continent = Column(String, default="UEFA")

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
    alt_positions = Column(String, default="[]")
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
    bench = Column(String, default="[]")
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
    position_focus = Column(String, nullable=True)
    stat_boosts = Column(String, default="{}")
    ovr_boost = Column(Integer, default=0)

class Tournament(Base):
    __tablename__ = "tournaments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    continent = Column(String)
    type = Column(String)

class ClubTournament(Base):
    __tablename__ = "club_tournaments"
    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), index=True)
    season = Column(String, default="2026/27")

Base.metadata.create_all(bind=engine)

# === СПИСКИ УЧАСТНИКОВ ЕВРОКУБКОВ 2026/27 ===
UCL_TEAMS = ["Arsenal", "Aston Villa", "Liverpool", "Manchester City", "Manchester United", "Atlético Madrid", "Barcelona", "Real Betis", "Real Madrid", "Villarreal", "Bayern München", "Borussia Dortmund", "RB Leipzig", "VfB Stuttgart", "Inter", "Como", "Napoli", "Roma", "Paris Saint-Germain", "Lens", "Lille", "PSV", "Feyenoord", "Sporting CP", "FC Porto", "Galatasaray", "Fenerbahçe", "AEK Athens", "Club Brugge KV", "Bodø/Glimt", "Viking", "LASK", "Sabah", "Slavia Praha", "Slovan Bratislava", "Shakhtar Donetsk"]
UEL_TEAMS = ["Crystal Palace", "Bournemouth", "Sunderland", "Milan", "Juventus", "Real Sociedad", "Celta de Vigo", "Bayer Leverkusen", "Hoffenheim", "Marseille", "Rennes", "Benfica", "Torreense", "AZ Alkmaar", "Anderlecht", "Union Saint-Gilloise", "Beşiktaş", "Viktoria Plzeň", "Sparta Praha", "Sturm Graz", "Olympiacos", "Ararat-Armenia", "Dinamo Zagreb", "Ludogorets"]
UECL_TEAMS = ["Atalanta", "Braga", "Ajax", "Freiburg", "Monaco", "Copenhagen", "Midtjylland", "Crvena Zvezda", "Gent", "Panathinaikos", "Pafos", "Brighton", "Lugano", "Getafe", "Twente", "KuPS", "Borac Banja Luka", "Sint-Truiden", "Lincoln Red Imps", "Brann", "Hearts", "Kairat", "Trabzonspor", "Universitatea Craiova", "Riga", "Hajduk Split", "Jablonec", "Nordsjælland", "Inter Escaldes", "Aarhus", "Thun", "CSKA Sofia", "Kauno Žalgiris", "Mjällby", "Iberia 1999", "Egnatia"]

# 🔥 ИСПРАВЛЕНИЕ: Единый маппинг кубков для дивизионов одной страны (реальные названия)
COUNTRY_CUPS = {
    # Англия
    "premier league": ["FA Cup", "EFL Cup"],
    "championship": ["FA Cup", "EFL Cup"],
    "efl league one": ["FA Cup", "EFL Cup"],
    "efl league two": ["FA Cup", "EFL Cup"],
    # Испания
    "laliga": ["Copa del Rey"],
    "la liga": ["Copa del Rey"],
    "laliga 2": ["Copa del Rey"],
    # Германия
    "bundesliga": ["DFB-Pokal"],
    "2. bundesliga": ["DFB-Pokal"],
    "3. liga": ["DFB-Pokal"],
    # Италия
    "serie a": ["Coppa Italia"],
    "serie b": ["Coppa Italia"],
    # Франция
    "ligue 1": ["Coupe de France"],
    "ligue 2": ["Coupe de France"],
    # Нидерланды
    "eredivisie": ["KNVB Beker"],
    "eerste divisie": ["KNVB Beker"],
    # Португалия
    "liga portugal": ["Taça de Portugal"],
    "liga portugal 2": ["Taça de Portugal"],
    # Турция
    "süper lig": ["Türkiye Kupası"],
    "tff first league": ["Türkiye Kupası"],
    # Швеция
    "allsvenskan": ["Svenska Cupen"],
    "superettan": ["Svenska Cupen"],
    # Норвегия
    "eliteserien": ["NM-Cup"],
    "obos-ligaen": ["NM-Cup"],
    # Дания
    "superliga": ["Landspokalturneringen"],
    "1. division": ["Landspokalturneringen"],
    # Шотландия
    "scottish premiership": ["Scottish FA Cup", "Scottish League Cup"],
    "scottish championship": ["Scottish FA Cup", "Scottish League Cup"],
    # Бельгия
    "pro league": ["Beker van België"],
    "challenger pro league": ["Beker van België"],
    # Австрия
    "austrian bundesliga": ["ÖFB-Cup"],
    "2. liga": ["ÖFB-Cup"],
    # Швейцария
    "super league": ["Schweizer Cup"],
    "challenge league": ["Schweizer Cup"],
    # Греция
    "super league 1": ["Kipelo Ellados"],
    "super league 2": ["Kipelo Ellados"],
    # Чехия
    "chance liga": ["Pohár FAČR"],
    "fotbalová národní liga": ["Pohár FAČR"],
    # Хорватия
    "supersport hnl": ["Hrvatski nogometni kup"],
    "first nhl": ["Hrvatski nogometni kup"],
    # Сербия
    "mozzart bet super liga": ["Kup Srbije"],
    "prva liga": ["Kup Srbije"],
    # Румыния
    "superliga": ["Cupa României"],
    "liga 2": ["Cupa României"],
    # Польша
    "pko bp ekstraklasa": ["Puchar Polski"],
    "fortuna 1 liga": ["Puchar Polski"],
    # Украина
    "ukrainian premier league": ["Kubok Ukrajiny"],
    "persha liha": ["Kubok Ukrajiny"],
    # Россия
    "russian premier league": ["Kubok Rossii"],
    "russian football national league": ["Kubok Rossii"],
    # 🔥 ИСПРАВЛЕНИЕ: Добавлены недостающие лиги
    # Ирландия
    "league of ireland premier division": ["FAI Cup"],
    "league of ireland first division": ["FAI Cup"],
    # Северная Ирландия
    "nifl premiership": ["Irish Cup"],
    "nifl championship": ["Irish Cup"],
    # Уэльс
    "cymru premier": ["Welsh Cup"],
    "cymru north": ["Welsh Cup"],
    "cymru south": ["Welsh Cup"],
    # Финляндия
    "veikkausliiga": ["Finnish Cup"],
    "ykkosliiga": ["Finnish Cup"],
    # Исландия
    "besta deild karla": ["Icelandic Cup"],
    "1. deild karla": ["Icelandic Cup"],
    # Словакия
    "slovak super liga": ["Slovenský pohár"],
    # Словения
    "prvaliga": ["Pokal Slovenije"],
    # Венгрия
    "nb i": ["Magyar Kupa"],
    # Болгария
    "efbet liga": ["Kupa na Balgariya"],
    # Израиль
    "ligat ha'al": ["Gvia HaMedina"],
    # Кипр
    "cyta championship": ["Kypriako Kypello"],
    # Казахстан
    "kazakhstan premier league": ["Kazakhstan Cup"],
    # Азербайджан
    "misli premier league": ["Azerbaijan Cup"],
    # Армения
    "armenian premier league": ["Armenian Cup"],
    # Грузия
    "erovnuli liga": ["Georgian Cup"],
    # Молдова
    "super liga": ["Cupa Moldovei"],
    # Беларусь
    "vysheyshaya liga": ["Kubak Belarusi"],
    # Латвия
    "virslīga": ["Latvijas Kauss"],
    # Литва
    "a lyga": ["Lietuvos Taurė"],
    # Эстония
    "meistriliiga": ["Eesti Karikas"],
}

# 🔥 ИСПРАВЛЕНИЕ: Список стран для континента (показываем сразу, без перезагрузки)
def clean_name(n):
    n = unicodedata.normalize('NFKD', n).encode('ASCII', 'ignore').decode('utf-8')
    return n.lower().replace(" ", "").replace("-", "").replace(".", "").replace("fc", "").replace("cf", "")

def is_in_list(club_name, team_list):
    c_clean = clean_name(club_name)
    for t in team_list:
        t_clean = clean_name(t)
        if t_clean in c_clean or c_clean in t_clean:
            return True
    return False

# --- ПЕРЕСОЗДАНИЕ ТУРНИРОВ ---
def rebuild_tournaments():
    db = Session(engine)
    try:
        db.execute(text("DROP TABLE IF EXISTS club_tournaments CASCADE;"))
        db.execute(text("DROP TABLE IF EXISTS tournaments CASCADE;"))
        db.commit()
        Base.metadata.tables['tournaments'].create(bind=engine)
        Base.metadata.tables['club_tournaments'].create(bind=engine)

        # 1. Континенты
        for c in db.query(Club).all():
            l = (c.league or "").lower()
            if "brazil" in l or "argentin" in l: c.continent = "CONMEBOL"
            elif "mls" in l or "mexico" in l: c.continent = "CONCACAF"
            elif "saudi" in l or "japan" in l or "korea" in l or "australia" in l: c.continent = "AFC"
            else: c.continent = "UEFA"
        db.commit()

        # 2. Базовые турниры
        tour_names = set()
        for c, t_list in [
            ("UEFA", ["UEFA Champions League", "UEFA Europa League", "UEFA Conference League"]),
            ("CONMEBOL", ["CONMEBOL Libertadores", "CONMEBOL Sudamericana"]),
            ("CONCACAF", ["CONCACAF Champions Cup"]),
            ("AFC", ["AFC Champions League Elite"]),
            ("World", ["FIFA Intercontinental Cup"])  # 🔥 Убран FIFA Club World Cup
        ]:
            for name in t_list:
                tour_names.add((name, c, "Continental" if c != "World" else "World"))

        unique_leagues = set(cl.league for cl in db.query(Club).all() if cl.league)
        for l in unique_leagues:
            tour_names.add((l, "Domestic", "League"))

        # 🔥 ИСПРАВЛЕНИЕ: Используем COUNTRY_CUPS для реальных названий
        cup_map = {}
        for l in unique_leagues:
            ll = l.lower()
            real_cups = None
            for key, cups in COUNTRY_CUPS.items():
                if key in ll:
                    real_cups = cups
                    break
            if not real_cups:
                real_cups = [f"{l} Cup"]
            cup_map[l] = real_cups
            
            for cup in real_cups:
                tour_names.add((cup, "Domestic", "Cup"))

        for name, cont, t_type in tour_names:
            if not db.query(Tournament).filter_by(name=name).first():
                db.add(Tournament(name=name, continent=cont, type=t_type))
        db.commit()

        tour_map = {t.name: t.id for t in db.query(Tournament).all()}

        # 3. Привязка клубов
        for club in db.query(Club).all():
            if not club.league: continue
            
            if club.league in tour_map:
                db.add(ClubTournament(club_id=club.id, tournament_id=tour_map[club.league]))
            
            cups = cup_map.get(club.league, [f"{club.league} Cup"])
            for c in cups:
                if c in tour_map:
                    db.add(ClubTournament(club_id=club.id, tournament_id=tour_map[c]))

            if club.continent == "UEFA":
                if is_in_list(club.name, UCL_TEAMS):
                    db.add(ClubTournament(club_id=club.id, tournament_id=tour_map["UEFA Champions League"]))
                elif is_in_list(club.name, UEL_TEAMS):
                    db.add(ClubTournament(club_id=club.id, tournament_id=tour_map["UEFA Europa League"]))
                elif is_in_list(club.name, UECL_TEAMS):
                    db.add(ClubTournament(club_id=club.id, tournament_id=tour_map["UEFA Conference League"]))
            
            elif club.continent == "CONMEBOL":
                if club.stars >= 4.0:
                    db.add(ClubTournament(club_id=club.id, tournament_id=tour_map["CONMEBOL Libertadores"]))
                else:
                    db.add(ClubTournament(club_id=club.id, tournament_id=tour_map["CONMEBOL Sudamericana"]))
            
            elif club.continent == "CONCACAF":
                db.add(ClubTournament(club_id=club.id, tournament_id=tour_map["CONCACAF Champions Cup"]))
            
            elif club.continent == "AFC":
                db.add(ClubTournament(club_id=club.id, tournament_id=tour_map["AFC Champions League Elite"]))
                
        db.commit()
        print("✅ Турниры успешно пересозданы.")
    except Exception as e:
        print("❌ Ошибка пересоздания турниров:", e)
        db.rollback()
    finally:
        db.close()

# --- ИНИЦИАЛИЗАЦИЯ БД ---
def init_db():
    db = Session(engine)
    try:
        db.execute(text("ALTER TABLE clubs ADD COLUMN IF NOT EXISTS continent VARCHAR DEFAULT 'UEFA';"))
        db.execute(text("ALTER TABLE tactics ADD COLUMN IF NOT EXISTS bench VARCHAR DEFAULT '[]';"))
        db.commit()
        rebuild_tournaments()
    except Exception as e:
        print("Ошибка инициализации БД:", e)
    finally:
        db.close()

init_db()

# --- ТРЕНИРОВКИ ---
def seed_training_programs():
    db = Session(engine)
    try:
        if db.query(TrainingProgram).count() == 0:
            programs = [
                TrainingProgram(name="Скоростная работа", description="Спринты и ускорения. +1 к скорости.", duration_weeks=2, stat_boosts=json.dumps({"pace": 1})),
                TrainingProgram(name="Ударная техника", description="Отработка ударов. +1 к удару.", duration_weeks=3, stat_boosts=json.dumps({"shooting": 1})),
                TrainingProgram(name="Пас в движении", description="Быстрые комбинации. +1 к пасу.", duration_weeks=3, stat_boosts=json.dumps({"passing": 1})),
                TrainingProgram(name="Дриблинг 1-в-1", description="Обводка и контроль мяча. +1 к дриблингу.", duration_weeks=4, stat_boosts=json.dumps({"dribbling": 1})),
                TrainingProgram(name="Оборонительная стойка", description="Отбор и позиционная игра. +1 к защите.", duration_weeks=4, stat_boosts=json.dumps({"defending": 1})),
                TrainingProgram(name="Физическая мощь", description="Работа в зале. +1 к физике.", duration_weeks=4, stat_boosts=json.dumps({"physicality": 1})),
                TrainingProgram(name="Комплексная работа", description="Всестороннее развитие. Шанс +1 к OVR.", duration_weeks=12, ovr_boost=1, stat_boosts=json.dumps({"pace": 1, "shooting": 1, "passing": 1, "dribbling": 1, "defending": 1, "physicality": 1})),
                TrainingProgram(name="Освоение позиции (лёгкая)", description="Открывает смежную позицию.", duration_weeks=16, position_focus="adjacent"),
                TrainingProgram(name="Освоение позиции (сложная)", description="Открывает дальнюю позицию.", duration_weeks=32, position_focus="far"),
                TrainingProgram(name="Переподготовка", description="Смена амплуа.", duration_weeks=80, position_focus="any"),
                TrainingProgram(name="Воспитание лидера", description="Капитанские качества. +1 пас, +1 физика.", duration_weeks=52, ovr_boost=1, stat_boosts=json.dumps({"passing": 1, "physicality": 1})),
                TrainingProgram(name="Реакция вратаря", description="Отработка реакции и прыгучести. +1 к реакции, +1 к прыжку.", duration_weeks=3, position_focus="GK", stat_boosts=json.dumps({"gk_reflexes": 1, "gk_diving": 1})),
                TrainingProgram(name="Игра на выходах", description="Чтение игры. +1 к позиции, +1 к хватке.", duration_weeks=4, position_focus="GK", stat_boosts=json.dumps({"gk_positioning": 1, "gk_handling": 1})),
                TrainingProgram(name="Удары с дистанции", description="Парирование дальних ударов. +1 к реакции.", duration_weeks=2, position_focus="GK", stat_boosts=json.dumps({"gk_reflexes": 1})),
                TrainingProgram(name="Пенальти", description="Спецподготовка к сериям пенальти. +1 к позиции, +1 к реакции.", duration_weeks=5, position_focus="GK", stat_boosts=json.dumps({"gk_positioning": 1, "gk_reflexes": 1})),
            ]
            for p in programs: db.add(p)
            db.commit()
    finally:
        db.close()

seed_training_programs()

# --- ПОЗИЦИИ И ШТРАФЫ ---
POSITION_GROUPS = {"GK": ["GK"], "DEF": ["CB", "LB", "RB", "LWB", "RWB"], "MID": ["CDM", "CM", "CAM", "LM", "RM"], "ATT": ["LW", "RW", "ST", "CF"]}
POSITION_PENALTY = {
    ("CM", "CDM"): 4, ("CM", "CAM"): 4, ("CM", "LM"): 6, ("CM", "RM"): 6, ("CM", "CB"): 10, ("CM", "LB"): 11, ("CM", "RB"): 11, ("CM", "ST"): 8, ("CM", "LW"): 9, ("CM", "RW"): 9, ("CM", "GK"): 45,
    ("CDM", "CM"): 3, ("CDM", "CAM"): 6, ("CDM", "CB"): 7, ("CDM", "LB"): 8, ("CDM", "RB"): 8, ("CDM", "LM"): 8, ("CDM", "RM"): 8, ("CDM", "ST"): 12, ("CDM", "GK"): 45,
    ("CAM", "CM"): 3, ("CAM", "CDM"): 6, ("CAM", "ST"): 5, ("CAM", "LW"): 6, ("CAM", "RW"): 6, ("CAM", "LM"): 7, ("CAM", "RM"): 7, ("CAM", "CB"): 15, ("CAM", "GK"): 45,
    ("ST", "CF"): 1, ("ST", "CAM"): 7, ("ST", "LW"): 5, ("ST", "RW"): 5, ("ST", "CM"): 10, ("ST", "CDM"): 14, ("ST", "CB"): 18, ("ST", "GK"): 48,
    ("LW", "LM"): 3, ("LW", "RW"): 2, ("LW", "ST"): 5, ("LW", "CAM"): 6, ("LW", "CM"): 9, ("LW", "LB"): 7, ("LW", "RB"): 12, ("LW", "CB"): 15, ("LW", "GK"): 47,
    ("RW", "RM"): 3, ("RW", "LW"): 2, ("RW", "ST"): 5, ("RW", "CAM"): 6, ("RW", "CM"): 9, ("RW", "RB"): 7, ("RW", "LB"): 12, ("RW", "CB"): 15, ("RW", "GK"): 47,
    ("CB", "CDM"): 7, ("CB", "LB"): 4, ("CB", "RB"): 4, ("CB", "CM"): 12, ("CB", "CAM"): 16, ("CB", "ST"): 20, ("CB", "GK"): 40,
    ("LB", "LWB"): 2, ("LB", "CB"): 4, ("LB", "RB"): 5, ("LB", "LM"): 4, ("LB", "CM"): 11, ("LB", "CDM"): 9, ("LB", "CAM"): 15, ("LB", "ST"): 20, ("LB", "GK"): 45,
    ("RB", "RWB"): 2, ("RB", "CB"): 4, ("RB", "LB"): 5, ("RB", "RM"): 4, ("RB", "CM"): 11, ("RB", "CDM"): 9, ("RB", "CAM"): 15, ("RB", "ST"): 20, ("RB", "GK"): 45,
    ("GK", "CB"): 40, ("GK", "CM"): 45, ("GK", "ST"): 48,
    ("LWB", "LB"): 2, ("LWB", "LM"): 3, ("LWB", "CB"): 5,
    ("RWB", "RB"): 2, ("RWB", "RM"): 3, ("RWB", "CB"): 5,
    ("LM", "LW"): 3, ("LM", "CM"): 5, ("LM", "CAM"): 6, ("LM", "LB"): 4, ("LM", "CDM"): 9, ("LM", "ST"): 9, ("LM", "CB"): 14, ("LM", "GK"): 45,
    ("RM", "RW"): 3, ("RM", "CM"): 5, ("RM", "CAM"): 6, ("RM", "RB"): 4, ("RM", "CDM"): 9, ("RM", "ST"): 9, ("RM", "CB"): 14, ("RM", "GK"): 45,
}
GROUP_PENALTY = {
    ("MID", "MID"): 5, ("MID", "DEF"): 12, ("MID", "ATT"): 9, ("MID", "GK"): 45,
    ("DEF", "MID"): 11, ("DEF", "DEF"): 4, ("DEF", "ATT"): 18, ("DEF", "GK"): 42,
    ("ATT", "MID"): 8, ("ATT", "DEF"): 16, ("ATT", "ATT"): 3, ("ATT", "GK"): 47,
    ("GK", "DEF"): 40, ("GK", "MID"): 45, ("GK", "ATT"): 48,
}

def normalize_pos(pos: str) -> str:
    if not pos: return "CM"
    p = pos.upper()
    mapping = {"GOALKEEPER": "GK", "GK": "GK", "LEFT BACK": "LB", "LB": "LB", "LWB": "LWB", "LEFT WING BACK": "LWB", "RIGHT BACK": "RB", "RB": "RB", "RWB": "RWB", "RIGHT WING BACK": "RWB", "CENTRE-BACK": "CB", "CENTER-BACK": "CB", "CB": "CB", "CENTRAL DEFENSIVE MIDFIELD": "CDM", "CDM": "CDM", "CENTRAL MIDFIELD": "CM", "CM": "CM", "CENTRAL ATTACKING MIDFIELD": "CAM", "CAM": "CAM", "LEFT MIDFIELD": "LM", "LM": "LM", "RIGHT MIDFIELD": "RM", "RM": "RM", "LEFT WING": "LW", "LW": "LW", "RIGHT WING": "RW", "RW": "RW", "STRIKER": "ST", "ST": "ST", "CENTRE-FORWARD": "CF", "CF": "CF"}
    for k, v in mapping.items():
        if k in p: return v
    return "CM"

def group_of(pos: str) -> str:
    for g, positions in POSITION_GROUPS.items():
        if pos in positions: return g
    return "MID"

def position_penalty(native_pos: str, target_pos: str, alt_positions: list) -> int:
    native = normalize_pos(native_pos)
    target = normalize_pos(target_pos)
    if native == target: return 0
    alts = [normalize_pos(a) for a in alt_positions]
    if target in alts: return 0
    key = (native, target)
    if key in POSITION_PENALTY: return POSITION_PENALTY[key]
    ng = group_of(native)
    tg = group_of(target)
    return GROUP_PENALTY.get((ng, tg), 20)

def effective_overall(player: Player, slot_pos: str) -> int:
    alts = json.loads(player.alt_positions or "[]")
    pen = position_penalty(player.position, slot_pos, alts)
    return max(1, player.overall_rating - pen)

def apply_training_if_done(player: Player, db: Session) -> bool:
    if not player.training_program_id or not player.training_started_at: return False
    prog = db.query(TrainingProgram).filter_by(id=player.training_program_id).first()
    if not prog: return False
    end_date = player.training_started_at + timedelta(weeks=prog.duration_weeks)
    if datetime.utcnow() < end_date: return False

    if prog.stat_boosts:
        boosts = json.loads(prog.stat_boosts)
        for stat, val in boosts.items():
            if hasattr(player, stat):
                current = getattr(player, stat) or 0
                if random.random() < 0.6: setattr(player, stat, current + 1)

    if prog.ovr_boost and prog.ovr_boost > 0:
        if random.random() < 0.33: player.overall_rating = (player.overall_rating or 50) + 1

    if prog.position_focus:
        alts = json.loads(player.alt_positions or "[]")
        native = normalize_pos(player.position)
        if prog.position_focus == "any":
            all_pos = ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LM", "RM", "LW", "RW", "ST"]
            candidates = [p for p in all_pos if p != native and p not in alts]
            if candidates: alts.append(random.choice(candidates))
        elif prog.position_focus == "far":
            ng = group_of(native)
            candidates = [p for p in ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LM", "RM", "LW", "RW", "ST"] if p != native and p not in alts and group_of(p) != ng]
            if candidates: alts.append(random.choice(candidates))
        elif prog.position_focus == "adjacent":
            adjacent_map = {"CM": ["CDM", "CAM", "LM", "RM"], "CDM": ["CM", "CB"], "CAM": ["CM", "ST", "LW", "RW"], "ST": ["CF", "CAM", "LW", "RW"], "LW": ["LM", "ST", "RW"], "RW": ["RM", "ST", "LW"], "CB": ["CDM", "LB", "RB"], "LB": ["LWB", "CB", "LM"], "RB": ["RWB", "CB", "RM"], "LM": ["LW", "CM", "LB"], "RM": ["RW", "CM", "RB"], "GK": []}
            candidates = [p for p in adjacent_map.get(native, []) if p not in alts]
            if candidates: alts.append(random.choice(candidates))
        elif prog.position_focus == "GK": pass
        player.alt_positions = json.dumps(alts)

    player.training_program_id = None
    player.training_started_at = None
    db.commit()
    return True

app = FastAPI()
security = HTTPBasic()

def run_seed_script():
    result = subprocess.run([sys.executable, "seed_data.py"], capture_output=True, text=True)
    print("Вывод (stdout):", result.stdout)

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {"message": "Soccery 27 API"}

@app.get("/admin/force-rebuild")
def force_rebuild():
    rebuild_tournaments()
    return {"status": "ok", "message": "Все турниры пересозданы и привязаны к клубам. Зайдите в приложение."}

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
        rows = db.query(Club.id, Club.name, Club.league, Club.stars, Club.continent, func.count(Player.id).label("players"), func.avg(Player.overall_rating).label("avg_ovr")).outerjoin(Player, Player.club_id == Club.id).group_by(Club.id).order_by(Club.league, Club.name).all()
        return [{"id": r.id, "name": r.name, "league": r.league, "stars": r.stars or 3.0, "continent": r.continent, "players": int(r.players or 0), "avg_ovr": round(float(r.avg_ovr), 1) if r.avg_ovr else 0} for r in rows]
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
        return {"has_club": True, "club_id": club.id, "club_name": club.name, "league": club.league, "continent": club.continent, "stars": club.stars or 3.0, "is_setup_complete": bool(m.is_setup_complete), "coach_name": m.coach_name}
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

class UpdateCoachNameRequest(BaseModel):
    telegram_id: str
    coach_name: str

@app.post("/api/update-coach-name")
def update_coach_name(req: UpdateCoachNameRequest):
    db = Session(engine)
    try:
        m = db.query(Manager).filter_by(telegram_id=req.telegram_id).first()
        if not m: raise HTTPException(status_code=404, detail="Менеджер не найден")
        m.coach_name = req.coach_name
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
            apply_training_if_done(p, db)
            alts = json.loads(p.alt_positions or "[]")
            result.append({
                "id": p.id, "name": p.name, "position": p.position, "age": p.age,
                "overall": p.overall_rating, "nationality": p.nationality,
                "market_value": p.market_value or 0, "wage": p.wage or 0, "contract_until": p.contract_until,
                "alt_positions": alts,
                "pace": p.pace or 50, "shooting": p.shooting or 50, "passing": p.passing or 50,
                "dribbling": p.dribbling or 50, "defending": p.defending or 50, "physicality": p.physicality or 50,
                "gk_diving": p.gk_diving or 10, "gk_handling": p.gk_handling or 10, "gk_kicking": p.gk_kicking or 10,
                "gk_positioning": p.gk_positioning or 10, "gk_reflexes": p.gk_reflexes or 10
            })
        return result
    finally:
        db.close()

@app.get("/api/training-programs")
def get_training_programs():
    db = Session(engine)
    try:
        programs = db.query(TrainingProgram).all()
        return [{"id": p.id, "name": p.name, "description": p.description, "duration_weeks": p.duration_weeks, "position_focus": p.position_focus, "stat_boosts": json.loads(p.stat_boosts or "{}"), "ovr_boost": p.ovr_boost} for p in programs]
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
        if not player: raise HTTPException(status_code=404, detail="Игрок не найден")
        if player.training_program_id: raise HTTPException(status_code=400, detail="Игрок уже на тренировке")
        prog = db.query(TrainingProgram).filter_by(id=req.program_id).first()
        if not prog: raise HTTPException(status_code=404, detail="Программа не найдена")
        player.training_program_id = prog.id
        player.training_started_at = datetime.utcnow()
        db.commit()
        end_date = player.training_started_at + timedelta(weeks=prog.duration_weeks)
        return {"status": "ok", "program_name": prog.name, "end_date": end_date.isoformat()}
    finally:
        db.close()

@app.get("/api/player/{player_id}/training-status")
def training_status(player_id: int):
    db = Session(engine)
    try:
        player = db.query(Player).filter_by(id=player_id).first()
        if not player: raise HTTPException(status_code=404, detail="Игрок не найден")
        apply_training_if_done(player, db)
        if not player.training_program_id: return {"active": False}
        prog = db.query(TrainingProgram).filter_by(id=player.training_program_id).first()
        if not prog: return {"active": False}
        end_date = player.training_started_at + timedelta(weeks=prog.duration_weeks)
        weeks_left = max(0, (end_date - datetime.utcnow()).days // 7)
        return {"active": True, "program_name": prog.name, "weeks_left": weeks_left, "end_date": end_date.isoformat()}
    finally:
        db.close()

@app.get("/api/tactics/{telegram_id}")
def get_tactics(telegram_id: str):
    db = Session(engine)
    try:
        m = db.query(Manager).filter_by(telegram_id=telegram_id).first()
        if not m: raise HTTPException(status_code=404, detail="Менеджер не найден")
        t = db.query(Tactic).filter_by(manager_id=m.id).first()
        if not t:
            return {"formation": "4-3-3 (Линия)", "starting_xi": [], "bench": [], "captain_id": None, "free_kick_taker_id": None, "corner_taker_id": None, "penalty_taker_id": None}
        try:
            xi = json.loads(t.starting_xi or "[]")
            bench = json.loads(t.bench or "[]")
        except Exception:
            xi = []
            bench = []
        return {"formation": t.formation or "4-3-3 (Линия)", "starting_xi": xi, "bench": bench, "captain_id": t.captain_id, "free_kick_taker_id": t.free_kick_taker_id, "corner_taker_id": t.corner_taker_id, "penalty_taker_id": t.penalty_taker_id}
    finally:
        db.close()

class SaveTacticsRequest(BaseModel):
    telegram_id: str
    formation: str
    starting_xi: List[Optional[int]]
    bench: List[Optional[int]]
    captain_id: Optional[int] = None
    free_kick_taker_id: Optional[int] = None
    corner_taker_id: Optional[int] = None
    penalty_taker_id: Optional[int] = None

@app.post("/api/tactics")
def save_tactics(req: SaveTacticsRequest):
    db = Session(engine)
    try:
        m = db.query(Manager).filter_by(telegram_id=req.telegram_id).first()
        if not m: raise HTTPException(status_code=404, detail="Менеджер не найден")
        t = db.query(Tactic).filter_by(manager_id=m.id).first()
        if not t:
            t = Tactic(manager_id=m.id)
            db.add(t)
        t.formation = req.formation
        t.starting_xi = json.dumps(req.starting_xi)
        t.bench = json.dumps(req.bench)
        t.captain_id = req.captain_id
        t.free_kick_taker_id = req.free_kick_taker_id
        t.corner_taker_id = req.corner_taker_id
        t.penalty_taker_id = req.penalty_taker_id
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()

@app.get("/api/clubs/{club_id}/tournaments")
def get_club_tournaments(club_id: int):
    db = Session(engine)
    try:
        rows = db.query(Tournament).join(ClubTournament).filter(ClubTournament.club_id == club_id).all()
        return [{"id": t.id, "name": t.name, "continent": t.continent, "type": t.type} for t in rows]
    finally:
        db.close()

# --- БОТ ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    web_app_url = "https://soccery-27.onrender.com/app"
    keyboard = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="🚀 Открыть Soccery 27", web_app=types.WebAppInfo(url=web_app_url))]], resize_keyboard=True)
    await message.answer("Добро пожаловать в Soccery 27!\nНажми кнопку ниже, чтобы начать карьеру.", reply_markup=keyboard)

async def start_bot():
    await dp.start_polling(bot)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/app")
def read_index():
    return FileResponse("static/index.html")