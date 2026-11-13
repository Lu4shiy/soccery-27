import os
import json
import random
import unicodedata
import calendar
import asyncio
import threading
from datetime import datetime, timedelta, date
from typing import Optional, List

db_lock = threading.RLock()

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, func, Float, text
from sqlalchemy.orm import declarative_base, Session

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL)
Base = declarative_base()

ADMIN_TELEGRAM_ID = "5020258637"

INJURY_TYPES = [
    {"name": "Небольшой ушиб", "weight": 25, "min_weeks": 0, "max_weeks": 1},
    {"name": "Ушиб колена", "weight": 18, "min_weeks": 0, "max_weeks": 1},
    {"name": "Мышечное повреждение", "weight": 15, "min_weeks": 1, "max_weeks": 3},
    {"name": "Растяжение связок", "weight": 15, "min_weeks": 1, "max_weeks": 3},
    {"name": "Повреждение бедра", "weight": 12, "min_weeks": 1, "max_weeks": 3},
    {"name": "Растяжение приводящей мышцы", "weight": 12, "min_weeks": 2, "max_weeks": 4},
    {"name": "Повреждение паха", "weight": 10, "min_weeks": 2, "max_weeks": 4},
    {"name": "Растяжение подколенного сухожилия", "weight": 10, "min_weeks": 2, "max_weeks": 5},
    {"name": "Повреждение икроножной мышцы", "weight": 8, "min_weeks": 3, "max_weeks": 6},
    {"name": "Перелом пальца ноги", "weight": 7, "min_weeks": 2, "max_weeks": 4},
    {"name": "Сотрясение мозга", "weight": 5, "min_weeks": 1, "max_weeks": 3},
    {"name": "Повреждение лодыжки", "weight": 6, "min_weeks": 2, "max_weeks": 5},
    {"name": "Перелом носа", "weight": 5, "min_weeks": 1, "max_weeks": 3},
    {"name": "Инфекция", "weight": 4, "min_weeks": 1, "max_weeks": 2},
    {"name": "Травма головы", "weight": 4, "min_weeks": 2, "max_weeks": 4},
    {"name": "Повреждение кисти", "weight": 3, "min_weeks": 3, "max_weeks": 6},
    {"name": "Вывих плеча", "weight": 3, "min_weeks": 3, "max_weeks": 6},
    {"name": "Перелом ребра", "weight": 3, "min_weeks": 4, "max_weeks": 6},
    {"name": "Повреждение мениска", "weight": 2, "min_weeks": 5, "max_weeks": 10},
    {"name": "Перелом ключицы", "weight": 2, "min_weeks": 6, "max_weeks": 10},
    {"name": "Перелом плюсневой кости", "weight": 2, "min_weeks": 6, "max_weeks": 12},
    {"name": "Повреждение связок колена", "weight": 2, "min_weeks": 6, "max_weeks": 12},
    {"name": "Трещина в кости", "weight": 1, "min_weeks": 8, "max_weeks": 14},
    {"name": "Разрыв мышцы бедра", "weight": 1, "min_weeks": 8, "max_weeks": 16},
    {"name": "Повреждение спинного диска", "weight": 1, "min_weeks": 8, "max_weeks": 16},
    {"name": "Перелом голени", "weight": 1, "min_weeks": 12, "max_weeks": 20},
    {"name": "Перелом большеберцовой кости", "weight": 1, "min_weeks": 16, "max_weeks": 28},
    {"name": "Разрыв ахиллова сухожилия", "weight": 1, "min_weeks": 20, "max_weeks": 32},
    {"name": "Тяжелое повреждение колена", "weight": 1, "min_weeks": 20, "max_weeks": 35},
    {"name": "Разрыв крестообразных связок", "weight": 1, "min_weeks": 28, "max_weeks": 45}
]

class Club(Base):
    __tablename__ = "clubs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    league = Column(String, index=True)
    original_league = Column(String, nullable=True)
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
    morale = Column(String, default="green")
    fitness = Column(String, default="green")
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    matches_played = Column(Integer, default=0)
    rating_sum = Column(Float, default=0.0)
    fatigue = Column(Integer, default=0)
    injury_weeks = Column(Integer, default=0)
    injury_days = Column(Integer, default=0)
    injury_name = Column(String, nullable=True)
    suspension_matches = Column(Integer, default=0)
    consecutive_yellows = Column(Integer, default=0)
    potential = Column(Integer, default=85)
    growth_progress = Column(Integer, default=0)
    season_start_ovr = Column(Integer, nullable=True)
    original_data = Column(String, nullable=True)

class Fixture(Base):
    __tablename__ = "fixtures"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"))
    round_number = Column(Integer, default=1)
    match_index = Column(Integer, default=0)
    leg = Column(Integer, default=1)
    home_club_id = Column(Integer, ForeignKey("clubs.id"))
    away_club_id = Column(Integer, ForeignKey("clubs.id"))
    is_played = Column(Integer, default=0)
    home_goals = Column(Integer, nullable=True)
    away_goals = Column(Integer, nullable=True)
    home_poss = Column(Integer, default=50)
    away_poss = Column(Integer, default=50)
    home_shots = Column(Integer, default=0)
    away_shots = Column(Integer, default=0)
    home_sot = Column(Integer, default=0)
    away_sot = Column(Integer, default=0)
    home_fouls = Column(Integer, default=0)
    away_fouls = Column(Integer, default=0)
    home_corners = Column(Integer, default=0)
    away_corners = Column(Integer, default=0)
    home_offsides = Column(Integer, default=0)
    away_offsides = Column(Integer, default=0)
    home_xg = Column(Float, default=0.0)
    away_xg = Column(Float, default=0.0)
    home_freekicks = Column(Integer, default=0)
    away_freekicks = Column(Integer, default=0)
    first_half_added = Column(Integer, default=0)
    second_half_added = Column(Integer, default=0)
    has_extra_time = Column(Integer, default=0)
    home_penalties = Column(Integer, nullable=True)
    away_penalties = Column(Integer, nullable=True)

class MatchEvent(Base):
    __tablename__ = "match_events"
    id = Column(Integer, primary_key=True, index=True)
    fixture_id = Column(Integer, ForeignKey("fixtures.id"))
    minute = Column(Integer)
    event_type = Column(String)
    club_id = Column(Integer, ForeignKey("clubs.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    assist_id = Column(Integer, ForeignKey("players.id"), nullable=True)

class MatchPlayerStats(Base):
    __tablename__ = "match_player_stats"
    id = Column(Integer, primary_key=True, index=True)
    fixture_id = Column(Integer, ForeignKey("fixtures.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    club_id = Column(Integer, ForeignKey("clubs.id"))
    minutes_played = Column(Integer, default=0)
    rating = Column(Float, default=6.0)
    is_mvp = Column(Integer, default=0)

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

class Trophy(Base):
    __tablename__ = "trophies"
    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), index=True)
    tournament_name = Column(String)
    season = Column(String)

class GameState(Base):
    __tablename__ = "game_state"
    id = Column(Integer, primary_key=True, default=1)
    current_date = Column(String, default="2026-08-01")
    season = Column(String, default="2026/27")
    last_month_advance_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def clean_name(n):
    if not n: return ""
    n = unicodedata.normalize('NFKD', n).encode('ASCII', 'ignore').decode('utf-8')
    return n.lower().replace(" ", "").replace("-", "").replace(".", "").replace("'", "")

def parse_eng_dates(dates_list, start_year=2026):
    res = []
    for d_str in dates_list:
        try:
            d, m = map(int, d_str.split("."))
            year = start_year if m >= 7 else start_year + 1
            res.append(date(year, m, d))
        except Exception as e:
            print(f"parse_eng_dates FAILED on '{d_str}': {e}")
            raise
    return res

def generate_season_fixtures(db, base_year):
    start_str = f"{base_year}-07-01"
    end_str = f"{base_year+1}-06-30"
    existing = db.query(Fixture).filter(Fixture.date >= start_str, Fixture.date <= end_str).first()
    if existing:
        return
        
    eng_leagues = ["Premier League", "EFL Championship", "EFL League One", "EFL League Two"]
    eng_clubs = db.query(Club).filter(Club.league.in_(eng_leagues)).all()
    if not eng_clubs: return
    
    pl_clubs = [c for c in eng_clubs if c.league == "Premier League"]
    champ_clubs = [c for c in eng_clubs if c.league == "EFL Championship"]
    l1_clubs = [c for c in eng_clubs if c.league == "EFL League One"]
    l2_clubs = [c for c in eng_clubs if c.league == "EFL League Two"]
    
    pl_dates = parse_eng_dates(["23.08", "28.08", "05.09", "13.09", "20.09", "10.10", "17.10", "24.10", "31.10", "07.11", "21.11", "29.11", "02.12", "05.12", "12.12", "19.12", "26.12", "29.12", "03.01", "06.01", "16.01", "23.01", "30.01", "06.02", "10.02", "20.02", "27.02", "03.03", "13.03", "20.03", "10.04", "17.04", "24.04", "01.05", "08.05", "15.05", "23.05", "26.05"], base_year)
    efl_dates = parse_eng_dates(["07.08", "10.08", "17.08", "22.08", "28.08", "02.09", "05.09", "11.09", "19.09", "10.10", "17.10", "24.10", "30.10", "07.11", "21.11", "28.11", "05.12", "11.12", "19.12", "26.12", "29.12", "01.01", "16.01", "23.01", "30.01", "06.02", "13.02", "20.02", "27.02", "02.03", "06.03", "13.03", "20.03", "03.04", "10.04", "17.04", "20.04", "23.04", "01.05", "07.05", "10.05", "13.05", "16.05", "19.05", "22.05", "25.05"], base_year)
    
    fixtures_data = []
    for l_name, l_clubs, l_dates in [("Premier League", pl_clubs, pl_dates), ("EFL Championship", champ_clubs, efl_dates), ("EFL League One", l1_clubs, efl_dates), ("EFL League Two", l2_clubs, efl_dates)]:
        tour = db.query(Tournament).filter_by(name=l_name).first()
        if not tour: continue
        matches = get_double_round_robin(l_clubs[:])
        for r_idx, round_m in enumerate(matches):
            if r_idx >= len(l_dates): break
            for i, (h, a) in enumerate(round_m):
                fixtures_data.append({
                    "date": l_dates[r_idx].strftime("%Y-%m-%d"), "tournament_id": tour.id,
                    "round_number": r_idx+1, "match_index": i, "home_club_id": h.id, "away_club_id": a.id, "is_played": 0
                })
                
    sorted_eng = sorted(eng_clubs, key=lambda c: (-(c.stars or 0), c.name))
    fa_cup = db.query(Tournament).filter_by(name="FA Cup").first()
    carabao = db.query(Tournament).filter(Tournament.name.in_(["Carabao Cup", "EFL Cup"])).first()
    
    fa_dates = parse_eng_dates(["25.08", "24.09", "14.12", "09.01", "23.03", "29.03", "28.05"], base_year)
    car_dates = parse_eng_dates(["20.08", "30.08", "15.09", "28.09", "01.10", "04.10", "07.10", "23.12"], base_year)
    
    for cup, dates in [(fa_cup, fa_dates), (carabao, car_dates)]:
        if not cup: continue
        weak_teams = sorted_eng[36:]
        strong_teams = sorted_eng[:36]
        random.shuffle(weak_teams)
        random.shuffle(strong_teams)
        
        for i in range(0, 56, 2):
            fixtures_data.append({
                "date": dates[0].strftime("%Y-%m-%d"), "tournament_id": cup.id, "round_number": 1, "match_index": i//2,
                "home_club_id": weak_teams[i].id, "away_club_id": weak_teams[i+1].id, "is_played": 0
            })
            
        match_idx = 0
        for i in range(28):
            fixtures_data.append({
                "date": dates[1].strftime("%Y-%m-%d"), "tournament_id": cup.id, "round_number": 2, "match_index": match_idx,
                "home_club_id": strong_teams[i].id, "away_club_id": 9999, "is_played": 0
            })
            match_idx += 1
        for i in range(28, 36, 2):
            fixtures_data.append({
                "date": dates[1].strftime("%Y-%m-%d"), "tournament_id": cup.id, "round_number": 2, "match_index": match_idx,
                "home_club_id": strong_teams[i].id, "away_club_id": strong_teams[i+1].id, "is_played": 0
            })
            match_idx += 1
            
        for i in range(16):
            fixtures_data.append({"date": dates[2].strftime("%Y-%m-%d"), "tournament_id": cup.id, "round_number": 3, "match_index": i, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})
        for i in range(8):
            fixtures_data.append({"date": dates[3].strftime("%Y-%m-%d"), "tournament_id": cup.id, "round_number": 4, "match_index": i, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})
        for i in range(4):
            fixtures_data.append({"date": dates[4].strftime("%Y-%m-%d"), "tournament_id": cup.id, "round_number": 5, "match_index": i, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})
            
        if cup.name in ["Carabao Cup", "EFL Cup"]:
            for i in range(2):
                fixtures_data.append({"date": dates[5].strftime("%Y-%m-%d"), "tournament_id": cup.id, "round_number": 6, "match_index": i, "leg": 1, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})
            for i in range(2):
                fixtures_data.append({"date": dates[6].strftime("%Y-%m-%d"), "tournament_id": cup.id, "round_number": 7, "match_index": i, "leg": 2, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})
            fixtures_data.append({"date": dates[7].strftime("%Y-%m-%d"), "tournament_id": cup.id, "round_number": 8, "match_index": 0, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})
        else:
            for i in range(2):
                fixtures_data.append({"date": dates[5].strftime("%Y-%m-%d"), "tournament_id": cup.id, "round_number": 6, "match_index": i, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})
            fixtures_data.append({"date": dates[6].strftime("%Y-%m-%d"), "tournament_id": cup.id, "round_number": 7, "match_index": 0, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})

    po_champ = db.query(Tournament).filter_by(name="EFL Championship Playoffs").first()
    po_l1 = db.query(Tournament).filter_by(name="EFL League One Playoffs").first()
    po_l2 = db.query(Tournament).filter_by(name="EFL League Two Playoffs").first()
    po_dates = parse_eng_dates(["10.05", "15.05", "18.05", "25.05"], base_year)
    
    if po_champ:
        for i in range(2):
            fixtures_data.append({"date": po_dates[0].strftime("%Y-%m-%d"), "tournament_id": po_champ.id, "round_number": 1, "match_index": i, "leg": 1, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})
        for i in range(2):
            fixtures_data.append({"date": po_dates[1].strftime("%Y-%m-%d"), "tournament_id": po_champ.id, "round_number": 2, "match_index": i, "leg": 1, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})
        for i in range(2):
            fixtures_data.append({"date": po_dates[2].strftime("%Y-%m-%d"), "tournament_id": po_champ.id, "round_number": 3, "match_index": i, "leg": 2, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})
        fixtures_data.append({"date": po_dates[3].strftime("%Y-%m-%d"), "tournament_id": po_champ.id, "round_number": 4, "match_index": 0, "leg": 1, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})

    for po_tour in [po_l1, po_l2]:
        if po_tour:
            for i in range(2):
                fixtures_data.append({"date": po_dates[1].strftime("%Y-%m-%d"), "tournament_id": po_tour.id, "round_number": 1, "match_index": i, "leg": 1, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})
            for i in range(2):
                fixtures_data.append({"date": po_dates[2].strftime("%Y-%m-%d"), "tournament_id": po_tour.id, "round_number": 2, "match_index": i, "leg": 2, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})
            fixtures_data.append({"date": po_dates[3].strftime("%Y-%m-%d"), "tournament_id": po_tour.id, "round_number": 3, "match_index": 0, "leg": 1, "home_club_id": 9999, "away_club_id": 9999, "is_played": 0})

    if fixtures_data:
        db.bulk_insert_mappings(Fixture, fixtures_data)
        db.commit()
        
    season_str = f"{base_year}/{base_year+1}"
    ct_data = []
    for c in eng_clubs:
        for t_name in [c.league, "FA Cup", "EFL Cup"]:
            t = db.query(Tournament).filter_by(name=t_name).first()
            if t:
                existing_ct = db.query(ClubTournament).filter_by(club_id=c.id, tournament_id=t.id, season=season_str).first()
                if not existing_ct:
                    ct_data.append({"club_id": c.id, "tournament_id": t.id, "season": season_str})
    if ct_data:
        db.bulk_insert_mappings(ClubTournament, ct_data)
    db.commit()

def get_double_round_robin(clubs):
    if len(clubs) % 2 != 0: clubs.append(None)
    n = len(clubs)
    matches = []
    for r in range(n - 1):
        round_matches = []
        for i in range(n // 2):
            if clubs[i] and clubs[n - 1 - i]:
                if r % 2 == 0: round_matches.append((clubs[i], clubs[n - 1 - i]))
                else: round_matches.append((clubs[n - 1 - i], clubs[i]))
        matches.append(round_matches)
        clubs.insert(1, clubs.pop())
    first_half = list(matches)
    for r_matches in first_half:
        rev = []
        for h, a in r_matches:
            rev.append((a, h))
        matches.append(rev)
    return matches

def init_db():
    db = Session(engine)
    try:
        db.execute(text("ALTER TABLE clubs ADD COLUMN IF NOT EXISTS original_league VARCHAR;"))
        db.execute(text("UPDATE clubs SET original_league = league WHERE original_league IS NULL;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS morale VARCHAR DEFAULT 'green';"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS fitness VARCHAR DEFAULT 'green';"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS goals INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS assists INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS matches_played INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS rating_sum FLOAT DEFAULT 0.0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS fatigue INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS injury_weeks INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS round_number INTEGER DEFAULT 1;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS match_index INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS leg INTEGER DEFAULT 1;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS home_sot INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS away_sot INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS home_fouls INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS away_fouls INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS home_corners INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS away_corners INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS home_offsides INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS away_offsides INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE game_state ADD COLUMN IF NOT EXISTS last_month_advance_at TIMESTAMP DEFAULT NOW();"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS home_xg FLOAT DEFAULT 0.0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS away_xg FLOAT DEFAULT 0.0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS home_freekicks INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS away_freekicks INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS first_half_added INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS second_half_added INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE match_player_stats ADD COLUMN IF NOT EXISTS is_mvp INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS injury_name VARCHAR;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS injury_days INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS suspension_matches INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS consecutive_yellows INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS potential INTEGER DEFAULT 85;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS growth_progress INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS season_start_ovr INTEGER;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS original_data VARCHAR;"))
        db.execute(text("UPDATE players SET potential = LEAST(99, overall_rating + (random() * 10)::int) WHERE potential = 85;"))
        db.execute(text("UPDATE players SET season_start_ovr = overall_rating WHERE season_start_ovr IS NULL;"))
        db.execute(text("UPDATE players SET original_data = json_build_object('age', age, 'overall_rating', overall_rating, 'market_value', market_value, 'wage', wage, 'pace', pace, 'shooting', shooting, 'passing', passing, 'dribbling', dribbling, 'defending', defending, 'physicality', physicality, 'gk_diving', gk_diving, 'gk_handling', gk_handling, 'gk_kicking', gk_kicking, 'gk_positioning', gk_positioning, 'gk_reflexes', gk_reflexes)::text WHERE original_data IS NULL;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS has_extra_time INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS home_penalties INTEGER;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS away_penalties INTEGER;"))
        db.commit()
        
        if not db.query(GameState).first():
            db.add(GameState(current_date="2026-08-01", season="2026/27"))
            db.commit()

        if not db.query(Club).filter_by(id=9999).first():
            db.add(Club(id=9999, name="TBD", league="None", stars=0))
            db.commit()

        for c in db.query(Club).all():
            if c.id == 9999: continue
            l = (c.league or "").lower()
            if any(x in l for x in ["brazil", "argentin", "chile", "colombia", "ecuador", "paraguay", "peru", "uruguay", "venezuela", "bolivia"]): c.continent = "CONMEBOL"
            elif any(x in l for x in ["mls", "mexico", "liga mx"]): c.continent = "CONCACAF"
            elif any(x in l for x in ["saudi", "japan", "korea", "australia", "china", "qatar", "uae", "india", "iran", "j1 league", "k league"]): c.continent = "AFC"
            else: c.continent = "UEFA"
        db.commit()

        if db.query(Tournament).count() == 0:
            tours = [
                Tournament(name="Premier League", continent="Domestic", type="League"),
                Tournament(name="EFL Championship", continent="Domestic", type="League"),
                Tournament(name="EFL League One", continent="Domestic", type="League"),
                Tournament(name="EFL League Two", continent="Domestic", type="League"),
                Tournament(name="FA Cup", continent="Domestic", type="Cup"),
                Tournament(name="EFL Cup", continent="Domestic", type="Cup"),
                Tournament(name="FA Community Shield", continent="Domestic", type="SuperCup"),
                Tournament(name="EFL Championship Playoffs", continent="Domestic", type="Cup"),
                Tournament(name="EFL League One Playoffs", continent="Domestic", type="Cup"),
                Tournament(name="EFL League Two Playoffs", continent="Domestic", type="Cup"),
                Tournament(name="UEFA Champions League", continent="UEFA", type="Continental"),
                Tournament(name="UEFA Europa League", continent="UEFA", type="Continental"),
                Tournament(name="UEFA Conference League", continent="UEFA", type="Continental")
            ]
            for t in tours: db.add(t)
            db.commit()
            
        for po_name in ["EFL Championship Playoffs", "EFL League One Playoffs", "EFL League Two Playoffs"]:
            if not db.query(Tournament).filter_by(name=po_name).first():
                db.add(Tournament(name=po_name, continent="Domestic", type="Cup"))
        db.commit()

        if db.query(ClubTournament).count() == 0:
            for club in db.query(Club).all():
                if club.id == 9999: continue
                if club.league in ["Premier League", "EFL Championship", "EFL League One", "EFL League Two"]:
                    t1 = db.query(Tournament).filter_by(name=club.league).first()
                    if t1: db.add(ClubTournament(club_id=club.id, tournament_id=t1.id))
                    t2 = db.query(Tournament).filter_by(name="FA Cup").first()
                    if t2: db.add(ClubTournament(club_id=club.id, tournament_id=t2.id))
                    t3 = db.query(Tournament).filter(Tournament.name.in_(["Carabao Cup", "EFL Cup"])).first()
                    if t3: db.add(ClubTournament(club_id=club.id, tournament_id=t3.id))
                elif club.continent == "UEFA":
                    t4 = db.query(Tournament).filter_by(name="UEFA Champions League").first()
                    if t4: db.add(ClubTournament(club_id=club.id, tournament_id=t4.id))
            db.commit()

        carabao_old = db.query(Tournament).filter_by(name="Carabao Cup").first()
        carabao_new = db.query(Tournament).filter_by(name="EFL Cup").first()
        if carabao_old and carabao_new:
            old_fix = [r[0] for r in db.query(Fixture.id).filter(Fixture.tournament_id == carabao_old.id).all()]
            if old_fix:
                db.query(MatchEvent).filter(MatchEvent.fixture_id.in_(old_fix)).delete(synchronize_session=False)
                db.query(MatchPlayerStats).filter(MatchPlayerStats.fixture_id.in_(old_fix)).delete(synchronize_session=False)
                db.query(Fixture).filter(Fixture.id.in_(old_fix)).delete(synchronize_session=False)
            db.query(ClubTournament).filter(ClubTournament.tournament_id == carabao_old.id).update({ClubTournament.tournament_id: carabao_new.id}, synchronize_session=False)
            db.delete(carabao_old)
            db.commit()
        elif carabao_old:
            carabao_old.name = "EFL Cup"
            db.commit()

        state = db.query(GameState).first()
        if state:
            c_date = datetime.strptime(state.current_date, "%Y-%m-%d").date()
            correct_season = f"{c_date.year}/{c_date.year+1}" if c_date.month >= 7 else f"{c_date.year-1}/{c_date.year}"
            if state.season != correct_season:
                state.season = correct_season
                db.commit()

            base_yr = c_date.year if c_date.month >= 7 else c_date.year - 1
            generate_season_fixtures(db, base_yr)

    except Exception as e:
        import traceback
        print("DB Init Error:", e)
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

init_db()

def seed_training_programs():
    db = Session(engine)
    try:
        if db.query(TrainingProgram).count() == 0:
            programs = [
                TrainingProgram(name="Скоростная работа", description="+1 к Скорости.", duration_weeks=2, stat_boosts=json.dumps({"pace": 1})),
                TrainingProgram(name="Ударная техника", description="+1 к Удару.", duration_weeks=3, stat_boosts=json.dumps({"shooting": 1})),
                TrainingProgram(name="Пас в движении", description="+1 к Пасу.", duration_weeks=3, stat_boosts=json.dumps({"passing": 1})),
                TrainingProgram(name="Дриблинг 1-в-1", description="+1 к Дриблингу.", duration_weeks=4, stat_boosts=json.dumps({"dribbling": 1})),
                TrainingProgram(name="Оборонительная стойка", description="+1 к Защите.", duration_weeks=4, stat_boosts=json.dumps({"defending": 1})),
                TrainingProgram(name="Физическая мощь", description="+1 к Физике.", duration_weeks=4, stat_boosts=json.dumps({"physicality": 1})),
                TrainingProgram(name="Вратарская реакция", description="+1 к Реакции, +1 к Прыжку.", duration_weeks=3, position_focus="GK", stat_boosts=json.dumps({"gk_reflexes": 1, "gk_diving": 1})),
                TrainingProgram(name="Игра на выходах", description="+1 к Позиции, +1 к Хватке.", duration_weeks=4, position_focus="GK", stat_boosts=json.dumps({"gk_positioning": 1, "gk_handling": 1})),
                TrainingProgram(name="Комплексная работа", description="+1 ко всем статам. Шанс +1 OVR.", duration_weeks=12, ovr_boost=1, stat_boosts=json.dumps({"pace": 1, "shooting": 1, "passing": 1, "dribbling": 1, "defending": 1, "physicality": 1})),
            ]
            for p in programs: db.add(p)
            db.commit()
        valid_ids = [r[0] for r in db.query(TrainingProgram.id).all()]
        if valid_ids:
            db.query(Player).filter(
                Player.training_program_id.isnot(None),
                ~Player.training_program_id.in_(valid_ids)
            ).update({
                Player.training_program_id: None,
                Player.training_started_at: None
            }, synchronize_session=False)
        else:
            db.query(Player).filter(Player.training_program_id.isnot(None)).update({
                Player.training_program_id: None,
                Player.training_started_at: None
            }, synchronize_session=False)
        db.commit()
    finally:
        db.close()

seed_training_programs()

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
    ("LWB", "LB"): 2, ("LWB", "LM"): 3, ("LWB", "CB"): 5, ("RWB", "RB"): 2, ("RWB", "RM"): 3, ("RWB", "CB"): 5,
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
    exact = POSITION_PENALTY.get((native, target))
    if exact is not None: return exact
    ng = group_of(native)
    tg = group_of(target)
    return GROUP_PENALTY.get((ng, tg), 20)

def recalculate_overall(player: Player) -> int:
    pos = normalize_pos(player.position)
    def s(val): return val if val is not None else 50
    if pos == "GK":
        ovr = int((s(player.gk_reflexes) * 0.35) + (s(player.gk_handling) * 0.25) + (s(player.gk_positioning) * 0.2) + (s(player.gk_diving) * 0.1) + (s(player.gk_kicking) * 0.1))
    elif pos in ["CB", "LB", "RB", "LWB", "RWB"]:
        ovr = int((s(player.defending) * 0.45) + (s(player.physicality) * 0.25) + (s(player.pace) * 0.2) + (s(player.passing) * 0.1))
    elif pos in ["CDM", "CM", "CAM", "LM", "RM"]:
        ovr = int((s(player.passing) * 0.3) + (s(player.dribbling) * 0.2) + (s(player.defending) * 0.2) + (s(player.physicality) * 0.15) + (s(player.shooting) * 0.15))
    else:
        ovr = int((s(player.shooting) * 0.4) + (s(player.pace) * 0.25) + (s(player.dribbling) * 0.25) + (s(player.physicality) * 0.1))
    return max(1, min(99, ovr))

def recalculate_market_value(player: Player) -> int:
    age = player.age
    ovr = player.overall_rating
    pot = player.potential or ovr
    base = int((ovr ** 4) / 5)
    if age <= 21: age_mult = 2.0
    elif age <= 24: age_mult = 1.5
    elif age <= 27: age_mult = 1.2
    elif age <= 30: age_mult = 1.0
    elif age <= 33: age_mult = 0.8
    elif age <= 35: age_mult = 0.6
    else: age_mult = 0.4
    pot_bonus = max(0, pot - ovr) * 100000
    return int((base * age_mult) + pot_bonus)

def apply_training_if_done(player: Player, db: Session) -> bool:
    if not player.training_program_id or not player.training_started_at: return False
    prog = db.query(TrainingProgram).filter_by(id=player.training_program_id).first()
    if not prog: return False
    state = db.query(GameState).first()
    current_game_date = datetime.strptime(state.current_date, "%Y-%m-%d") if state else datetime.utcnow()
    end_date = player.training_started_at + timedelta(weeks=prog.duration_weeks)
    if current_game_date < end_date: return False

    if prog.stat_boosts:
        boosts = json.loads(prog.stat_boosts)
        for stat, val in boosts.items():
            if hasattr(player, stat):
                current = getattr(player, stat) or 0
                if random.random() < 0.6: setattr(player, stat, current + 1)

    if random.random() < 0.33:
        player.overall_rating = (player.overall_rating or 50) + 1

    if random.random() < 0.20:
        alts = json.loads(player.alt_positions or "[]")
        native = normalize_pos(player.position)
        all_pos = ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LM", "RM", "LW", "RW", "ST"]
        candidates = [p for p in all_pos if p != native and p not in alts]
        if candidates:
            alts.append(random.choice(candidates))
            player.alt_positions = json.dumps(alts)

    player.training_program_id = None
    player.training_started_at = None
    return True

app = FastAPI()

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {"message": "Soccery 27 API"}

@app.get("/api/clubs")
def get_clubs():
    db = Session(engine)
    try:
        rows = db.query(Club.id, Club.name, Club.league, Club.stars, Club.continent, func.count(Player.id).label("players"), func.avg(Player.overall_rating).label("avg_ovr")).outerjoin(Player, Player.club_id == Club.id).group_by(Club.id).order_by(Club.league, Club.name).all()
        return [{"id": r.id, "name": r.name, "league": r.league, "stars": r.stars or 3.0, "continent": r.continent, "players": int(r.players or 0), "avg_ovr": round(float(r.avg_ovr), 1) if r.avg_ovr else 0} for r in rows if r.id != 9999]
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
        
        is_admin = (telegram_id == ADMIN_TELEGRAM_ID)
        return {"has_club": True, "club_id": club.id, "club_name": club.name, "league": club.league, "continent": club.continent, "stars": club.stars or 3.0, "is_setup_complete": bool(m.is_setup_complete), "coach_name": m.coach_name, "is_admin": is_admin}
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
        changed = False
        for p in players:
            if apply_training_if_done(p, db): changed = True
            alts = json.loads(p.alt_positions or "[]")
            result.append({
                "id": p.id, "name": p.name, "position": p.position, "age": p.age,
                "overall": p.overall_rating, "nationality": p.nationality,
                "market_value": p.market_value or 0, "wage": p.wage or 0, "contract_until": p.contract_until,
                "alt_positions": alts, "morale": p.morale or "green", "fitness": p.fitness or "green",
                "injury_weeks": p.injury_weeks or 0, "injury_days": p.injury_days or 0, "injury_name": p.injury_name,
                "suspension_matches": p.suspension_matches or 0,
                "pace": p.pace or 50, "shooting": p.shooting or 50, "passing": p.passing or 50,
                "dribbling": p.dribbling or 50, "defending": p.defending or 50, "physicality": p.physicality or 50,
                "gk_diving": p.gk_diving or 10, "gk_handling": p.gk_handling or 10, "gk_kicking": p.gk_kicking or 10,
                "gk_positioning": p.gk_positioning or 10, "gk_reflexes": p.gk_reflexes or 10
            })
        if changed: db.commit()
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
        state = db.query(GameState).first()
        game_date_str = state.current_date if state else "2026-08-01"
        player.training_program_id = prog.id
        player.training_started_at = datetime.strptime(game_date_str, "%Y-%m-%d")
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
        state = db.query(GameState).first()
        current_game_date = datetime.strptime(state.current_date, "%Y-%m-%d") if state else datetime.utcnow()
        end_date = player.training_started_at + timedelta(weeks=prog.duration_weeks)
        weeks_left = max(0, (end_date - current_game_date).days // 7)
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
            xi, bench = [], []
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
def get_club_tournaments(club_id: int, season: str = None):
    db = Session(engine)
    try:
        if not season:
            state = db.query(GameState).first()
            season = state.season if state else "2026/27"
        
        start_yr = int(season.split("/")[0])
        start_str = f"{start_yr}-07-01"
        end_str = f"{start_yr+1}-06-30"
        
        tour_ids = db.query(Fixture.tournament_id).filter(
            (Fixture.home_club_id == club_id) | (Fixture.away_club_id == club_id),
            Fixture.date >= start_str,
            Fixture.date <= end_str
        ).distinct().all()
        
        tids = [t[0] for t in tour_ids]
        if not tids: return []
        
        tours = db.query(Tournament).filter(Tournament.id.in_(tids)).all()
        return [{"id": t.id, "name": t.name, "continent": t.continent, "type": t.type} for t in tours]
    finally:
        db.close()

@app.get("/api/clubs/{club_id}/trophies")
def get_club_trophies(club_id: int):
    db = Session(engine)
    try:
        trophies = db.query(Trophy).filter_by(club_id=club_id).order_by(Trophy.season.desc()).all()
        return [{"tournament_name": t.tournament_name, "season": t.season} for t in trophies]
    finally:
        db.close()

def maybe_auto_advance_month(db):
    with db_lock:
        try:
            state = db.query(GameState).first()
            if not state: return
            now = datetime.utcnow()
            if state.last_month_advance_at is None:
                state.last_month_advance_at = now
                db.commit()
                return
            try:
                elapsed = (now - state.last_month_advance_at).total_seconds()
            except Exception:
                state.last_month_advance_at = now
                db.commit()
                return
            periods = int(elapsed // (8 * 3600))
            if periods <= 0: return
            periods = min(periods, 2)
            state.last_month_advance_at = now
            db.commit()
            for _ in range(periods):
                try:
                    st = db.query(GameState).first()
                    if not st: break
                    curr = datetime.strptime(st.current_date, "%Y-%m-%d").date()
                    last_day = calendar.monthrange(curr.year, curr.month)[1]
                    if curr.day == last_day:
                        if curr.month == 12:
                            next_month = date(curr.year + 1, 1, 1)
                        else:
                            next_month = date(curr.year, curr.month + 1, 1)
                        next_month_last_day = calendar.monthrange(next_month.year, next_month.month)[1]
                        new_date = date(next_month.year, next_month.month, next_month_last_day)
                    else:
                        new_date = date(curr.year, curr.month, last_day)
                    advance_game_date(db, (new_date - curr).days)
                except Exception as e:
                    print("Auto-advance iteration failed:", e)
                    break
        except Exception as e:
            print("maybe_auto_advance_month error:", e)

@app.get("/api/game/time")
def get_game_time():
    db = Session(engine)
    try:
        maybe_auto_advance_month(db)
        state = db.query(GameState).first()
        if not state:
            return {"current_date": "2026-08-01", "season": "2026/27"}
        last = state.last_month_advance_at or datetime.utcnow()
        next_adv = last + timedelta(hours=8)
        return {
            "current_date": state.current_date,
            "season": state.season,
            "next_advance_at": next_adv.isoformat() + "Z"
        }
    finally:
        db.close()

@app.get("/api/game/schedule")
def get_schedule(year: int, month: int, club_id: int = None):
    db = Session(engine)
    try:
        num_days = calendar.monthrange(year, month)[1]
        start_str = f"{year}-{month:02d}-01"
        end_str = f"{year}-{month:02d}-{num_days:02d}"
        
        fixtures = []
        if club_id:
            fixtures = db.query(Fixture).filter(
                Fixture.date >= start_str,
                Fixture.date <= end_str,
                (Fixture.home_club_id == club_id) | (Fixture.away_club_id == club_id)
            ).all()
        
        _club_ids = set()
        _tour_ids = set()
        for f in fixtures:
            _club_ids.add(f.home_club_id)
            _club_ids.add(f.away_club_id)
            _tour_ids.add(f.tournament_id)
        _clubs_map = {c.id: c for c in db.query(Club).filter(Club.id.in_(_club_ids)).all()} if _club_ids else {}
        _tours_map = {t.id: t for t in db.query(Tournament).filter(Tournament.id.in_(_tour_ids)).all()} if _tour_ids else {}
            
        fixture_map = {}
        for f in fixtures:
            fixture_map.setdefault(f.date, []).append(f)
        
        prev_day = date(year, month, 1) - timedelta(days=1)
        prev_match = False
        if club_id:
            prev_match = db.query(Fixture).filter(
                Fixture.date == prev_day.strftime("%Y-%m-%d"),
                (Fixture.home_club_id == club_id) | (Fixture.away_club_id == club_id)
            ).first() is not None
            
        result = []
        
        for day in range(1, num_days + 1):
            date_obj = date(year, month, day)
            date_str = date_obj.strftime("%Y-%m-%d")
            
            if date_str in fixture_map:
                today_matches = fixture_map[date_str]
                f = next((m for m in today_matches if not m.is_played), today_matches[0])
                tour = _tours_map.get(f.tournament_id)
                is_home = (f.home_club_id == club_id)
                opp_id = f.away_club_id if is_home else f.home_club_id
                opp = _clubs_map.get(opp_id)
                
                entry = {
                    "date": date_str, "type": "match", "fixture_id": f.id,
                    "is_played": f.is_played, "tournament_name": tour.name if tour else "Товарищеский",
                    "opponent_name": opp.name if opp else "Соперник", "is_home": is_home,
                    "home_penalties": f.home_penalties, "away_penalties": f.away_penalties
                }
                if f.is_played:
                    entry["home_goals"] = f.home_goals
                    entry["away_goals"] = f.away_goals
                result.append(entry)
                prev_match = True
            elif prev_match:
                result.append({"date": date_str, "type": "rest"})
                prev_match = False
            else:
                if date_obj.day % 2 == 0:
                    result.append({"date": date_str, "type": "training"})
                else:
                    result.append({"date": date_str, "type": "rest"})
        return result
    except Exception as e:
        print("Schedule Error:", e)
        return [{"date": f"{year}-{month:02d}-{d:02d}", "type": "rest"} for d in range(1, calendar.monthrange(year, month)[1] + 1)]
    finally:
        db.close()

@app.get("/api/tournaments/{tournament_id}/standings")
def get_standings(tournament_id: int, season: str = None):
    db = Session(engine) 
    try:
        tour = db.query(Tournament).filter_by(id=tournament_id).first()
        if not tour: raise HTTPException(status_code=404, detail="Турнир не найден")
        
        clubs = db.query(Club).join(ClubTournament).filter(ClubTournament.tournament_id == tournament_id).all()
        if not clubs:
            clubs = db.query(Club).filter(Club.league == tour.name).all()
            
        if not season:
            state = db.query(GameState).first()
            season = state.season if state else "2026/27"
        season_start_year = int(season.split("/")[0])
        start_str = f"{season_start_year}-07-01"
        end_str = f"{season_start_year+1}-06-30"
        fixtures = db.query(Fixture).filter(
            Fixture.tournament_id == tournament_id,
            Fixture.is_played == 1,
            Fixture.date >= start_str,
            Fixture.date <= end_str
        ).all()
        stats = {c.id: {"pos": 0, "club_name": c.name, "mp": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "gd": 0, "pts": 0} for c in clubs}
        
        for f in fixtures:
            if f.home_club_id in stats and f.away_club_id in stats:
                h, a = stats[f.home_club_id], stats[f.away_club_id]
                h["mp"] += 1; a["mp"] += 1
                h["gf"] += f.home_goals; a["gf"] += f.away_goals
                h["ga"] += f.away_goals; a["ga"] += f.home_goals
                
                if f.home_goals > f.away_goals:
                    h["w"] += 1; h["pts"] += 3
                    a["l"] += 1
                elif f.home_goals < f.away_goals:
                    a["w"] += 1; a["pts"] += 3
                    h["l"] += 1
                else:
                    h["d"] += 1; a["d"] += 1
                    h["pts"] += 1; a["pts"] += 1

        standings = list(stats.values())
        for s in standings:
            s["gd"] = s["gf"] - s["ga"]
            
        standings.sort(key=lambda x: (-x["pts"], -x["gd"], -x["gf"], x["club_name"]))
        for i, s in enumerate(standings): s["pos"] = i + 1
            
        return {"type": tour.type, "standings": standings}
    finally:
        db.close()

@app.get("/api/match/{fixture_id}/players")
def get_match_players(fixture_id: int):
    db = Session(engine)
    try:
        fx = db.query(Fixture).filter_by(id=fixture_id).first()
        if not fx:
            return {"home": [], "away": [], "home_name": "", "away_name": "", "home_club_id": None, "away_club_id": None}
        
        home = db.query(Club).filter_by(id=fx.home_club_id).first()
        away = db.query(Club).filter_by(id=fx.away_club_id).first()
        
        events = db.query(MatchEvent).filter_by(fixture_id=fixture_id).all()
        p_events = {}
        for e in events:
            if e.player_id:
                if e.player_id not in p_events: p_events[e.player_id] = {"goals": 0, "assists": 0, "own_goals": 0, "yellow": 0, "red": 0, "penalty_miss": 0}
                if e.event_type in ('goal', 'penalty_goal'): p_events[e.player_id]["goals"] += 1
                if e.event_type == 'own_goal': p_events[e.player_id]["own_goals"] += 1
                if e.event_type == 'yellow_card': p_events[e.player_id]["yellow"] += 1
                if e.event_type == 'red_card': p_events[e.player_id]["red"] += 1
                if e.event_type == 'penalty_miss': p_events[e.player_id]["penalty_miss"] += 1
            if e.event_type in ('goal', 'penalty_goal') and e.assist_id:
                if e.assist_id not in p_events: p_events[e.assist_id] = {"goals": 0, "assists": 0, "own_goals": 0, "yellow": 0, "red": 0, "penalty_miss": 0}
                p_events[e.assist_id]["assists"] += 1

        stats = db.query(MatchPlayerStats).filter_by(fixture_id=fixture_id).all()
        home_players = []
        away_players = []
        for s in stats:
            p = db.query(Player).filter_by(id=s.player_id).first()
            if not p: continue
            ev = p_events.get(p.id, {"goals": 0, "assists": 0, "own_goals": 0, "yellow": 0, "red": 0, "penalty_miss": 0})
            entry = {
                "name": p.name,
                "position": p.position,
                "minutes": s.minutes_played,
                "rating": round(s.rating, 1),
                "is_mvp": bool(s.is_mvp),
                "goals": ev["goals"],
                "assists": ev["assists"],
                "own_goals": ev["own_goals"],
                "yellow": ev["yellow"],
                "red": ev["red"],
                "penalty_miss": ev["penalty_miss"]
            }
            if s.club_id == fx.home_club_id:
                home_players.append(entry)
            else:
                away_players.append(entry)
        
        home_players.sort(key=lambda x: -x["rating"])
        away_players.sort(key=lambda x: -x["rating"])
        
        return {
            "home": home_players,
            "away": away_players,
            "home_name": home.name if home else "TBD",
            "away_name": away.name if away else "TBD",
            "home_club_id": fx.home_club_id,
            "away_club_id": fx.away_club_id
        }
    finally:
        db.close()

@app.get("/api/tournaments/{tournament_id}/stats")
def get_stats(tournament_id: int, season: str = None):
    db = Session(engine)
    try:
        tour = db.query(Tournament).filter_by(id=tournament_id).first()
        if not tour: return {"scorers": [], "assists": [], "rating": [], "mvps": [], "yellows": [], "reds": [], "clean_sheets": []}
        
        if not season:
            state = db.query(GameState).first()
            season = state.season if state else "2026/27"
        season_start_year = int(season.split("/")[0])
        start_str = f"{season_start_year}-07-01"
        end_str = f"{season_start_year+1}-06-30"
        fixtures = db.query(Fixture).filter(
            Fixture.tournament_id == tournament_id,
            Fixture.is_played == 1,
            Fixture.date >= start_str,
            Fixture.date <= end_str
        ).all()
        fx_ids = [f.id for f in fixtures]
        
        if not fx_ids:
            return {"scorers": [], "assists": [], "rating": [], "mvps": [], "yellows": [], "reds": [], "clean_sheets": []}
            
        scorers_q = db.query(MatchEvent.player_id, func.count(MatchEvent.id)).filter(
            MatchEvent.fixture_id.in_(fx_ids),
            MatchEvent.event_type.in_(['goal', 'penalty_goal'])
        ).group_by(MatchEvent.player_id).order_by(func.count(MatchEvent.id).desc()).limit(10).all()
        
        scorers = []
        for pid, count in scorers_q:
            p = db.query(Player).filter_by(id=pid).first()
            if p:
                club = db.query(Club).filter_by(id=p.club_id).first()
                scorers.append({"player": p.name, "team": club.name if club else "—", "nationality": p.nationality, "val": count})
            
        assists_q = db.query(MatchEvent.assist_id, func.count(MatchEvent.id)).filter(
            MatchEvent.fixture_id.in_(fx_ids),
            MatchEvent.event_type.in_(['goal', 'penalty_goal']),
            MatchEvent.assist_id.isnot(None)
        ).group_by(MatchEvent.assist_id).order_by(func.count(MatchEvent.id).desc()).limit(10).all()
        
        assists = []
        for pid, count in assists_q:
            p = db.query(Player).filter_by(id=pid).first()
            if p:
                club = db.query(Club).filter_by(id=p.club_id).first()
                assists.append({"player": p.name, "team": club.name if club else "—", "nationality": p.nationality, "val": count})
            
        ratings_q = db.query(MatchPlayerStats.player_id, func.avg(MatchPlayerStats.rating)).filter(
            MatchPlayerStats.fixture_id.in_(fx_ids)
        ).group_by(MatchPlayerStats.player_id).order_by(func.avg(MatchPlayerStats.rating).desc()).limit(10).all()
        
        avg_ratings = []
        for pid, avg_r in ratings_q:
            p = db.query(Player).filter_by(id=pid).first()
            if p:
                club = db.query(Club).filter_by(id=p.club_id).first()
                avg_ratings.append({"player": p.name, "team": club.name if club else "—", "nationality": p.nationality, "val": round(avg_r, 2)})
        
        mvp_q = db.query(MatchPlayerStats.player_id, func.count(MatchPlayerStats.id)).filter(
            MatchPlayerStats.fixture_id.in_(fx_ids),
            MatchPlayerStats.is_mvp == 1
        ).group_by(MatchPlayerStats.player_id).order_by(func.count(MatchPlayerStats.id).desc()).limit(10).all()
        
        mvps = []
        for pid, count in mvp_q:
            p = db.query(Player).filter_by(id=pid).first()
            if p:
                club = db.query(Club).filter_by(id=p.club_id).first()
                mvps.append({"player": p.name, "team": club.name if club else "—", "nationality": p.nationality, "val": count})
        
        yellows_q = db.query(MatchEvent.player_id, func.count(MatchEvent.id)).filter(
            MatchEvent.fixture_id.in_(fx_ids),
            MatchEvent.event_type == 'yellow_card'
        ).group_by(MatchEvent.player_id).order_by(func.count(MatchEvent.id).desc()).limit(10).all()

        yellows = []
        for pid, count in yellows_q:
            p = db.query(Player).filter_by(id=pid).first()
            if p:
                club = db.query(Club).filter_by(id=p.club_id).first()
                yellows.append({"player": p.name, "team": club.name if club else "—", "nationality": p.nationality, "val": count})

        reds_q = db.query(MatchEvent.player_id, func.count(MatchEvent.id)).filter(
            MatchEvent.fixture_id.in_(fx_ids),
            MatchEvent.event_type == 'red_card'
        ).group_by(MatchEvent.player_id).order_by(func.count(MatchEvent.id).desc()).limit(10).all()

        reds = []
        for pid, count in reds_q:
            p = db.query(Player).filter_by(id=pid).first()
            if p:
                club = db.query(Club).filter_by(id=p.club_id).first()
                reds.append({"player": p.name, "team": club.name if club else "—", "nationality": p.nationality, "val": count})
            
        cs_dict = {}
        for f in fixtures:
            if f.home_goals == 0: cs_dict[f.away_club_id] = cs_dict.get(f.away_club_id, 0) + 1
            if f.away_goals == 0: cs_dict[f.home_club_id] = cs_dict.get(f.home_club_id, 0) + 1
                
        clean_sheets = []
        for cid, count in cs_dict.items():
            c = db.query(Club).filter_by(id=cid).first()
            if c: clean_sheets.append({"team": c.name, "val": count})
        clean_sheets.sort(key=lambda x: x["val"], reverse=True)

        return {"scorers": scorers, "assists": assists, "rating": avg_ratings, "mvps": mvps, "yellows": yellows, "reds": reds, "clean_sheets": clean_sheets[:10]}
    finally:
        db.close()

@app.get("/api/tournaments/{tournament_id}/bracket")
def get_bracket(tournament_id: int, season: str = None):
    db = Session(engine)
    try:
        tour = db.query(Tournament).filter_by(id=tournament_id).first()
        if not tour: raise HTTPException(status_code=404, detail="Турнир не найден")
        
        if not season:
            state = db.query(GameState).first()
            season = state.season if state else "2026/27"
        season_start_year = int(season.split("/")[0])
        start_str = f"{season_start_year}-07-01"
        end_str = f"{season_start_year+1}-06-30"
        fixtures = db.query(Fixture).filter(
            Fixture.tournament_id == tournament_id,
            Fixture.date >= start_str,
            Fixture.date <= end_str
        ).order_by(Fixture.round_number, Fixture.match_index, Fixture.leg).all()
        if not fixtures:
            return {"type": tour.type, "rounds": []}
        
        _club_ids = set()
        for f in fixtures:
            _club_ids.add(f.home_club_id)
            _club_ids.add(f.away_club_id)
        _clubs_map = {c.id: c for c in db.query(Club).filter(Club.id.in_(_club_ids)).all()} if _club_ids else {}
            
        rounds_dict = {}
        for f in fixtures:
            if f.round_number not in rounds_dict:
                rounds_dict[f.round_number] = []
                
            h = _clubs_map.get(f.home_club_id)
            a = _clubs_map.get(f.away_club_id)
            
            rounds_dict[f.round_number].append({
                "id": f.id,
                "team1": h.name if h else "TBD",
                "team2": a.name if a else "TBD",
                "score1": f.home_goals,
                "score2": f.away_goals,
                "pen1": f.home_penalties,
                "pen2": f.away_penalties,
                "is_played": bool(f.is_played),
                "leg": f.leg
            })

        sorted_rounds = []
        for r_num in sorted(rounds_dict.keys()):
            r_name = f"Тур {r_num}"
            if tour.name in ["FA Cup", "Carabao Cup", "EFL Cup"]:
                if r_num == 1: r_name = "Предварительный этап"
                elif r_num == 2: r_name = "1/64 финала"
                elif r_num == 3: r_name = "1/32 финала"
                elif r_num == 4: r_name = "1/16 финала"
                elif r_num == 5: r_name = "1/4 финала"
                elif r_num == 6:
                    r_name = "1/2 финала" if tour.name == "FA Cup" else "1/2 финала (1-й матч)"
                elif r_num == 7:
                    r_name = "Финал" if tour.name == "FA Cup" else "1/2 финала (2-й матч)"
                elif r_num == 8: r_name = "Финал"

            sorted_rounds.append({"name": r_name, "matches": rounds_dict[r_num]})

        return {"type": tour.type, "rounds": sorted_rounds}
    finally:
        db.close()

@app.post("/api/admin/reset-game")
def reset_game(req: dict):
    tg_id = req.get("telegram_id")
    if tg_id != ADMIN_TELEGRAM_ID: raise HTTPException(status_code=403, detail="Нет прав")
    
    with db_lock:
        db = Session(engine)
        try:
            db.execute(text("DELETE FROM match_events"))
            db.execute(text("DELETE FROM match_player_stats"))
            db.execute(text("DELETE FROM fixtures"))
            db.execute(text("DELETE FROM tactics"))
            db.execute(text("DELETE FROM managers"))
            db.execute(text("DELETE FROM trophies"))
            db.execute(text("DELETE FROM club_tournaments"))
            db.execute(text("UPDATE clubs SET league = original_league"))
            db.commit()
            
            players = db.query(Player).all()
            for p in players:
                if p.original_data:
                    try:
                        orig = json.loads(p.original_data)
                        for k, v in orig.items():
                            setattr(p, k, v)
                    except Exception:
                        pass
                p.goals = 0
                p.assists = 0
                p.matches_played = 0
                p.rating_sum = 0.0
                p.fatigue = 0
                p.injury_weeks = 0
                p.injury_days = 0
                p.injury_name = None
                p.fitness = "green"
                p.morale = "green"
                p.consecutive_yellows = 0
                p.suspension_matches = 0
                p.training_program_id = None
                p.training_started_at = None
                p.growth_progress = 0
                p.season_start_ovr = p.overall_rating
                p.alt_positions = "[]"
            db.commit()
            
            state = db.query(GameState).first()
            if state:
                state.current_date = "2026-08-01"
                state.last_month_advance_at = datetime.utcnow()
            db.commit()
            init_db()
            return {"status": "ok"}
        finally:
            db.close()

class AdminActionRequest(BaseModel):
    telegram_id: str
    password: str

@app.post("/api/admin/advance-day")
def advance_day_api(req: AdminActionRequest):
    if req.password != "soccery27admin":
        raise HTTPException(status_code=403, detail="Неверный пароль")
    db = Session(engine)
    try:
        new_date = advance_game_date(db, 1)
        return {"status": "ok", "new_date": new_date}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/admin/advance-week")
def advance_week_api(req: AdminActionRequest):
    if req.password != "soccery27admin":
        raise HTTPException(status_code=403, detail="Неверный пароль")
    db = Session(engine)
    try:
        state = db.query(GameState).first()
        if not state:
            raise HTTPException(status_code=404, detail="Состояние игры не найдено")
        curr = datetime.strptime(state.current_date, "%Y-%m-%d").date()
        days_to_sunday = 6 - curr.weekday()
        if days_to_sunday == 0:
            days_to_sunday = 7
        new_date = advance_game_date(db, days_to_sunday)
        return {"status": "ok", "new_date": new_date}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

class SimulateToDateRequest(BaseModel):
    telegram_id: str
    password: str
    target_date: str

@app.post("/api/admin/simulate-to-date")
def simulate_to_date_api(req: SimulateToDateRequest):
    if req.password != "soccery27admin":
        raise HTTPException(status_code=403, detail="Неверный пароль")
    db = Session(engine)
    try:
        state = db.query(GameState).first()
        if not state:
            raise HTTPException(status_code=404, detail="Состояние игры не найдено")
        curr = datetime.strptime(state.current_date, "%Y-%m-%d").date()
        target = datetime.strptime(req.target_date, "%Y-%m-%d").date()
        
        days_to_add = (target - curr).days - 1
        if days_to_add <= 0:
            return {"status": "ok", "new_date": state.current_date, "message": "Дата уже наступила или прошла"}
            
        new_date = advance_game_date(db, days_to_add)
        return {"status": "ok", "new_date": new_date}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/admin/advance-month")
def advance_month_api(req: AdminActionRequest):
    if req.password != "soccery27admin":
        raise HTTPException(status_code=403, detail="Неверный пароль")
    db = Session(engine)
    try:
        state = db.query(GameState).first()
        if not state:
            raise HTTPException(status_code=404, detail="Состояние игры не найдено")
        curr = datetime.strptime(state.current_date, "%Y-%m-%d").date()
        last_day = calendar.monthrange(curr.year, curr.month)[1]
        if curr.day == last_day:
            if curr.month == 12:
                next_month = date(curr.year + 1, 1, 1)
            else:
                next_month = date(curr.year, curr.month + 1, 1)
            next_month_last_day = calendar.monthrange(next_month.year, next_month.month)[1]
            new_date = date(next_month.year, next_month.month, next_month_last_day)
        else:
            new_date = date(curr.year, curr.month, last_day)
        delta_days = (new_date - curr).days
        new_date_str = advance_game_date(db, delta_days)
        return {"status": "ok", "new_date": new_date_str}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/admin/reset-career")
def reset_career_api(req: AdminActionRequest):
    if req.password != "soccery27admin":
        raise HTTPException(status_code=403, detail="Неверный пароль")
    with db_lock:
        db = Session(engine)
        try:
            db.execute(text("DELETE FROM match_events"))
            db.execute(text("DELETE FROM match_player_stats"))
            db.execute(text("DELETE FROM fixtures"))
            db.execute(text("DELETE FROM tactics"))
            db.execute(text("DELETE FROM managers"))
            db.execute(text("DELETE FROM trophies"))
            db.execute(text("DELETE FROM club_tournaments"))
            db.execute(text("UPDATE clubs SET league = original_league"))
            db.commit()
            
            db.query(Player).update({
                Player.goals: 0, Player.assists: 0, Player.matches_played: 0,
                Player.rating_sum: 0.0, Player.fatigue: 0, Player.injury_weeks: 0,
                Player.injury_days: 0, Player.injury_name: None,
                Player.fitness: "green", Player.morale: "green",
                Player.consecutive_yellows: 0, Player.suspension_matches: 0,
                Player.training_program_id: None, Player.training_started_at: None,
                Player.growth_progress: 0, Player.season_start_ovr: Player.overall_rating
            }, synchronize_session=False)
            
            state = db.query(GameState).first()
            if state:
                state.current_date = "2026-08-01"
                state.season = "2026/27"
                state.last_month_advance_at = datetime.utcnow()
            db.commit()
            init_db()
            return {"status": "ok"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            db.close()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    web_app_url = "https://soccery-27.onrender.com/app"
    keyboard = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="🚀 Открыть Soccery 27", web_app=types.WebAppInfo(url=web_app_url))]], resize_keyboard=True)
    await message.answer("Добро пожаловать в Soccery 27!\nНажми кнопку ниже, чтобы начать карьеру.", reply_markup=keyboard)

def advance_cup_bracket(fx, db):
    tour = db.query(Tournament).filter_by(id=fx.tournament_id).first()
    if not tour or tour.type not in ["Cup", "SuperCup"]:
        return

    if tour.name == "EFL Championship Playoffs":
        if fx.round_number == 1:
            next_fx = db.query(Fixture).filter_by(tournament_id=fx.tournament_id, round_number=2, match_index=fx.match_index).first()
            if next_fx:
                if fx.home_penalties is not None and fx.away_penalties is not None:
                    winner_id = fx.home_club_id if fx.home_penalties > fx.away_penalties else fx.away_club_id
                else:
                    winner_id = fx.home_club_id if (fx.home_goals or 0) > (fx.away_goals or 0) else fx.away_club_id
                next_fx.away_club_id = winner_id
                db.flush()
            return

    is_two_legged = (tour.name in ["Carabao Cup", "EFL Cup"] and fx.round_number == 6) or \
                    (tour.name == "EFL Championship Playoffs" and fx.round_number == 2) or \
                    (tour.name in ["EFL League One Playoffs", "EFL League Two Playoffs"] and fx.round_number == 1)

    if is_two_legged and fx.leg == 1:
        leg2 = db.query(Fixture).filter_by(
            tournament_id=fx.tournament_id,
            round_number=fx.round_number + 1,
            match_index=fx.match_index,
            leg=2
        ).first()
        if leg2:
            leg2.home_club_id = fx.away_club_id
            leg2.away_club_id = fx.home_club_id
            db.flush()
        return

    is_two_legged_2nd = (tour.name in ["Carabao Cup", "EFL Cup"] and fx.round_number == 7) or \
                        (tour.name == "EFL Championship Playoffs" and fx.round_number == 3) or \
                        (tour.name in ["EFL League One Playoffs", "EFL League Two Playoffs"] and fx.round_number == 2)

    if is_two_legged_2nd and fx.leg == 2:
        leg1 = db.query(Fixture).filter_by(
            tournament_id=fx.tournament_id,
            round_number=fx.round_number - 1,
            match_index=fx.match_index,
            leg=1
        ).first()
        if leg1 and leg1.is_played:
            agg_home = (leg1.home_goals or 0) + (fx.away_goals or 0)
            agg_away = (leg1.away_goals or 0) + (fx.home_goals or 0)
            if agg_home > agg_away:
                winner_id = fx.away_club_id
            elif agg_away > agg_home:
                winner_id = fx.home_club_id
            else:
                if fx.home_penalties is not None and fx.away_penalties is not None:
                    winner_id = fx.home_club_id if fx.home_penalties > fx.away_penalties else fx.away_club_id
                else:
                    winner_id = fx.home_club_id if random.random() < 0.5 else fx.away_club_id

            final_fx = db.query(Fixture).filter_by(
                tournament_id=fx.tournament_id,
                round_number=fx.round_number + 1
            ).first()
            if final_fx:
                if fx.match_index == 0:
                    final_fx.home_club_id = winner_id
                else:
                    final_fx.away_club_id = winner_id
                db.flush()
        return

    if fx.home_penalties is not None and fx.away_penalties is not None:
        winner_id = fx.home_club_id if fx.home_penalties > fx.away_penalties else fx.away_club_id
    else:
        winner_id = fx.home_club_id if (fx.home_goals or 0) > (fx.away_goals or 0) else fx.away_club_id
        if (fx.home_goals or 0) == (fx.away_goals or 0):
            winner_id = fx.home_club_id if random.random() < 0.5 else fx.away_club_id

    if fx.round_number == 1:
        next_fx = db.query(Fixture).filter_by(
            tournament_id=fx.tournament_id, round_number=2, match_index=fx.match_index
        ).first()
        if next_fx:
            next_fx.away_club_id = winner_id
    else:
        next_round = fx.round_number + 1
        next_match_index = fx.match_index // 2
        next_fx = db.query(Fixture).filter_by(
            tournament_id=fx.tournament_id,
            round_number=next_round,
            match_index=next_match_index
        ).first()
        if next_fx:
            if fx.match_index % 2 == 0:
                next_fx.home_club_id = winner_id
            else:
                next_fx.away_club_id = winner_id
    db.flush()

def simulate_match(fixture_id: int, db: Session):
    fx = db.query(Fixture).filter_by(id=fixture_id).first()
    if not fx or fx.is_played: return
        
    if fx.home_club_id == 9999 or fx.away_club_id == 9999:
        fx.is_played = 1
        fx.home_goals = 0
        fx.away_goals = 0
        db.commit()
        return
            
    home = db.query(Club).filter_by(id=fx.home_club_id).first()
    away = db.query(Club).filter_by(id=fx.away_club_id).first()
    if not home or not away: return

    def get_xi(club_id):
        t = db.query(Tactic).join(Manager).filter(Manager.club_id == club_id).first()
        if not t or not t.starting_xi:
            return db.query(Player).filter_by(club_id=club_id, injury_weeks=0, injury_days=0, suspension_matches=0).order_by(Player.overall_rating.desc()).limit(11).all()
            
        xi_ids = json.loads(t.starting_xi or "[]")
        bench_ids = json.loads(t.bench or "[]") if t.bench else []
        all_players = {p.id: p for p in db.query(Player).filter_by(club_id=club_id).all()}
        
        available_bench_objs = [all_players[pid] for pid in bench_ids if pid in all_players and all_players[pid].injury_weeks == 0 and all_players[pid].injury_days == 0 and all_players[pid].suspension_matches == 0]
        
        available_reserve_objs = [p for p in all_players.values() if p.id not in xi_ids and p.id not in bench_ids and p.injury_weeks == 0 and p.injury_days == 0 and p.suspension_matches == 0]
        available_reserve_objs.sort(key=lambda p: p.overall_rating, reverse=True)
        
        def get_best_replacement(target_pos):
            nonlocal available_bench_objs, available_reserve_objs
            if available_bench_objs:
                best = min(available_bench_objs, key=lambda p: position_penalty(p.position, target_pos, json.loads(p.alt_positions or "[]")))
                available_bench_objs.remove(best)
                return best
            if available_reserve_objs:
                best = min(available_reserve_objs, key=lambda p: position_penalty(p.position, target_pos, json.loads(p.alt_positions or "[]")))
                available_reserve_objs.remove(best)
                return best
            return None

        final_xi = []
        for pid in xi_ids:
            p = all_players.get(pid)
            if p and p.injury_weeks == 0 and p.injury_days == 0 and p.suspension_matches == 0:
                final_xi.append(p)
            else:
                target_pos = p.position if p else "CM"
                rep = get_best_replacement(target_pos)
                if rep:
                    final_xi.append(rep)
                    
        while len(final_xi) < 11:
            if available_bench_objs:
                final_xi.append(available_bench_objs.pop(0))
            elif available_reserve_objs:
                final_xi.append(available_reserve_objs.pop(0))
            else:
                break
                
        return final_xi

    h_xi = get_xi(home.id)
    a_xi = get_xi(away.id)
    
    h_att = sum([(p.shooting or 50) + (p.pace or 50) for p in h_xi if "Goalkeeper" not in p.position]) / 20
    a_def = sum([(p.defending or 50) + (p.physicality or 50) for p in a_xi if "Goalkeeper" not in p.position]) / 20
    a_att = sum([(p.shooting or 50) + (p.pace or 50) for p in a_xi if "Goalkeeper" not in p.position]) / 20
    h_def = sum([(p.defending or 50) + (p.physicality or 50) for p in h_xi if "Goalkeeper" not in p.position]) / 20
    
    h_goals, a_goals = 0, 0
    events = []
    used_by_any = set()
    used_by_non_sub = set()
    match_goals = {}
    match_assists = {}
    match_yellow = {}
    match_red = {}
    match_own_goals = {}
    match_penalty_miss = {}
    
    def pick_minute(lo=1, hi=90, is_sub=False):
        if is_sub:
            available = [m for m in range(lo, hi+1) if m not in used_by_non_sub]
            if not available:
                m = random.randint(lo, hi)
            else:
                m = random.choice(available)
            used_by_any.add(m)
            return m
        available = [m for m in range(lo, hi+1) if m not in used_by_any]
        if not available:
            return random.randint(lo, hi)
        m = random.choice(available)
        used_by_any.add(m)
        used_by_non_sub.add(m)
        return m
    
    def add_event(minute, e_type, club_id, p_id=None, a_id=None):
        events.append(MatchEvent(fixture_id=fx.id, minute=minute, event_type=e_type, club_id=club_id, player_id=p_id, assist_id=a_id))
        
    add_event(0, "start", None)
    add_event(45, "half_end", None)
    add_event(46, "second_half", None)
    add_event(90, "end", None)
    used_by_any.update([0, 45, 46, 90])

    xi_ids_h = [p.id for p in h_xi]
    xi_ids_a = [p.id for p in a_xi]
    h_bench = db.query(Player).filter(
        Player.club_id == home.id,
        ~Player.id.in_(xi_ids_h),
        func.coalesce(Player.injury_weeks, 0) == 0,
        func.coalesce(Player.injury_days, 0) == 0,
        func.coalesce(Player.suspension_matches, 0) == 0
    ).order_by(Player.overall_rating.desc()).limit(9).all()
    a_bench = db.query(Player).filter(
        Player.club_id == away.id,
        ~Player.id.in_(xi_ids_a),
        func.coalesce(Player.injury_weeks, 0) == 0,
        func.coalesce(Player.injury_days, 0) == 0,
        func.coalesce(Player.suspension_matches, 0) == 0
    ).order_by(Player.overall_rating.desc()).limit(9).all()
    
    h_on_pitch = list(h_xi)
    a_on_pitch = list(a_xi)
    h_bench_available = list(h_bench)
    a_bench_available = list(a_bench)
    
    h_subs_off = {}
    a_subs_off = {}
    h_subs_on = {}
    a_subs_on = {}
    h_subs_used = 0
    a_subs_used = 0
    max_subs = 5

    total_shots_h = max(2, int((h_att - a_def) * 1.5) + 10)
    total_shots_a = max(2, int((a_att - h_def) * 1.5) + 8)
    h_sot, a_sot = 0, 0
    
    if not h_xi or not a_xi:
        fx.is_played = 1
        fx.home_goals = 0
        fx.away_goals = 0
        db.commit()
        return
    
    def pick_scorer(on_pitch):
        field_players = [p for p in on_pitch if normalize_pos(p.position) != "GK"]
        if not field_players: return random.choice(on_pitch)
        weights = [(p.shooting or 50) + (p.pace or 50) * 0.5 + (p.dribbling or 50) * 0.2 for p in field_players]
        return random.choices(field_players, weights=weights, k=1)[0]

    def pick_assister(on_pitch, scorer):
        pool = [p for p in on_pitch if p.id != scorer.id and normalize_pos(p.position) != "GK"]
        if not pool: return None
        weights = [(p.passing or 50) + (p.dribbling or 50) * 0.5 for p in pool]
        return random.choices(pool, weights=weights, k=1)[0]

    for _ in range(total_shots_h):
        if random.random() < 0.4:
            h_sot += 1
            if random.random() < 0.35:
                h_goals += 1
                minute = pick_minute()
                scorer = pick_scorer(h_on_pitch)
                assist = pick_assister(h_on_pitch, scorer) if random.random() < 0.65 else None
                add_event(minute, 'goal', home.id, scorer.id, assist.id if assist else None)
                scorer.goals = (scorer.goals or 0) + 1
                match_goals[scorer.id] = match_goals.get(scorer.id, 0) + 1
                if assist:
                    assist.assists = (assist.assists or 0) + 1
                    match_assists[assist.id] = match_assists.get(assist.id, 0) + 1
                
    for _ in range(total_shots_a):
        if random.random() < 0.4:
            a_sot += 1
            if random.random() < 0.30:
                a_goals += 1
                minute = pick_minute()
                scorer = pick_scorer(a_on_pitch)
                assist = pick_assister(a_on_pitch, scorer) if random.random() < 0.65 else None
                add_event(minute, 'goal', away.id, scorer.id, assist.id if assist else None)
                scorer.goals = (scorer.goals or 0) + 1
                match_goals[scorer.id] = match_goals.get(scorer.id, 0) + 1
                if assist:
                    assist.assists = (assist.assists or 0) + 1
                    match_assists[assist.id] = match_assists.get(assist.id, 0) + 1

    if random.random() < 0.2:
        side = home.id if random.random() < 0.5 else away.id
        tactic_h = db.query(Tactic).join(Manager).filter(Manager.club_id == home.id).first()
        tactic_a = db.query(Tactic).join(Manager).filter(Manager.club_id == away.id).first()
        pen_taker = tactic_h.penalty_taker_id if side == home.id and tactic_h else (tactic_a.penalty_taker_id if side == away.id and tactic_a else None)
        
        on_pitch = h_on_pitch if side == home.id else a_on_pitch
        field_players = [p for p in on_pitch if normalize_pos(p.position) != "GK"]
        if not field_players: field_players = on_pitch

        if pen_taker:
            scorer = next((p for p in on_pitch if p.id == pen_taker), None)
            if not scorer or scorer not in field_players: scorer = random.choice(field_players)
        else:
            scorer = random.choice(field_players)
            
        minute = pick_minute()
        is_goal = random.random() < 0.75
        add_event(minute, 'penalty_goal' if is_goal else 'penalty_miss', side, scorer.id)
        if side == home.id:
            total_shots_h += 1
        else:
            total_shots_a += 1
        if is_goal:
            if side == home.id:
                h_goals += 1
                h_sot += 1
            else:
                a_goals += 1
                a_sot += 1
            scorer.goals = (scorer.goals or 0) + 1
            match_goals[scorer.id] = match_goals.get(scorer.id, 0) + 1
        else:
            match_penalty_miss[scorer.id] = match_penalty_miss.get(scorer.id, 0) + 1

    if random.random() < 0.05:
        side = home.id if random.random() < 0.5 else away.id
        on_pitch = a_on_pitch if side == home.id else h_on_pitch
        defenders = [p for p in on_pitch if normalize_pos(p.position) in ["CB", "LB", "RB", "LWB", "RWB"]]
        if defenders:
            scorer = random.choice(defenders)
            minute = pick_minute()
            if side == home.id: h_goals += 1
            else: a_goals += 1
            add_event(minute, 'own_goal', side, scorer.id)
            match_own_goals[scorer.id] = match_own_goals.get(scorer.id, 0) + 1

    def get_card_weight(p):
        pos = normalize_pos(p.position)
        if pos in ["CB", "LB", "RB", "LWB", "RWB"]: return 10
        if pos in ["CM", "LM", "CDM", "RM"]: return 8
        if pos in ["CAM", "CF"]: return 6
        if pos in ["LW", "ST", "RW"]: return 4
        if pos == "GK": return 1
        return 5

    num_yellows = random.choices([0, 1, 2, 3, 4], weights=[0.25, 0.45, 0.2, 0.08, 0.02])[0]
    for _ in range(num_yellows):
        side = home.id if random.random() < 0.5 else away.id
        on_pitch = h_on_pitch if side == home.id else a_on_pitch
        if on_pitch:
            weights = [get_card_weight(p) for p in on_pitch]
            p = random.choices(on_pitch, weights=weights, k=1)[0]
            add_event(pick_minute(10, 85), 'yellow_card', side, p.id)
            match_yellow[p.id] = match_yellow.get(p.id, 0) + 1
        
    if random.random() < 0.05:
        side = home.id if random.random() < 0.5 else away.id
        on_pitch = h_on_pitch if side == home.id else a_on_pitch
        if on_pitch:
            weights = [get_card_weight(p) for p in on_pitch]
            p = random.choices(on_pitch, weights=weights, k=1)[0]
            add_event(pick_minute(20, 80), 'red_card', side, p.id)
            match_red[p.id] = match_red.get(p.id, 0) + 1
    
    num_injuries = 0
    if random.random() < 0.55:
        num_injuries = random.randint(1, 2)
    
    for _ in range(num_injuries):
        side = home.id if random.random() < 0.5 else away.id
        if side == home.id:
            pool = [p for p in h_on_pitch if p.id not in h_subs_off]
            bench = h_bench_available if h_subs_used < max_subs else []
        else:
            pool = [p for p in a_on_pitch if p.id not in a_subs_off]
            bench = a_bench_available if a_subs_used < max_subs else []
        
        if not pool:
            continue
        victim = random.choice(pool)
        pool.remove(victim)
        
        total_w = sum(i["weight"] for i in INJURY_TYPES)
        r = random.uniform(0, total_w)
        cum = 0
        chosen = INJURY_TYPES[0]
        for i in INJURY_TYPES:
            cum += i["weight"]
            if r <= cum:
                chosen = i
                break
        
        days = random.randint(max(1, chosen["min_weeks"] * 7), max(1, chosen["max_weeks"] * 7))
        
        inj_min = pick_minute(5, 88)
        
        if bench:
            replacement = random.choice(bench)
            add_event(inj_min, 'substitution', side, victim.id, replacement.id)
            add_event(inj_min, 'injury', side, victim.id)
            
            if side == home.id:
                h_subs_off[victim.id] = inj_min
                h_subs_on[replacement.id] = inj_min
                h_on_pitch.remove(victim)
                h_on_pitch.append(replacement)
                h_bench_available.remove(replacement)
                h_subs_used += 1
            else:
                a_subs_off[victim.id] = inj_min
                a_subs_on[replacement.id] = inj_min
                a_on_pitch.remove(victim)
                a_on_pitch.append(replacement)
                a_bench_available.remove(replacement)
                a_subs_used += 1
        
        if not victim.injury_weeks and not victim.injury_days:
            victim.injury_weeks = days // 7
            victim.injury_days = days % 7
            victim.injury_name = chosen["name"]
    
    target_subs_h = random.randint(3, 5)
    target_subs_a = random.randint(3, 5)
    
    def pick_substitute(on_pitch, bench, subs_off):
        available_on = [p for p in on_pitch if p.id not in subs_off]
        if not available_on or not bench: return None, None
        out_p = random.choice(available_on)
        out_pos = out_p.position
        is_gk_out = "Goalkeeper" in (out_pos or "") or out_pos == "GK"
        
        if is_gk_out:
            gk_bench = [p for p in bench if "Goalkeeper" in (p.position or "") or p.position == "GK"]
            if gk_bench:
                in_p = min(gk_bench, key=lambda p: position_penalty(p.position, out_pos, []))
                return out_p, in_p
            else:
                in_p = min(bench, key=lambda p: position_penalty(p.position, "GK", []))
                return out_p, in_p
        
        gk_bench_ids = {p.id for p in bench if "Goalkeeper" in (p.position or "") or p.position == "GK"}
        field_bench = [p for p in bench if p.id not in gk_bench_ids]
        if not field_bench:
            return out_p, random.choice(bench)
        
        in_p = min(field_bench, key=lambda p: position_penalty(p.position, out_pos, []))
        return out_p, in_p

    for _ in range(target_subs_h):
        if h_subs_used >= max_subs: break
        out_p, in_p = pick_substitute(h_on_pitch, h_bench_available, h_subs_off)
        if not out_p or not in_p: break
        sub_min = pick_minute(60, 85, is_sub=True)
        add_event(sub_min, 'substitution', home.id, out_p.id, in_p.id)
        h_subs_off[out_p.id] = sub_min
        h_subs_on[in_p.id] = sub_min
        h_on_pitch.remove(out_p)
        h_on_pitch.append(in_p)
        h_bench_available.remove(in_p)
        h_subs_used += 1
        
    for _ in range(target_subs_a):
        if a_subs_used >= max_subs: break
        out_p, in_p = pick_substitute(a_on_pitch, a_bench_available, a_subs_off)
        if not out_p or not in_p: break
        sub_min = pick_minute(60, 85, is_sub=True)
        add_event(sub_min, 'substitution', away.id, out_p.id, in_p.id)
        a_subs_off[out_p.id] = sub_min
        a_subs_on[in_p.id] = sub_min
        a_on_pitch.remove(out_p)
        a_on_pitch.append(in_p)
        a_bench_available.remove(in_p)
        a_subs_used += 1
    
    tour = db.query(Tournament).filter_by(id=fx.tournament_id).first()
    if tour and tour.type in ["Cup", "SuperCup"]:
        is_two_legged = False
        if tour.name in ["Carabao Cup", "EFL Cup"] and fx.round_number in [6, 7]:
            is_two_legged = True
        elif tour.name == "EFL Championship Playoffs" and fx.round_number in [2, 3]:
            is_two_legged = True
        elif tour.name in ["EFL League One Playoffs", "EFL League Two Playoffs"] and fx.round_number in [1, 2]:
            is_two_legged = True

        trigger_et_pens = False
        if not is_two_legged:
            if h_goals == a_goals:
                trigger_et_pens = True
        elif fx.leg == 2:
            leg1 = db.query(Fixture).filter_by(tournament_id=fx.tournament_id, round_number=fx.round_number-1, match_index=fx.match_index, leg=1).first()
            if leg1 and leg1.is_played:
                agg_home = (leg1.home_goals or 0) + a_goals
                agg_away = (leg1.away_goals or 0) + h_goals
                if agg_home == agg_away:
                    trigger_et_pens = True

        if trigger_et_pens:
            fx.has_extra_time = 1
            et_h = 1 if random.random() < 0.25 else 0
            et_a = 1 if random.random() < 0.25 else 0
            h_goals += et_h
            a_goals += et_a
            if et_h == et_a:
                fx.home_penalties = random.randint(3, 6)
                fx.away_penalties = random.randint(3, 6)
                while fx.home_penalties == fx.away_penalties:
                    fx.home_penalties += random.randint(0, 1)
                    fx.away_penalties += random.randint(0, 1)

    total_goals = h_goals + a_goals
    total_fouls_fixed = random.randint(5, 15) + random.randint(5, 15)
    num_yellow = sum(1 for e in events if e.event_type == 'yellow_card')
    num_red = sum(1 for e in events if e.event_type == 'red_card')
    num_inj = sum(1 for e in events if e.event_type == 'injury')
    
    base_1 = 1 + total_goals // 2 + num_yellow // 2 + num_red + num_inj
    base_2 = 2 + total_goals // 2 + total_fouls_fixed // 8 + num_red * 2 + num_inj * 2
    added_1st = min(10, max(0, base_1 + random.randint(-1, 1)))
    added_2nd = min(10, max(0, base_2 + random.randint(-1, 2)))
    total_match_minutes = 90 + added_1st + added_2nd

    all_player_data = []
    sub_ids = set(h_subs_on.keys()) | set(a_subs_on.keys())
    all_participants = list(h_xi) + list(a_xi)
    for p in h_bench:
        if p.id in sub_ids:
            all_participants.append(p)
    for p in a_bench:
        if p.id in sub_ids:
            all_participants.append(p)
            
    h_gk = next((p for p in h_xi if "Goalkeeper" in (p.position or "") or p.position == "GK"), None)
    a_gk = next((p for p in a_xi if "Goalkeeper" in (p.position or "") or p.position == "GK"), None)
    saves_h = max(0, a_sot - a_goals)
    saves_a = max(0, h_sot - h_goals)
    
    def calculate_rating(p, is_home_team):
        rating = 6.0
        is_gk = "Goalkeeper" in (p.position or "") or p.position == "GK"
        is_def = any(pos in (p.position or "").upper() for pos in ["CB", "LB", "RB", "LWB", "RWB", "BACK"])
        
        goals = match_goals.get(p.id, 0)
        assists = match_assists.get(p.id, 0)
        conceded = (a_goals if is_home_team else h_goals)
        saves = (saves_h if is_home_team else saves_a) if is_gk else 0
        
        if goals > 0:
            if is_gk: rating += 1.5 * goals
            elif is_def: rating += 1.5 * goals
            else: rating += 1.0 * goals
            
        rating += 0.6 * assists
        
        og = match_own_goals.get(p.id, 0)
        if og > 0: rating -= 1.5 * og
        pm = match_penalty_miss.get(p.id, 0)
        if pm > 0: rating -= 0.5 * pm
        
        if is_gk:
            rating += 0.15 * saves
            rating -= 0.3 * conceded
        elif is_def:
            rating -= 0.15 * conceded
            
        if conceded == 0 and (is_gk or is_def):
            rating += 0.5
            
        y = match_yellow.get(p.id, 0)
        r = match_red.get(p.id, 0)
        rating -= 0.4 * y
        rating -= 1.5 * r
        
        team_goals = h_goals if is_home_team else a_goals
        opp_goals = a_goals if is_home_team else h_goals
        if team_goals > opp_goals: rating += 0.3
        elif team_goals < opp_goals: rating -= 0.3
        
        variance = random.uniform(-0.3, 0.3)
        if (p.overall_rating or 50) > 80: variance *= 0.5
        rating += variance
        
        return round(max(1.0, min(10.0, rating)), 1)
    
    for p in all_participants:
        p.matches_played = (p.matches_played or 0) + 1
        p.fatigue = min(100, (p.fatigue or 0) + random.randint(20, 35))
        
        if p.id in match_yellow:
            p.consecutive_yellows = (p.consecutive_yellows or 0) + 1
            if p.consecutive_yellows >= 2:
                p.suspension_matches = (p.suspension_matches or 0) + 1
                p.consecutive_yellows = 0
        else:
            p.consecutive_yellows = 0
            
        if p.id in match_red:
            p.suspension_matches = (p.suspension_matches or 0) + random.randint(1, 2)
            p.consecutive_yellows = 0
            
        is_home = (p.club_id == home.id)
        rating = calculate_rating(p, is_home)
        
        if is_home:
            if p.id in h_subs_off:
                minutes = h_subs_off[p.id]
            elif p.id in h_subs_on:
                minutes = total_match_minutes - h_subs_on[p.id]
            else:
                minutes = total_match_minutes
        else:
            if p.id in a_subs_off:
                minutes = a_subs_off[p.id]
            elif p.id in a_subs_on:
                minutes = total_match_minutes - a_subs_on[p.id]
            else:
                minutes = total_match_minutes
        
        all_player_data.append((p, rating, minutes))

    mvp_player = None
    if all_player_data:
        max_r = max(r for _, r, _ in all_player_data)
        mvp_candidates = [p for p, r, _ in all_player_data if r == max_r]
        mvp_player = random.choice(mvp_candidates)

    for p, rating, minutes in all_player_data:
        is_mvp = 1 if (mvp_player and p.id == mvp_player.id) else 0
        mp_stat = MatchPlayerStats(fixture_id=fx.id, player_id=p.id, club_id=p.club_id, minutes_played=minutes, rating=rating, is_mvp=is_mvp)
        db.add(mp_stat)
        
    if h_goals > a_goals:
        for p in h_xi: p.morale = "green"
        for p in a_xi: p.morale = "red" if p.morale == "orange" else "orange"
    elif a_goals > h_goals:
        for p in a_xi: p.morale = "green"
        for p in h_xi: p.morale = "red" if p.morale == "orange" else "orange"

    total_shots_h = max(total_shots_h, h_goals)
    total_shots_a = max(total_shots_a, a_goals)
    h_sot = max(h_sot, h_goals)
    a_sot = max(a_sot, a_goals)
        
    if tour and tour.type == "Cup":
        is_final = False
        if tour.name == "FA Cup" and fx.round_number == 7: is_final = True
        elif tour.name in ["Carabao Cup", "EFL Cup"] and fx.round_number == 8: is_final = True
        elif "Playoffs" in tour.name:
            if tour.name == "EFL Championship Playoffs" and fx.round_number == 4: is_final = True
            elif tour.name in ["EFL League One Playoffs", "EFL League Two Playoffs"] and fx.round_number == 3: is_final = True
        
        if is_final:
            winner_id = None
            if fx.home_penalties is not None and fx.away_penalties is not None:
                winner_id = fx.home_club_id if fx.home_penalties > fx.away_penalties else fx.away_club_id
            else:
                winner_id = fx.home_club_id if h_goals > a_goals else fx.away_club_id
                if h_goals == a_goals: winner_id = None
            
            if winner_id:
                state = db.query(GameState).first()
                season_str = state.season if state else "2026/27"
                if not db.query(Trophy).filter_by(club_id=winner_id, tournament_name=tour.name, season=season_str).first():
                    db.add(Trophy(club_id=winner_id, tournament_name=tour.name, season=season_str))
                if tour.name == "FA Cup":
                    shield_tour = db.query(Tournament).filter_by(name="FA Community Shield").first()
                    pl_tour = db.query(Tournament).filter_by(name="Premier League").first()
                    if shield_tour and pl_tour:
                        season_start_year = int(season_str.split("/")[0])
                        season_end_year = season_start_year + 1
                        pl_clubs = db.query(Club).filter(Club.league == "Premier League").all()
                        pl_fixtures = db.query(Fixture).filter(
                            Fixture.tournament_id == pl_tour.id,
                            Fixture.is_played == 1,
                            Fixture.date >= f"{season_start_year}-07-01",
                            Fixture.date <= f"{season_end_year}-06-30"
                        ).all()
                        pl_stats = {c.id: {"club": c, "pts": 0, "gd": 0, "gf": 0} for c in pl_clubs}
                        for pf in pl_fixtures:
                            if pf.home_club_id in pl_stats and pf.away_club_id in pl_stats:
                                h_s = pl_stats[pf.home_club_id]
                                a_s = pl_stats[pf.away_club_id]
                                h_s["gf"] += pf.home_goals
                                a_s["gf"] += pf.away_goals
                                h_s["gd"] += pf.home_goals - pf.away_goals
                                a_s["gd"] += pf.away_goals - pf.home_goals
                                if pf.home_goals > pf.away_goals: h_s["pts"] += 3
                                elif pf.home_goals < pf.away_goals: a_s["pts"] += 3
                                else:
                                    h_s["pts"] += 1
                                    a_s["pts"] += 1
                        pl_sorted = sorted(pl_stats.values(), key=lambda x: (-x["pts"], -x["gd"], -x["gf"]))
                        if pl_sorted and pl_sorted[0]["pts"] > 0:
                            pl_winner_id = pl_sorted[0]["club"].id
                            shield_date = f"{season_end_year}-06-09"
                            existing_shield = db.query(Fixture).filter(
                                Fixture.tournament_id == shield_tour.id,
                                Fixture.date >= f"{season_start_year}-07-01",
                                Fixture.date <= f"{season_end_year}-06-30"
                            ).first()
                            if existing_shield:
                                existing_shield.home_club_id = pl_winner_id
                                existing_shield.away_club_id = winner_id
                                existing_shield.date = shield_date
                                existing_shield.is_played = 0
                                existing_shield.home_goals = None
                                existing_shield.away_goals = None
                                existing_shield.home_penalties = None
                                existing_shield.away_penalties = None
                                existing_shield.has_extra_time = 0
                            else:
                                db.add(Fixture(
                                    date=shield_date,
                                    tournament_id=shield_tour.id,
                                    round_number=1,
                                    match_index=0,
                                    leg=1,
                                    home_club_id=pl_winner_id,
                                    away_club_id=winner_id,
                                    is_played=0
                                ))
                            for cid in [pl_winner_id, winner_id]:
                                if not db.query(ClubTournament).filter_by(club_id=cid, tournament_id=shield_tour.id, season=season_str).first():
                                    db.add(ClubTournament(club_id=cid, tournament_id=shield_tour.id, season=season_str))

    fx.home_goals = h_goals
    fx.away_goals = a_goals
    fx.is_played = 1
    fx.home_poss = random.randint(35, 65)
    fx.away_poss = 100 - fx.home_poss
    fx.home_shots = total_shots_h
    fx.away_shots = total_shots_a
    fx.home_sot = h_sot
    fx.away_sot = a_sot
    fx.home_fouls = random.randint(5, 15)
    fx.away_fouls = random.randint(5, 15)
    fx.home_corners = random.randint(2, 10)
    fx.away_corners = random.randint(2, 10)
    fx.home_offsides = random.randint(0, 4)
    fx.away_offsides = random.randint(0, 4)
    fx.home_xg = round(h_sot * random.uniform(0.1, 0.4) + h_goals * 0.15, 2)
    fx.away_xg = round(a_sot * random.uniform(0.1, 0.4) + a_goals * 0.15, 2)
    fx.first_half_added = added_1st
    fx.second_half_added = added_2nd
    
    for ev in events: db.add(ev)
    db.flush()
    
    advance_cup_bracket(fx, db)

def populate_playoffs(db, year):
    def get_standings(league_name):
        tour = db.query(Tournament).filter_by(name=league_name).first()
        if not tour: return []
        clubs = db.query(Club).filter(Club.league == league_name).all()
        fixtures = db.query(Fixture).filter_by(tournament_id=tour.id, is_played=1).filter(Fixture.date >= f"{year}-07-01", Fixture.date <= f"{year+1}-06-30").all()
        stats = {c.id: {"club": c, "pts": 0, "gd": 0, "gf": 0} for c in clubs}
        for f in fixtures:
            if f.home_club_id in stats and f.away_club_id in stats:
                h, a = stats[f.home_club_id], stats[f.away_club_id]
                h["gf"] += f.home_goals; a["gf"] += f.away_goals
                h["gd"] += f.home_goals - f.away_goals; a["gd"] += f.away_goals - f.home_goals
                if f.home_goals > f.away_goals: h["pts"] += 3
                elif f.home_goals < f.away_goals: a["pts"] += 3
                else: h["pts"] += 1; a["pts"] += 1
        return sorted(stats.values(), key=lambda x: (-x["pts"], -x["gd"], -x["gf"]))

    st_champ = get_standings("EFL Championship")
    if len(st_champ) >= 8:
        po_tour = db.query(Tournament).filter_by(name="EFL Championship Playoffs").first()
        if po_tour:
            p3, p4, p5, p6, p7, p8 = st_champ[2]["club"], st_champ[3]["club"], st_champ[4]["club"], st_champ[5]["club"], st_champ[6]["club"], st_champ[7]["club"]
            fx1 = db.query(Fixture).filter_by(tournament_id=po_tour.id, round_number=1, match_index=0).first()
            fx2 = db.query(Fixture).filter_by(tournament_id=po_tour.id, round_number=1, match_index=1).first()
            if fx1: fx1.home_club_id = p5.id; fx1.away_club_id = p8.id
            if fx2: fx2.home_club_id = p6.id; fx2.away_club_id = p7.id
            sf1 = db.query(Fixture).filter_by(tournament_id=po_tour.id, round_number=2, match_index=0).first()
            sf2 = db.query(Fixture).filter_by(tournament_id=po_tour.id, round_number=2, match_index=1).first()
            if sf1: sf1.home_club_id = p3.id
            if sf2: sf2.home_club_id = p4.id
            for c in [p3, p4, p5, p6, p7, p8]:
                if not db.query(ClubTournament).filter_by(club_id=c.id, tournament_id=po_tour.id).first():
                    db.add(ClubTournament(club_id=c.id, tournament_id=po_tour.id))
            db.commit()

    st_l1 = get_standings("EFL League One")
    if len(st_l1) >= 6:
        po_tour = db.query(Tournament).filter_by(name="EFL League One Playoffs").first()
        if po_tour:
            p3, p4, p5, p6 = st_l1[2]["club"], st_l1[3]["club"], st_l1[4]["club"], st_l1[5]["club"]
            fx1 = db.query(Fixture).filter_by(tournament_id=po_tour.id, round_number=1, match_index=0).first()
            fx2 = db.query(Fixture).filter_by(tournament_id=po_tour.id, round_number=1, match_index=1).first()
            if fx1: fx1.home_club_id = p3.id; fx1.away_club_id = p6.id
            if fx2: fx2.home_club_id = p4.id; fx2.away_club_id = p5.id
            for c in [p3, p4, p5, p6]:
                if not db.query(ClubTournament).filter_by(club_id=c.id, tournament_id=po_tour.id).first():
                    db.add(ClubTournament(club_id=c.id, tournament_id=po_tour.id))
            db.commit()

    st_l2 = get_standings("EFL League Two")
    if len(st_l2) >= 7:
        po_tour = db.query(Tournament).filter_by(name="EFL League Two Playoffs").first()
        if po_tour:
            p4, p5, p6, p7 = st_l2[3]["club"], st_l2[4]["club"], st_l2[5]["club"], st_l2[6]["club"]
            fx1 = db.query(Fixture).filter_by(tournament_id=po_tour.id, round_number=1, match_index=0).first()
            fx2 = db.query(Fixture).filter_by(tournament_id=po_tour.id, round_number=1, match_index=1).first()
            if fx1: fx1.home_club_id = p4.id; fx1.away_club_id = p7.id
            if fx2: fx2.home_club_id = p5.id; fx2.away_club_id = p6.id
            for c in [p4, p5, p6, p7]:
                if not db.query(ClubTournament).filter_by(club_id=c.id, tournament_id=po_tour.id).first():
                    db.add(ClubTournament(club_id=c.id, tournament_id=po_tour.id))
            db.commit()

def process_season_end(db, year):
    fa_cup = db.query(Tournament).filter_by(name="FA Cup").first()
    def get_league_standings(league_name):
        tour = db.query(Tournament).filter_by(name=league_name).first()
        if not tour: return []
        clubs = db.query(Club).filter(Club.league == league_name).all()
        fixtures = db.query(Fixture).filter_by(tournament_id=tour.id, is_played=1).filter(
            Fixture.date >= f"{year}-07-01", Fixture.date <= f"{year+1}-06-30"
        ).all()
        stats = {c.id: {"club": c, "pts": 0, "gf": 0, "ga": 0, "gd": 0} for c in clubs}
        for f in fixtures:
            if f.home_club_id in stats and f.away_club_id in stats:
                h, a = stats[f.home_club_id], stats[f.away_club_id]
                h["gf"] += f.home_goals; a["gf"] += f.away_goals
                h["ga"] += f.away_goals; a["ga"] += f.home_goals
                if f.home_goals > f.away_goals: h["pts"] += 3
                elif f.home_goals < f.away_goals: a["pts"] += 3
                else: h["pts"] += 1; a["pts"] += 1
        for s in stats.values():
            s["gd"] = s["gf"] - s["ga"]
        standings = sorted(stats.values(), key=lambda x: (-x["pts"], -x["gd"], -x["gf"]))
        return standings

    pl_standings = get_league_standings("Premier League")
    champ_standings = get_league_standings("EFL Championship")
    l1_standings = get_league_standings("EFL League One")
    l2_standings = get_league_standings("EFL League Two")
    
    def get_playoff_winner(po_name, final_round):
        po_tour = db.query(Tournament).filter_by(name=po_name).first()
        if not po_tour: return None
        final_fx = db.query(Fixture).filter_by(tournament_id=po_tour.id, round_number=final_round).first()
        if final_fx and final_fx.is_played:
            if final_fx.home_penalties is not None and final_fx.away_penalties is not None:
                winner_id = final_fx.home_club_id if final_fx.home_penalties > final_fx.away_penalties else final_fx.away_club_id
            else:
                winner_id = final_fx.home_club_id if final_fx.home_goals > final_fx.away_goals else final_fx.away_club_id
            return db.query(Club).get(winner_id)
        return None

    pl_relegated = [s["club"] for s in pl_standings[-3:]] if len(pl_standings) >= 3 else []
    champ_promoted = [s["club"] for s in champ_standings[:2]]
    champ_po = get_playoff_winner("EFL Championship Playoffs", 4)
    if champ_po: champ_promoted.append(champ_po)
    
    champ_relegated = [s["club"] for s in champ_standings[-3:]] if len(champ_standings) >= 3 else []
    l1_promoted = [s["club"] for s in l1_standings[:2]]
    l1_po = get_playoff_winner("EFL League One Playoffs", 3)
    if l1_po: l1_promoted.append(l1_po)
    
    l1_relegated = [s["club"] for s in l1_standings[-4:]] if len(l1_standings) >= 4 else []
    l2_promoted = [s["club"] for s in l2_standings[:3]]
    l2_po = get_playoff_winner("EFL League Two Playoffs", 3)
    if l2_po: l2_promoted.append(l2_po)

    def update_club_tournament(club, new_league_name):
        if not club: return
        club.league = new_league_name
        new_tour = db.query(Tournament).filter_by(name=new_league_name).first()
        if new_tour:
            league_tours = ["Premier League", "EFL Championship", "EFL League One", "EFL League Two", 
                            "EFL Championship Playoffs", "EFL League One Playoffs", "EFL League Two Playoffs"]
            old_tours = db.query(Tournament).filter(Tournament.name.in_(league_tours)).all()
            old_tour_ids = [t.id for t in old_tours]
            db.query(ClubTournament).filter(ClubTournament.club_id == club.id, ClubTournament.tournament_id.in_(old_tour_ids)).delete(synchronize_session=False)
            db.add(ClubTournament(club_id=club.id, tournament_id=new_tour.id))

    for c in pl_relegated: update_club_tournament(c, "EFL Championship")
    for c in champ_promoted: update_club_tournament(c, "Premier League")
    for c in champ_relegated: update_club_tournament(c, "EFL League One")
    for c in l1_promoted: update_club_tournament(c, "EFL Championship")
    for c in l1_relegated: update_club_tournament(c, "EFL League Two")
    for c in l2_promoted: update_club_tournament(c, "EFL League One")
    def award_trophy(club, tour_name):
        if not club: return
        season_str = f"{year}/{year+1}"
        if not db.query(Trophy).filter_by(club_id=club.id, tournament_name=tour_name, season=season_str).first():
            db.add(Trophy(club_id=club.id, tournament_name=tour_name, season=season_str))

    if pl_standings: award_trophy(pl_standings[0]["club"], "Premier League")
    if champ_standings: award_trophy(champ_standings[0]["club"], "EFL Championship")
    if l1_standings: award_trophy(l1_standings[0]["club"], "EFL League One")
    if l2_standings: award_trophy(l2_standings[0]["club"], "EFL League Two")
    
    if fa_cup:
        fa_final = db.query(Fixture).filter_by(tournament_id=fa_cup.id, round_number=7).first()
        if fa_final and fa_final.is_played:
            if fa_final.home_penalties is not None:
                fa_win_id = fa_final.home_club_id if fa_final.home_penalties > fa_final.away_penalties else fa_final.away_club_id
            else:
                fa_win_id = fa_final.home_club_id if (fa_final.home_goals or 0) > (fa_final.away_goals or 0) else fa_final.away_club_id
            fa_winner = db.query(Club).get(fa_win_id)
            award_trophy(fa_winner, "FA Cup")

    carabao = db.query(Tournament).filter(Tournament.name.in_(["Carabao Cup", "EFL Cup"])).first()
    if carabao:
        car_final = db.query(Fixture).filter_by(tournament_id=carabao.id, round_number=8).first()
        if car_final and car_final.is_played:
            if car_final.home_penalties is not None:
                car_win_id = car_final.home_club_id if car_final.home_penalties > car_final.away_penalties else car_final.away_club_id
            else:
                car_win_id = car_final.home_club_id if (car_final.home_goals or 0) > (car_final.away_goals or 0) else car_final.away_club_id
            car_winner = db.query(Club).get(car_win_id)
            award_trophy(car_winner, "EFL Cup")

    db.commit()

    shield = db.query(Tournament).filter_by(name="FA Community Shield").first()
    if fa_cup and shield and len(pl_standings) > 0:
        fa_final = db.query(Fixture).filter_by(tournament_id=fa_cup.id, round_number=7).first()
        pl_winner = pl_standings[0]["club"]
        if fa_final and fa_final.is_played:
            if fa_final.home_penalties is not None and fa_final.away_penalties is not None:
                fa_winner_id = fa_final.home_club_id if fa_final.home_penalties > fa_final.away_penalties else fa_final.away_club_id
            else:
                fa_winner_id = fa_final.home_club_id if (fa_final.home_goals or 0) > (fa_final.away_goals or 0) else fa_final.away_club_id
            fa_winner = db.query(Club).get(fa_winner_id)
            
            if pl_winner and fa_winner:
                shield_fx = db.query(Fixture).filter_by(tournament_id=shield.id).first()
                if shield_fx:
                    shield_fx.home_club_id = pl_winner.id
                    shield_fx.away_club_id = fa_winner.id
                    db.commit()

def advance_game_date(db, days_to_add):
    with db_lock:
        state = db.query(GameState).first()
        if not state: return None
        curr = datetime.strptime(state.current_date, "%Y-%m-%d").date()
        
        for _ in range(days_to_add):
            curr += timedelta(days=1)
            date_str = curr.strftime("%Y-%m-%d")
            
            if curr.month == 5 and curr.day == 9:
                populate_playoffs(db, curr.year - 1)

            if curr.month == 7 and curr.day == 1:
                try:
                    process_season_end(db, curr.year - 1)
                except Exception as e:
                    print("Season end error:", e)
                    db.rollback()
                
                db.query(Player).update({
                    Player.goals: 0, Player.assists: 0, Player.matches_played: 0,
                    Player.rating_sum: 0.0, Player.consecutive_yellows: 0, 
                    Player.suspension_matches: 0, Player.fatigue: 0,
                    Player.training_program_id: None, Player.training_started_at: None,
                    Player.season_start_ovr: Player.overall_rating,
                    Player.age: Player.age + 1
                }, synchronize_session=False)
                
                state.season = f"{curr.year}/{curr.year+1}"
                try:
                    generate_season_fixtures(db, curr.year)
                except Exception as e:
                    print("Season generate error:", e)
                    db.rollback()

            db.execute(text("""
                UPDATE players
                SET injury_days = injury_days - 1
                WHERE injury_days > 0
            """))
            db.execute(text("""
                UPDATE players
                SET injury_weeks = injury_weeks - 1, injury_days = 6
                WHERE injury_days = 0 AND injury_weeks > 0
            """))
            db.execute(text("""
                UPDATE players
                SET injury_name = NULL
                WHERE injury_days = 0 AND injury_weeks = 0
            """))
            
            fixtures = db.query(Fixture).filter(Fixture.date == date_str, Fixture.is_played == 0).all()
            for fx in fixtures:
                try:
                    simulate_match(fx.id, db)
                except Exception as e:
                    print(f"Match simulation failed for fixture {fx.id}: {e}")
                    db.rollback()
                    fx_db = db.query(Fixture).filter_by(id=fx.id).first()
                    if fx_db:
                        fx_db.is_played = 1
                        fx_db.home_goals = 0
                        fx_db.away_goals = 0
                        db.commit()
            
            db.execute(text("""
                UPDATE players
                SET fatigue = GREATEST(0, fatigue - 15),
                    fitness = CASE
                        WHEN GREATEST(0, fatigue - 15) > 80 THEN 'red'
                        WHEN GREATEST(0, fatigue - 15) > 60 THEN 'orange'
                        WHEN GREATEST(0, fatigue - 15) > 40 THEN 'yellow'
                        ELSE 'green'
                    END,
                    suspension_matches = CASE WHEN suspension_matches > 0 THEN suspension_matches - 1 ELSE 0 END
                WHERE fatigue > 0 OR suspension_matches > 0
            """))
            
            if curr.weekday() == 6:
                all_players = db.query(Player).all()
                for p in all_players:
                    decline_age = 33 + (p.id % 3)
                    growth_chance = 0
                    if p.age < 24: growth_chance = 0.05
                    elif p.age <= 29: growth_chance = 0.01
                        
                    if p.training_program_id:
                        prog = db.query(TrainingProgram).filter_by(id=p.training_program_id).first()
                        if prog:
                            p.growth_progress = (p.growth_progress or 0) + random.randint(10, 25)
                            if p.growth_progress >= 100:
                                p.growth_progress = 0
                                if prog.stat_boosts:
                                    boosts = json.loads(prog.stat_boosts)
                                    for stat, val in boosts.items():
                                        if hasattr(p, stat):
                                            setattr(p, stat, min(99, getattr(p, stat) + 1))
                                            
                    if p.age < 30 and p.overall_rating < (p.potential or 99) and random.random() < growth_chance:
                        stats_pool = ["pace", "shooting", "passing", "dribbling", "defending", "physicality"]
                        if "Goalkeeper" in p.position or p.position == "GK":
                            stats_pool = ["gk_reflexes", "gk_handling", "gk_positioning", "gk_diving"]
                        chosen_stat = random.choice(stats_pool)
                        setattr(p, chosen_stat, min(99, getattr(p, chosen_stat) + 1))
                    elif p.age >= decline_age and random.random() < 0.15:
                        new_ovr = recalculate_overall(p)
                        if new_ovr > ((p.season_start_ovr or p.overall_rating) - 9):
                            stats_pool = ["pace", "physicality"]
                            chosen_stat = random.choice(stats_pool)
                            setattr(p, chosen_stat, max(1, getattr(p, chosen_stat) - 1))
                            
                    new_ovr = recalculate_overall(p)
                    if new_ovr != p.overall_rating:
                        p.overall_rating = new_ovr
                        p.market_value = recalculate_market_value(p)

            state.current_date = curr.strftime("%Y-%m-%d")
            db.commit()
            
        state.last_month_advance_at = datetime.utcnow()
        db.commit()
        return state.current_date

@app.post("/api/admin/advance-month")
def advance_month(req: dict):
    tg_id = req.get("telegram_id")
    if tg_id != ADMIN_TELEGRAM_ID: raise HTTPException(status_code=403, detail="Нет прав")
    
    db = Session(engine)
    try:
        state = db.query(GameState).first()
        if not state: return {"status": "error"}
        
        curr = datetime.strptime(state.current_date, "%Y-%m-%d").date()
        last_day = calendar.monthrange(curr.year, curr.month)[1]
        
        if curr.day == last_day:
            if curr.month == 12: next_month = date(curr.year + 1, 1, 1)
            else: next_month = date(curr.year, curr.month + 1, 1)
            next_month_last_day = calendar.monthrange(next_month.year, next_month.month)[1]
            new_date = date(next_month.year, next_month.month, next_month_last_day)
        else:
            new_date = date(curr.year, curr.month, last_day)
            
        delta_days = (new_date - curr).days
        advance_game_date(db, delta_days)
        return {"status": "ok", "new_date": db.query(GameState).first().current_date}
    finally:
        db.close()

@app.get("/api/tournaments/{tournament_id}/rounds")
def get_tournament_rounds(tournament_id: int, season: str = None):
    db = Session(engine)
    try:
        if not season:
            state = db.query(GameState).first()
            season = state.season if state else "2026/27"
        season_start_year = int(season.split("/")[0])
        start_str = f"{season_start_year}-07-01"
        end_str = f"{season_start_year+1}-06-30"
        rounds = db.query(Fixture.round_number).filter(
            Fixture.tournament_id == tournament_id,
            Fixture.date >= start_str,
            Fixture.date <= end_str
        ).distinct().order_by(Fixture.round_number).all()
        return [r[0] for r in rounds]
    finally:
        db.close()

@app.get("/api/tournaments/{tournament_id}/rounds/{round_number}")
def get_round_matches(tournament_id: int, round_number: int, season: str = None):
    db = Session(engine)
    try:
        if not season:
            state = db.query(GameState).first()
            season = state.season if state else "2026/27"
        season_start_year = int(season.split("/")[0])
        start_str = f"{season_start_year}-07-01"
        end_str = f"{season_start_year+1}-06-30"
        fixtures = db.query(Fixture).filter(
            Fixture.tournament_id == tournament_id,
            Fixture.round_number == round_number,
            Fixture.date >= start_str,
            Fixture.date <= end_str
        ).all()
        result = []
        for f in fixtures:
            h = db.query(Club).filter_by(id=f.home_club_id).first()
            a = db.query(Club).filter_by(id=f.away_club_id).first()
            result.append({
                "id": f.id, "date": f.date, "is_played": bool(f.is_played),
                "home_name": h.name if h else "", "away_name": a.name if a else "",
                "home_goals": f.home_goals, "away_goals": f.away_goals
            })
        return result
    finally:
        db.close()

@app.get("/api/match/{fixture_id}")
def get_match_details(fixture_id: int):
    db = Session(engine)
    try:
        fx = db.query(Fixture).filter_by(id=fixture_id).first()
        if not fx: raise HTTPException(status_code=404, detail="Матч не найден")
        home = db.query(Club).filter_by(id=fx.home_club_id).first()
        away = db.query(Club).filter_by(id=fx.away_club_id).first()
        tour = db.query(Tournament).filter_by(id=fx.tournament_id).first()
        
        events = db.query(MatchEvent).filter_by(fixture_id=fx.id).order_by(MatchEvent.minute).all()
        _pids = set()
        for e in events:
            if e.player_id: _pids.add(e.player_id)
            if e.assist_id: _pids.add(e.assist_id)
        _players_map = {p.id: p for p in db.query(Player).filter(Player.id.in_(_pids)).all()} if _pids else {}
        events_data = []
        for e in events:
            p = _players_map.get(e.player_id)
            a = _players_map.get(e.assist_id) if e.assist_id else None
            events_data.append({
                "minute": e.minute, "type": e.event_type, "club_id": e.club_id,
                "player": p.name if p else "", "assist": a.name if a else ""
            })
            
        h_yellow = sum(1 for e in events if e.event_type == 'yellow_card' and e.club_id == fx.home_club_id)
        a_yellow = sum(1 for e in events if e.event_type == 'yellow_card' and e.club_id == fx.away_club_id)
        h_red = sum(1 for e in events if e.event_type == 'red_card' and e.club_id == fx.home_club_id)
        a_red = sum(1 for e in events if e.event_type == 'red_card' and e.club_id == fx.away_club_id)
        h_subs = sum(1 for e in events if e.event_type == 'substitution' and e.club_id == fx.home_club_id)
        a_subs = sum(1 for e in events if e.event_type == 'substitution' and e.club_id == fx.away_club_id)
        h_pens = sum(1 for e in events if e.event_type in ('penalty_goal', 'penalty_miss') and e.club_id == fx.home_club_id)
        a_pens = sum(1 for e in events if e.event_type in ('penalty_goal', 'penalty_miss') and e.club_id == fx.away_club_id)
        
        return {
            "id": fx.id, "date": fx.date, "is_played": bool(fx.is_played),
            "home_club": home.name if home else "TBD", "away_club": away.name if away else "TBD",
            "home_club_id": fx.home_club_id, "away_club_id": fx.away_club_id,
            "home_goals": fx.home_goals, "away_goals": fx.away_goals,
            "home_poss": fx.home_poss, "away_poss": fx.away_poss,
            "home_shots": fx.home_shots, "away_shots": fx.away_shots,
            "home_sot": fx.home_sot, "away_sot": fx.away_sot,
            "home_fouls": fx.home_fouls, "away_fouls": fx.away_fouls,
            "home_corners": fx.home_corners, "away_corners": fx.away_corners,
            "home_offsides": fx.home_offsides, "away_offsides": fx.away_offsides,
            "home_xg": fx.home_xg or 0.0, "away_xg": fx.away_xg or 0.0,
            "first_half_added": fx.first_half_added or 0,
            "second_half_added": fx.second_half_added or 0,
            "has_extra_time": fx.has_extra_time or 0,
            "home_penalties": fx.home_penalties,
            "away_penalties": fx.away_penalties,
            "home_yellow": h_yellow, "away_yellow": a_yellow,
            "home_red": h_red, "away_red": a_red,
            "home_subs": h_subs, "away_subs": a_subs,
            "home_pens": h_pens, "away_pens": a_pens,
            "tournament": tour.name if tour else "",
            "round_number": fx.round_number,
            "leg": fx.leg,
            "type": tour.type if tour else "League",
            "events": events_data
        }
    finally:
        db.close()

@dp.message(Command("day"))
async def cmd_admin_day(message: types.Message):
    if str(message.from_user.id) != ADMIN_TELEGRAM_ID:
        await message.answer("⛔ У вас нет прав.")
        return
    def do_work():
        db = Session(engine)
        try:
            return advance_game_date(db, 1)
        finally:
            db.close()
    new_date = await asyncio.to_thread(do_work)
    await message.answer(f"⏩ Промотан 1 день. Дата: {new_date}")

@dp.message(Command("week"))
async def cmd_admin_week(message: types.Message):
    if str(message.from_user.id) != ADMIN_TELEGRAM_ID:
        await message.answer("⛔ У вас нет прав.")
        return
    def do_work():
        db = Session(engine)
        try:
            state = db.query(GameState).first()
            if not state: return None
            curr = datetime.strptime(state.current_date, "%Y-%m-%d").date()
            days_to_sunday = 6 - curr.weekday()
            if days_to_sunday == 0: days_to_sunday = 7
            return advance_game_date(db, days_to_sunday)
        finally:
            db.close()
    new_date = await asyncio.to_thread(do_work)
    if new_date:
        await message.answer(f"⏩ Промотано до конца недели. Дата: {new_date}")
    else:
        await message.answer("❌ Ошибка: состояние игры не найдено")

@dp.message(Command("month"))
async def cmd_admin_month(message: types.Message):
    if str(message.from_user.id) != ADMIN_TELEGRAM_ID:
        await message.answer("⛔ У вас нет прав.")
        return
    def do_work():
        db = Session(engine)
        try:
            state = db.query(GameState).first()
            if not state: return None
            curr = datetime.strptime(state.current_date, "%Y-%m-%d").date()
            last_day = calendar.monthrange(curr.year, curr.month)[1]
            if curr.day == last_day:
                if curr.month == 12: next_month = date(curr.year + 1, 1, 1)
                else: next_month = date(curr.year, curr.month + 1, 1)
                next_month_last_day = calendar.monthrange(next_month.year, next_month.month)[1]
                new_date = date(next_month.year, next_month.month, next_month_last_day)
            else:
                new_date = date(curr.year, curr.month, last_day)
            delta_days = (new_date - curr).days
            return advance_game_date(db, delta_days)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"ERROR: {e}"
        finally:
            db.close()
    await message.answer("⏳ Промотка...")
    try:
        result = await asyncio.to_thread(do_work)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        return
    if isinstance(result, str) and result.startswith("ERROR:"):
        await message.answer(f"❌ {result}")
    elif result:
        await message.answer(f"⏩ Промотан месяц. Дата: {result}")
    else:
        await message.answer("❌ Ошибка: состояние игры не найдено")

@dp.message(Command("date"))
async def cmd_admin_date(message: types.Message, command: CommandObject):
    if str(message.from_user.id) != ADMIN_TELEGRAM_ID:
        await message.answer("⛔ У вас нет прав.")
        return
    if not command.args:
        await message.answer("⚠️ Укажите дату: /date 2026-09-15")
        return
    try:
        target = datetime.strptime(command.args.strip(), "%Y-%m-%d").date()
    except ValueError:
        await message.answer("⚠️ Неверный формат. Используйте ГГГГ-ММ-ДД.")
        return
    def do_work():
        db = Session(engine)
        try:
            state = db.query(GameState).first()
            if not state: return None
            curr = datetime.strptime(state.current_date, "%Y-%m-%d").date()
            if target < curr: return "past"
            return advance_game_date(db, (target - curr).days)
        finally:
            db.close()
    result = await asyncio.to_thread(do_work)
    if result == "past":
        await message.answer("⚠️ Нельзя промотать время назад.")
    elif result:
        await message.answer(f"⏩ Установлена дата: {result}")
    else:
        await message.answer("❌ Ошибка")

@dp.message(Command("reset"))
async def cmd_admin_reset(message: types.Message):
    if str(message.from_user.id) != ADMIN_TELEGRAM_ID:
        await message.answer("⛔ У вас нет прав.")
        return
    
    with db_lock:
        db = Session(engine)
        try:
            db.execute(text("DELETE FROM match_events"))
            db.execute(text("DELETE FROM match_player_stats"))
            db.execute(text("DELETE FROM fixtures"))
            db.execute(text("DELETE FROM tactics"))
            db.execute(text("DELETE FROM managers"))
            db.execute(text("DELETE FROM trophies"))
            db.execute(text("DELETE FROM club_tournaments"))
            db.execute(text("UPDATE clubs SET league = original_league"))
            db.commit()
            
            players = db.query(Player).all()
            for p in players:
                if p.original_data:
                    try:
                        orig = json.loads(p.original_data)
                        for k, v in orig.items():
                            setattr(p, k, v)
                    except Exception:
                        pass
                p.goals = 0
                p.assists = 0
                p.matches_played = 0
                p.rating_sum = 0.0
                p.fatigue = 0
                p.injury_weeks = 0
                p.injury_days = 0
                p.injury_name = None
                p.fitness = "green"
                p.morale = "green"
                p.consecutive_yellows = 0
                p.suspension_matches = 0
                p.training_program_id = None
                p.training_started_at = None
                p.growth_progress = 0
                p.season_start_ovr = p.overall_rating
                p.alt_positions = "[]"
            db.commit()
            
            state = db.query(GameState).first()
            if state:
                state.current_date = "2026-08-01"
                state.season = "2026/27"
                state.last_month_advance_at = datetime.utcnow()
                
            db.commit()
            init_db()
            await message.answer("💥 Карьера полностью сброшена! Время вернулось на 01.08.2026.")
        except Exception as e:
            db.rollback()
            await message.answer(f"❌ Ошибка: {e}")
        finally:
            db.close()

@app.get("/api/admin/fix-db-999")
def fix_db_999():
    import csv
    from datetime import datetime
    import random
    db = Session(engine)
    try:
        backup_players = []
        for p in db.query(Player).all():
            p_dict = {k: v for k, v in p.__dict__.items() if not k.startswith('_')}
            backup_players.append(p_dict)
        
        db.execute(text("DELETE FROM match_events"))
        db.execute(text("DELETE FROM match_player_stats"))
        db.execute(text("DELETE FROM tactics"))
        db.query(Player).delete()
        db.commit()
        
        if not os.path.exists("players.csv"):
            return {"status": "error", "message": "players.csv not found on server!"}
            
        count = 0
        csv_player_ids = set()
        with open("players.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('gender') != "Men's Football": continue
                if row.get('league') in ['UEFA Champions League', 'FIFA World Cup', 'European Championship']: continue
                if not row.get('club'): continue
                
                try:
                    pid = int(float(row['player_id']))
                except:
                    continue
                    
                if pid in csv_player_ids: continue
                csv_player_ids.add(pid)
                
                club_name = str(row['club']).strip()
                club = db.query(Club).filter_by(name=club_name).first()
                if not club:
                    club = Club(name=club_name, league=str(row.get('league', 'Unknown')).strip())
                    db.add(club)
                    db.commit()
                    db.refresh(club)
                
                name = str(row['common_name']).strip() if row.get('common_name') else f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
                age = 0
                if row.get('birthdate'):
                    try: age = 2026 - datetime.strptime(row['birthdate'], '%d-%m-%Y').year
                    except: pass
                    
                def get_val(col):
                    val = row.get(col)
                    try: return int(float(val))
                    except: return 0
                    
                p = Player(
                    player_id=pid,
                    name=name, position=str(row.get('position', 'CM')), overall_rating=int(float(row.get('overall_rating', 50))),
                    age=age, nationality=str(row.get('nationality', 'Unknown')), club_id=club.id,
                    preferred_foot=str(row.get('preferred_foot', 'Right')),
                    pace=get_val('pace'), shooting=get_val('shooting'), passing=get_val('passing'),
                    dribbling=get_val('dribbling'), defending=get_val('defending'), physicality=get_val('physicality'),
                    gk_diving=get_val('goalkeeping_diving'), gk_handling=get_val('goalkeeping_handling'),
                    gk_kicking=get_val('goalkeeping_kicking'), gk_positioning=get_val('goalkeeping_positioning'),
                    gk_reflexes=get_val('goalkeeping_reflexes')
                )
                db.add(p)
                count += 1
                if count % 1000 == 0:
                    db.commit()
        db.commit()
        
        existing_ids = {p[0] for p in db.query(Player.player_id).all() if p[0] is not None}
        added_backup_ids = set()
        for b in backup_players:
            try:
                pid = int(b['player_id'])
            except:
                continue
            if pid not in csv_player_ids and pid not in added_backup_ids and pid not in existing_ids:
                added_backup_ids.add(pid)
                del b['id']
                if 'original_data' in b: del b['original_data']
                db.add(Player(**b))
        db.commit()
        
        players_with_clubs = db.query(Player, Club).join(Club, Player.club_id == Club.id).all()
        for p, club in players_with_clubs:
            ovr = p.overall_rating or 50
            age = p.age or 25
            pos = p.position or ""
            
            base_val = int((ovr ** 4) / 5)
            
            l = club.league.lower() if club.league else ""
            if "premier league" in l or "laliga" in l or "la liga" in l: mult_league = 1.5
            elif "bundesliga" in l or "serie a" in l or "ligue 1" in l: mult_league = 1.2
            elif "championship" in l or "eredivisie" in l or "portugal" in l or "mls" in l or "saudi" in l: mult_league = 0.7
            else: mult_league = 0.2

            if "Goalkeeper" in pos: mult_pos = 0.4
            elif "Back" in pos: mult_pos = 1.0
            elif "Midfield" in pos: mult_pos = 1.1
            else: mult_pos = 1.3 

            if age <= 21: mult_age = 2.0
            elif age <= 24: mult_age = 1.5
            elif age <= 27: mult_age = 1.2
            elif age <= 30: mult_age = 1.0
            elif age <= 33: mult_age = 0.8
            elif age <= 35: mult_age = 0.6
            else: mult_age = 0.4

            market_value = int(base_val * mult_league * mult_pos * mult_age)
            market_value = max(10000, round(market_value / 10000) * 10000)

            base_wage_k = ((max(60, ovr) - 50) ** 3) * 2
            random.seed(p.id)
            wage_variance = random.uniform(0.85, 1.15)
            wage_pos_mult = 0.7 if "Goalkeeper" in pos else 1.0
            
            wage_k = int(base_wage_k * mult_league * wage_variance * wage_pos_mult)
            wage = max(1, wage_k) * 1000 
            wage = round(wage / 500) * 500

            if age <= 20: years_left = random.randint(4, 5)
            elif age <= 23: years_left = random.randint(3, 4)
            elif age <= 27: years_left = random.randint(2, 4)
            elif age <= 30: years_left = random.randint(2, 3)
            else: years_left = random.randint(1, 2)
                
            contract_until = f"{2026 + years_left}-06-30"

            p.market_value = market_value
            p.wage = wage
            p.contract_until = contract_until
        db.commit()
        
        for p in db.query(Player).all():
            orig = {
                'age': p.age, 'overall_rating': p.overall_rating, 'market_value': p.market_value,
                'wage': p.wage, 'contract_until': p.contract_until,
                'pace': p.pace, 'shooting': p.shooting, 'passing': p.passing,
                'dribbling': p.dribbling, 'defending': p.defending, 'physicality': p.physicality,
                'gk_diving': p.gk_diving, 'gk_handling': p.gk_handling, 'gk_kicking': p.gk_kicking,
                'gk_positioning': p.gk_positioning, 'gk_reflexes': p.gk_reflexes
            }
            p.original_data = json.dumps(orig)
        db.commit()
        
        return {"status": "ok", "message": "Database completely rebuilt and original_data updated!"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

async def start_bot():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print("delete_webhook error:", e)
    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    except Exception as e:
        print("start_polling error:", e)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/app")
def read_index():
    return FileResponse("static/index.html")