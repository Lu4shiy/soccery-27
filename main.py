import os
import json
import random
import unicodedata
import calendar
import asyncio
from datetime import datetime, timedelta, date
from typing import Optional, List

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
    morale = Column(String, default="green")
    fitness = Column(String, default="green")
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    matches_played = Column(Integer, default=0)
    rating_sum = Column(Float, default=0.0)
    fatigue = Column(Integer, default=0)
    injury_weeks = Column(Integer, default=0)

class Fixture(Base):
    __tablename__ = "fixtures"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"))
    round_number = Column(Integer, default=1)
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

class GameState(Base):
    __tablename__ = "game_state"
    id = Column(Integer, primary_key=True, default=1)
    current_date = Column(String, default="2026-08-01")
    season = Column(String, default="2026/27")

Base.metadata.create_all(bind=engine)

def clean_name(n):
    if not n: return ""
    n = unicodedata.normalize('NFKD', n).encode('ASCII', 'ignore').decode('utf-8')
    return n.lower().replace(" ", "").replace("-", "").replace(".", "").replace("'", "")

def init_db():
    db = Session(engine)
    try:
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS morale VARCHAR DEFAULT 'green';"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS fitness VARCHAR DEFAULT 'green';"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS goals INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS assists INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS matches_played INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS rating_sum FLOAT DEFAULT 0.0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS fatigue INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS injury_weeks INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS round_number INTEGER DEFAULT 1;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS home_sot INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS away_sot INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS home_fouls INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS away_fouls INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS home_corners INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS away_corners INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS home_offsides INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS away_offsides INTEGER DEFAULT 0;"))
        db.commit()
        
        if not db.query(GameState).first():
            db.add(GameState(current_date="2026-08-01", season="2026/27"))
            db.commit()

        for c in db.query(Club).all():
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
                Tournament(name="Carabao Cup", continent="Domestic", type="Cup"),
                Tournament(name="FA Community Shield", continent="Domestic", type="SuperCup"),
                Tournament(name="UEFA Champions League", continent="UEFA", type="Continental"),
                Tournament(name="UEFA Europa League", continent="UEFA", type="Continental"),
                Tournament(name="UEFA Conference League", continent="UEFA", type="Continental")
            ]
            for t in tours: db.add(t)
            db.commit()

        if db.query(ClubTournament).count() == 0:
            for club in db.query(Club).all():
                if club.league in ["Premier League", "EFL Championship", "EFL League One", "EFL League Two"]:
                    t1 = db.query(Tournament).filter_by(name=club.league).first()
                    if t1: db.add(ClubTournament(club_id=club.id, tournament_id=t1.id))
                    t2 = db.query(Tournament).filter_by(name="FA Cup").first()
                    if t2: db.add(ClubTournament(club_id=club.id, tournament_id=t2.id))
                    t3 = db.query(Tournament).filter_by(name="Carabao Cup").first()
                    if t3: db.add(ClubTournament(club_id=club.id, tournament_id=t3.id))
                elif club.continent == "UEFA":
                    t4 = db.query(Tournament).filter_by(name="UEFA Champions League").first()
                    if t4: db.add(ClubTournament(club_id=club.id, tournament_id=t4.id))
            db.commit()

    except Exception as e:
        print("DB Init Error:", e)
        db.rollback()
    finally:
        db.close()

init_db()

def generate_england_fixtures(db: Session):
    pl_tour = db.query(Tournament).filter_by(name="Premier League").first()
    if not pl_tour: return
    
    if db.query(Fixture).filter_by(tournament_id=pl_tour.id, date="2026-08-23").count() > 0:
        return
        
    t_ids = [t.id for t in db.query(Tournament).filter(Tournament.name.in_(["Premier League", "EFL Championship", "EFL League One", "EFL League Two", "FA Cup", "Carabao Cup", "FA Community Shield"])).all()]
    db.query(Fixture).filter(Fixture.tournament_id.in_(t_ids)).delete(synchronize_session=False)
    db.commit()

    eng_leagues = ["Premier League", "EFL Championship", "EFL League One", "EFL League Two"]
    eng_clubs = db.query(Club).filter(Club.league.in_(eng_leagues)).all()
    if not eng_clubs: return
    
    pl_clubs = [c for c in eng_clubs if c.league == "Premier League"]
    champ_clubs = [c for c in eng_clubs if c.league == "EFL Championship"]
    l1_clubs = [c for c in eng_clubs if c.league == "EFL League One"]
    l2_clubs = [c for c in eng_clubs if c.league == "EFL League Two"]
    
    pl_dates = parse_eng_dates(["23.08", "28.08", "05.09", "13.09", "20.09", "10.10", "17.10", "24.10", "31.10", "07.11", "21.11", "29.11", "02.12", "05.12", "12.12", "19.12", "26.12", "29.12", "03.01", "06.01", "16.01", "23.01", "30.01", "06.02", "10.02", "20.02", "27.02", "03.03", "13.03", "20.03", "10.04", "17.04", "24.04", "01.05", "08.05", "15.05", "23.05", "26.05"])
    efl_dates = parse_eng_dates(["07.08", "10.08", "17.08", "22.08", "28.08", "02.09", "05.09", "11.09", "19.09", "10.10", "17.10", "24.10", "30.10", "07.11", "21.11", "28.11", "05.12", "11.12", "19.12", "26.12", "29.12", "01.01", "16.01", "23.01", "30.01", "06.02", "13.02", "20.02", "27.02", "02.03", "06.03", "13.03", "20.03", "03.04", "10.04", "17.04", "20.04", "23.04", "01.05", "07.05", "10.05", "13.05", "16.05", "19.05", "22.05", "25.05"])
    
    for l_name, l_clubs, l_dates in [("Premier League", pl_clubs, pl_dates), ("EFL Championship", champ_clubs, efl_dates), ("EFL League One", l1_clubs, efl_dates), ("EFL League Two", l2_clubs, efl_dates)]:
        tour = db.query(Tournament).filter_by(name=l_name).first()
        if not tour: continue
        matches = get_double_round_robin(l_clubs[:])
        for r_idx, round_m in enumerate(matches):
            if r_idx >= len(l_dates): break
            for h, a in round_m:
                db.add(Fixture(date=l_dates[r_idx].strftime("%Y-%m-%d"), tournament_id=tour.id, round_number=r_idx+1, home_club_id=h.id, away_club_id=a.id, is_played=0))
                
    sorted_eng = sorted(eng_clubs, key=lambda c: (-(c.stars or 0), c.name))
    
    fa_cup = db.query(Tournament).filter_by(name="FA Cup").first()
    carabao = db.query(Tournament).filter_by(name="Carabao Cup").first()
    
    fa_dates = parse_eng_dates(["25.08", "24.09", "14.12", "09.01", "23.03", "29.03", "28.05"])
    car_dates = parse_eng_dates(["20.08", "30.08", "15.09", "28.09", "01.10", "04.10", "23.12"])
    
    for cup, dates in [(fa_cup, fa_dates), (carabao, car_dates)]:
        if not cup: continue
        rnd = random.Random(cup.id)
        
        weak_teams = sorted_eng[36:]
        strong_teams = sorted_eng[:36]
        
        rnd.shuffle(weak_teams)
        round2_teams = strong_teams + weak_teams[:28]
        
        if len(weak_teams) >= 56:
            weak_teams = weak_teams[:56]
            for i in range(0, len(weak_teams), 2):
                db.add(Fixture(date=dates[0].strftime("%Y-%m-%d"), tournament_id=cup.id, round_number=1, home_club_id=weak_teams[i].id, away_club_id=weak_teams[i+1].id, is_played=0))
            
        rnd.shuffle(round2_teams)
        for i in range(0, len(round2_teams), 2):
            if i+1 < len(round2_teams):
                db.add(Fixture(date=dates[1].strftime("%Y-%m-%d"), tournament_id=cup.id, round_number=2, home_club_id=round2_teams[i].id, away_club_id=round2_teams[i+1].id, is_played=0))
                
        curr_teams = round2_teams[:32]
        for r_idx in range(2, len(dates)):
            rnd.shuffle(curr_teams)
            next_r = []
            for i in range(0, len(curr_teams), 2):
                if i+1 < len(curr_teams):
                    h, a = curr_teams[i], curr_teams[i+1]
                    if r_idx == 5 and cup.name == "Carabao Cup":
                        db.add(Fixture(date=dates[r_idx].strftime("%Y-%m-%d"), tournament_id=cup.id, round_number=r_idx+1, home_club_id=h.id, away_club_id=a.id, is_played=0))
                        db.add(Fixture(date=(dates[r_idx] + timedelta(days=3)).strftime("%Y-%m-%d"), tournament_id=cup.id, round_number=r_idx+1, home_club_id=a.id, away_club_id=h.id, is_played=0))
                    else:
                        db.add(Fixture(date=dates[r_idx].strftime("%Y-%m-%d"), tournament_id=cup.id, round_number=r_idx+1, home_club_id=h.id, away_club_id=a.id, is_played=0))
                    next_r.append(h)
            curr_teams = next_r
            
    shield = db.query(Tournament).filter_by(name="FA Community Shield").first()
    if shield and len(pl_clubs) >= 2:
        db.add(Fixture(date="2027-06-09", tournament_id=shield.id, round_number=1, home_club_id=pl_clubs[0].id, away_club_id=pl_clubs[1].id, is_played=0))
        
    db.commit()

def seed_training_programs():
    db = Session(engine)
    try:
        db.query(TrainingProgram).delete()
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
        
        is_admin = (telegram_id == ADMIN_TELEGRAM_ID)
        return {"has_club": True, "club_id": club.id, "club_name": club.name, "league": club.league, "continent": club.continent, "stars": club.stars or 3.0, "is_setup_complete": bool(m.is_setup_complete), "coach_name": m.coach_name, "is_admin": is_admin}
    finally:
        db.close()

class SelectClubRequest(BaseModel):
    telegram_id: str
    first_name: Optional[str] = None
    club_id: int

def parse_eng_dates(dates_list):
    res = []
    for d_str in dates_list:
        m, d = map(int, d_str.split("."))
        year = 2026 if m >= 7 else 2027
        res.append(date(year, m, d))
    return res

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
    # Second half (reverse fixtures)
    first_half = list(matches)
    for r_matches in first_half:
        rev = []
        for h, a in r_matches:
            rev.append((a, h))
        matches.append(rev)
    return matches

def generate_england_fixtures(db: Session):
    pl_tour = db.query(Tournament).filter_by(name="Premier League").first()
    if not pl_tour: return
    if db.query(Fixture).filter_by(tournament_id=pl_tour.id).count() > 0: return
        
    eng_leagues = ["Premier League", "EFL Championship", "EFL League One", "EFL League Two"]
    eng_clubs = db.query(Club).filter(Club.league.in_(eng_leagues)).all()
    if not eng_clubs: return
    
    pl_clubs = [c for c in eng_clubs if c.league == "Premier League"]
    champ_clubs = [c for c in eng_clubs if c.league == "EFL Championship"]
    l1_clubs = [c for c in eng_clubs if c.league == "EFL League One"]
    l2_clubs = [c for c in eng_clubs if c.league == "EFL League Two"]
    
    pl_dates = parse_eng_dates(["23.08", "28.08", "05.09", "13.09", "20.09", "10.10", "17.10", "24.10", "31.10", "07.11", "21.11", "29.11", "02.12", "05.12", "12.12", "19.12", "26.12", "29.12", "03.01", "06.01", "16.01", "23.01", "30.01", "06.02", "10.02", "20.02", "27.02", "03.03", "13.03", "20.03", "10.04", "17.04", "24.04", "01.05", "08.05", "15.05", "23.05", "26.05"])
    efl_dates = parse_eng_dates(["07.08", "10.08", "17.08", "22.08", "28.08", "02.09", "05.09", "11.09", "19.09", "10.10", "17.10", "24.10", "30.10", "07.11", "21.11", "28.11", "05.12", "11.12", "19.12", "26.12", "29.12", "01.01", "16.01", "23.01", "30.01", "06.02", "13.02", "20.02", "27.02", "02.03", "06.03", "13.03", "20.03", "03.04", "10.04", "17.04", "20.04", "23.04", "01.05", "07.05", "10.05", "13.05", "16.05", "19.05", "22.05", "25.05"])
    
    for l_name, l_clubs, l_dates in [("Premier League", pl_clubs, pl_dates), ("EFL Championship", champ_clubs, efl_dates), ("EFL League One", l1_clubs, efl_dates), ("EFL League Two", l2_clubs, efl_dates)]:
        tour = db.query(Tournament).filter_by(name=l_name).first()
        if not tour: continue
        matches = get_double_round_robin(l_clubs[:])
        for r_idx, round_m in enumerate(matches):
            if r_idx >= len(l_dates): break
            for h, a in round_m:
                db.add(Fixture(date=l_dates[r_idx].strftime("%Y-%m-%d"), tournament_id=tour.id, round_number=r_idx+1, home_club_id=h.id, away_club_id=a.id, is_played=0))
                
    sorted_eng = sorted(eng_clubs, key=lambda c: (-(c.stars or 0), c.name))
    
    fa_cup = db.query(Tournament).filter_by(name="FA Cup").first()
    carabao = db.query(Tournament).filter_by(name="Carabao Cup").first()
    
    fa_dates = parse_eng_dates(["25.08", "24.09", "14.12", "09.01", "23.03", "29.03", "28.05"])
    car_dates = parse_eng_dates(["20.08", "30.08", "15.09", "28.09", "01.10", "04.10", "23.12"])
    
    for cup, dates in [(fa_cup, fa_dates), (carabao, car_dates)]:
        if not cup: continue
        rnd = random.Random(cup.id)
        
        weak_teams = sorted_eng[36:]
        strong_teams = sorted_eng[:36]
        
        rnd.shuffle(weak_teams)
        round2_teams = strong_teams + weak_teams[:28]
        
        if len(weak_teams) >= 56:
            weak_teams = weak_teams[:56]
            for i in range(0, len(weak_teams), 2):
                db.add(Fixture(date=dates[0].strftime("%Y-%m-%d"), tournament_id=cup.id, round_number=1, home_club_id=weak_teams[i].id, away_club_id=weak_teams[i+1].id, is_played=0))
            
        rnd.shuffle(round2_teams)
        for i in range(0, len(round2_teams), 2):
            if i+1 < len(round2_teams):
                db.add(Fixture(date=dates[1].strftime("%Y-%m-%d"), tournament_id=cup.id, round_number=2, home_club_id=round2_teams[i].id, away_club_id=round2_teams[i+1].id, is_played=0))
                
        curr_teams = round2_teams[:32]
        for r_idx in range(2, len(dates)):
            rnd.shuffle(curr_teams)
            next_r = []
            for i in range(0, len(curr_teams), 2):
                if i+1 < len(curr_teams):
                    h, a = curr_teams[i], curr_teams[i+1]
                    if r_idx == 5 and cup.name == "Carabao Cup":
                        db.add(Fixture(date=dates[r_idx].strftime("%Y-%m-%d"), tournament_id=cup.id, round_number=r_idx+1, home_club_id=h.id, away_club_id=a.id, is_played=0))
                        db.add(Fixture(date=(dates[r_idx] + timedelta(days=3)).strftime("%Y-%m-%d"), tournament_id=cup.id, round_number=r_idx+1, home_club_id=a.id, away_club_id=h.id, is_played=0))
                    else:
                        db.add(Fixture(date=dates[r_idx].strftime("%Y-%m-%d"), tournament_id=cup.id, round_number=r_idx+1, home_club_id=h.id, away_club_id=a.id, is_played=0))
                    next_r.append(h)
            curr_teams = next_r
            
    shield = db.query(Tournament).filter_by(name="FA Community Shield").first()
    if shield and len(pl_clubs) >= 2:
        db.add(Fixture(date="2027-06-09", tournament_id=shield.id, round_number=1, home_club_id=pl_clubs[0].id, away_club_id=pl_clubs[1].id, is_played=0))
        
    db.commit()

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
        
        generate_england_fixtures(db)
            
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
def get_club_tournaments(club_id: int):
    db = Session(engine)
    try:
        rows = db.query(Tournament).join(ClubTournament).filter(ClubTournament.club_id == club_id).all()
        if not rows:
            club = db.query(Club).filter_by(id=club_id).first()
            if club and club.league:
                t = db.query(Tournament).filter_by(name=club.league).first()
                if t: return [{"id": t.id, "name": t.name, "continent": t.continent, "type": t.type}]
            return []
        return [{"id": t.id, "name": t.name, "continent": t.continent, "type": t.type} for t in rows]
    finally:
        db.close()

@app.get("/api/game/time")
def get_game_time():
    db = Session(engine)
    try:
        state = db.query(GameState).first()
        return {"current_date": state.current_date if state else "2026-08-01", "season": state.season if state else "2026/27"}
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
            
        fixture_map = {f.date: f for f in fixtures}
        
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
                f = fixture_map[date_str]
                tour = db.query(Tournament).filter_by(id=f.tournament_id).first()
                is_home = (f.home_club_id == club_id)
                opp_id = f.away_club_id if is_home else f.home_club_id
                opp = db.query(Club).filter_by(id=opp_id).first()
                
                entry = {
                    "date": date_str, "type": "match", "fixture_id": f.id,
                    "is_played": f.is_played, "tournament_name": tour.name if tour else "Товарищеский",
                    "opponent_name": opp.name if opp else "Соперник", "is_home": is_home
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
def get_standings(tournament_id: int):
    db = Session(engine) 
    try:
        tour = db.query(Tournament).filter_by(id=tournament_id).first()
        if not tour: raise HTTPException(status_code=404, detail="Турнир не найден")
        
        clubs = db.query(Club).join(ClubTournament).filter(ClubTournament.tournament_id == tournament_id).all()
        if not clubs:
            clubs = db.query(Club).filter(Club.league == tour.name).all()
            
        fixtures = db.query(Fixture).filter_by(tournament_id=tournament_id, is_played=1).all()
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
        stats = db.query(MatchPlayerStats).filter_by(fixture_id=fixture_id).all()
        res = []
        for s in stats:
            p = db.query(Player).filter_by(id=s.player_id).first()
            if p:
                res.append({
                    "name": p.name, "club_id": s.club_id,
                    "minutes": s.minutes_played, "rating": round(s.rating, 1)
                })
        return res
    finally:
        db.close()

@app.get("/api/tournaments/{tournament_id}/stats")
def get_stats(tournament_id: int):
    db = Session(engine)
    try:
        tour = db.query(Tournament).filter_by(id=tournament_id).first()
        if not tour: return {"scorers": [], "assists": [], "rating": [], "clean_sheets": []}
        
        fixtures = db.query(Fixture).filter_by(tournament_id=tournament_id, is_played=1).all()
        fx_ids = [f.id for f in fixtures]
        
        if not fx_ids:
            return {"scorers": [], "assists": [], "rating": [], "clean_sheets": []}
            
        scorers_q = db.query(MatchEvent.player_id, func.count(MatchEvent.id)).filter(
            MatchEvent.fixture_id.in_(fx_ids),
            MatchEvent.event_type.in_(['goal', 'penalty_goal'])
        ).group_by(MatchEvent.player_id).order_by(func.count(MatchEvent.id).desc()).limit(10).all()
        
        scorers = []
        for pid, count in scorers_q:
            p = db.query(Player).filter_by(id=pid).first()
            if p: scorers.append({"player": p.name, "team": "Клуб", "val": count})
            
        assists_q = db.query(MatchEvent.assist_id, func.count(MatchEvent.id)).filter(
            MatchEvent.fixture_id.in_(fx_ids),
            MatchEvent.assist_id.isnot(None)
        ).group_by(MatchEvent.assist_id).order_by(func.count(MatchEvent.id).desc()).limit(10).all()
        
        assists = []
        for pid, count in assists_q:
            p = db.query(Player).filter_by(id=pid).first()
            if p: assists.append({"player": p.name, "team": "Клуб", "val": count})
            
        ratings_q = db.query(MatchPlayerStats.player_id, func.avg(MatchPlayerStats.rating)).filter(
            MatchPlayerStats.fixture_id.in_(fx_ids)
        ).group_by(MatchPlayerStats.player_id).order_by(func.avg(MatchPlayerStats.rating).desc()).limit(10).all()
        
        avg_ratings = []
        for pid, avg_r in ratings_q:
            p = db.query(Player).filter_by(id=pid).first()
            if p: avg_ratings.append({"player": p.name, "team": "Клуб", "val": round(avg_r, 2)})
            
        cs_dict = {}
        for f in fixtures:
            if f.home_goals == 0: cs_dict[f.away_club_id] = cs_dict.get(f.away_club_id, 0) + 1
            if f.away_goals == 0: cs_dict[f.home_club_id] = cs_dict.get(f.home_club_id, 0) + 1
                
        clean_sheets = []
        for cid, count in cs_dict.items():
            c = db.query(Club).filter_by(id=cid).first()
            if c: clean_sheets.append({"team": c.name, "val": count})
        clean_sheets.sort(key=lambda x: x["val"], reverse=True)

        return {"scorers": scorers, "assists": assists, "rating": avg_ratings, "clean_sheets": clean_sheets[:10]}
    finally:
        db.close()

@app.get("/api/tournaments/{tournament_id}/bracket")
def get_bracket(tournament_id: int):
    db = Session(engine)
    try:
        tour = db.query(Tournament).filter_by(id=tournament_id).first()
        if not tour: raise HTTPException(status_code=404, detail="Турнир не найден")
        
        clubs = db.query(Club).join(ClubTournament).filter(ClubTournament.tournament_id == tournament_id).order_by(Club.name).all()
        if not clubs: return {"type": tour.type, "rounds": []}
        
        n = len(clubs)
        size = 2
        while size < n and size < 128: size *= 2
        if size < 4: size = 4
        
        teams = [c.name for c in clubs[:size]]
        while len(teams) < size: teams.append("TBD")
        
        rounds = []
        round_names = {2: "Финал", 4: "1/2 финала", 8: "1/4 финала", 16: "1/8 финала", 32: "1/16 финала", 64: "1/32 финала", 128: "1/64 финала"}
        
        num_in_round = size
        is_first = True
        while num_in_round >= 2:
            round_name = round_names.get(num_in_round, f"1/{num_in_round-1} финала")
            num_matches = num_in_round // 2
            matches = []
            for i in range(num_matches):
                if is_first:
                    t1 = teams[i*2] if i*2 < len(teams) else "TBD"
                    t2 = teams[i*2 + 1] if i*2 + 1 < len(teams) else "TBD"
                else:
                    t1, t2 = "TBD", "TBD"
                matches.append({"team1": t1, "team2": t2, "score1": None, "score2": None})
            rounds.append({"name": round_name, "matches": matches})
            num_in_round //= 2
            is_first = False
        
        return {"type": tour.type, "rounds": rounds}
    finally:
        db.close()

@app.post("/api/admin/reset-game")
def reset_game(req: dict):
    tg_id = req.get("telegram_id")
    if tg_id != ADMIN_TELEGRAM_ID: raise HTTPException(status_code=403, detail="Нет прав")
    
    db = Session(engine)
    try:
        db.query(MatchEvent).delete()
        db.query(MatchPlayerStats).delete()
        db.query(Fixture).delete()
        db.query(Tactic).delete()
        db.query(Manager).delete()
        
        db.query(Player).update({
            Player.goals: 0, Player.assists: 0, Player.matches_played: 0,
            Player.rating_sum: 0.0, Player.fatigue: 0, Player.injury_weeks: 0,
            Player.fitness: "green", Player.morale: "green"
        }, synchronize_session=False)
        
        state = db.query(GameState).first()
        if state: state.current_date = "2026-08-01"
        db.commit()
        return {"status": "ok"}
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

def simulate_match(fixture_id: int, db: Session):
    fx = db.query(Fixture).filter_by(id=fixture_id).first()
    if not fx or fx.is_played: return
    
    home = db.query(Club).filter_by(id=fx.home_club_id).first()
    away = db.query(Club).filter_by(id=fx.away_club_id).first()
    
    def get_xi(club_id):
        t = db.query(Tactic).join(Manager).filter(Manager.club_id == club_id).first()
        players = []
        if t and t.starting_xi:
            xi_ids = json.loads(t.starting_xi)
            players = db.query(Player).filter(Player.id.in_(xi_ids)).all()
        if not players:
            players = db.query(Player).filter_by(club_id=club_id).order_by(Player.overall_rating.desc()).limit(11).all()
        return players

    h_xi = get_xi(home.id)
    a_xi = get_xi(away.id)
    
    h_att = sum([(p.shooting or 50) + (p.pace or 50) for p in h_xi if "Goalkeeper" not in p.position]) / 20
    a_def = sum([(p.defending or 50) + (p.physicality or 50) for p in a_xi if "Goalkeeper" not in p.position]) / 20
    a_att = sum([(p.shooting or 50) + (p.pace or 50) for p in a_xi if "Goalkeeper" not in p.position]) / 20
    h_def = sum([(p.defending or 50) + (p.physicality or 50) for p in h_xi if "Goalkeeper" not in p.position]) / 20
    
    h_goals, a_goals = 0, 0
    events = []
    
    def add_event(minute, e_type, club_id, p_id=None, a_id=None):
        events.append(MatchEvent(fixture_id=fx.id, minute=minute, event_type=e_type, club_id=club_id, player_id=p_id, assist_id=a_id))
        
    add_event(0, "start", None)
    add_event(45, "half_end", None)
    add_event(46, "second_half", None)
    add_event(90, "end", None)

    total_shots_h = max(2, int((h_att - a_def) * 1.5) + 10)
    total_shots_a = max(2, int((a_att - h_def) * 1.5) + 8)
    h_sot, a_sot = 0, 0
    
    h_players = [p for p in h_xi if "Goalkeeper" not in p.position]
    a_players = [p for p in a_xi if "Goalkeeper" not in p.position]
    
    for _ in range(total_shots_h):
        if random.random() < 0.4:
            h_sot += 1
            minute = random.randint(1, 90)
            if random.random() < 0.35:
                h_goals += 1
                scorer = random.choice(h_players)
                assist = random.choice([p for p in h_players if p.id != scorer.id]) if random.random() < 0.65 else None
                add_event(minute, 'goal', home.id, scorer.id, assist.id if assist else None)
                scorer.goals = (scorer.goals or 0) + 1
                if assist: assist.assists = (assist.assists or 0) + 1
                
    for _ in range(total_shots_a):
        if random.random() < 0.4:
            a_sot += 1
            minute = random.randint(1, 90)
            if random.random() < 0.30:
                a_goals += 1
                scorer = random.choice(a_players)
                assist = random.choice([p for p in a_players if p.id != scorer.id]) if random.random() < 0.65 else None
                add_event(minute, 'goal', away.id, scorer.id, assist.id if assist else None)
                scorer.goals = (scorer.goals or 0) + 1
                if assist: assist.assists = (assist.assists or 0) + 1

    if random.random() < 0.2:
        side = home.id if random.random() < 0.5 else away.id
        minute = random.randint(1, 90)
        add_event(minute, 'penalty_goal' if random.random() < 0.7 else 'penalty_miss', side)
        if side == home.id: h_goals += 1
        else: a_goals += 1

    for _ in range(random.randint(1, 4)):
        side = home.id if random.random() < 0.5 else away.id
        p = random.choice(h_players if side == home.id else a_players)
        add_event(random.randint(10, 85), 'yellow_card', side, p.id)
        
    if random.random() < 0.05:
        side = home.id if random.random() < 0.5 else away.id
        p = random.choice(h_players if side == home.id else a_players)
        add_event(random.randint(20, 80), 'red_card', side, p.id)
        
    for _ in range(random.randint(3, 5)):
        side = home.id if random.random() < 0.5 else away.id
        out_p = random.choice(h_players if side == home.id else a_players)
        in_p = db.query(Player).filter_by(club_id=side).first()
        add_event(random.randint(60, 85), 'substitution', side, out_p.id, in_p.id if in_p else None)

    for p in h_xi + a_xi:
        p.matches_played = (p.matches_played or 0) + 1
        p.fatigue = min(100, (p.fatigue or 0) + random.randint(20, 35))
        
        base_rating = 6.0 + random.uniform(-0.5, 0.5)
        mp_stat = MatchPlayerStats(fixture_id=fx.id, player_id=p.id, club_id=p.club_id, minutes_played=90, rating=base_rating)
        db.add(mp_stat)
        
    if h_goals > a_goals:
        for p in h_xi: p.morale = "green"
        for p in a_xi: p.morale = "red" if p.morale == "orange" else "orange"
    elif a_goals > h_goals:
        for p in a_xi: p.morale = "green"
        for p in h_xi: p.morale = "red" if p.morale == "orange" else "orange"
        
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
    
    for ev in events: db.add(ev)
    db.commit()

def advance_game_date(db, days_to_add):
    state = db.query(GameState).first()
    if not state: return None
    curr = datetime.strptime(state.current_date, "%Y-%m-%d").date()
    
    for _ in range(days_to_add):
        curr += timedelta(days=1)
        date_str = curr.strftime("%Y-%m-%d")
        
        fixtures = db.query(Fixture).filter(Fixture.date == date_str, Fixture.is_played == 0).all()
        for fx in fixtures:
            simulate_match(fx.id, db)
            
        players = db.query(Player).all()
        for p in players:
            p.fatigue = max(0, (p.fatigue or 0) - 15)
            if p.fatigue > 80: p.fitness = "red"
            elif p.fatigue > 60: p.fitness = "orange"
            elif p.fatigue > 40: p.fitness = "yellow"
            else: p.fitness = "green"
            
    state.current_date = curr.strftime("%Y-%m-%d")
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
def get_tournament_rounds(tournament_id: int):
    db = Session(engine)
    try:
        rounds = db.query(Fixture.round_number).filter_by(tournament_id=tournament_id).distinct().order_by(Fixture.round_number).all()
        return [r[0] for r in rounds]
    finally:
        db.close()

@app.get("/api/tournaments/{tournament_id}/rounds/{round_number}")
def get_round_matches(tournament_id: int, round_number: int):
    db = Session(engine)
    try:
        fixtures = db.query(Fixture).filter_by(tournament_id=tournament_id, round_number=round_number).all()
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
        events_data = []
        for e in events:
            p = db.query(Player).filter_by(id=e.player_id).first()
            a = db.query(Player).filter_by(id=e.assist_id).first() if e.assist_id else None
            events_data.append({
                "minute": e.minute, "type": e.event_type, "club_id": e.club_id,
                "player": p.name if p else "", "assist": a.name if a else ""
            })
            
        return {
            "id": fx.id, "date": fx.date, "is_played": bool(fx.is_played),
            "home_club": home.name, "away_club": away.name,
            "home_goals": fx.home_goals, "away_goals": fx.away_goals,
            "home_poss": fx.home_poss, "away_poss": fx.away_poss,
            "home_shots": fx.home_shots, "away_shots": fx.away_shots,
            "home_sot": fx.home_sot, "away_sot": fx.away_sot,
            "home_fouls": fx.home_fouls, "away_fouls": fx.away_fouls,
            "home_corners": fx.home_corners, "away_corners": fx.away_corners,
            "home_offsides": fx.home_offsides, "away_offsides": fx.away_offsides,
            "tournament": tour.name if tour else "",
            "events": events_data
        }
    finally:
        db.close()

@dp.message(Command("day"))
async def cmd_admin_day(message: types.Message):
    if str(message.from_user.id) != ADMIN_TELEGRAM_ID:
        await message.answer("⛔ У вас нет прав.")
        return
    db = Session(engine)
    new_date = advance_game_date(db, 1)
    db.close()
    await message.answer(f"⏩ Промотан 1 день. Дата: {new_date}")

@dp.message(Command("week"))
async def cmd_admin_week(message: types.Message):
    if str(message.from_user.id) != ADMIN_TELEGRAM_ID:
        await message.answer("⛔ У вас нет прав.")
        return
    db = Session(engine)
    state = db.query(GameState).first()
    if state:
        curr = datetime.strptime(state.current_date, "%Y-%m-%d").date()
        days_to_sunday = 6 - curr.weekday()
        if days_to_sunday == 0: days_to_sunday = 7
        new_date = advance_game_date(db, days_to_sunday)
        await message.answer(f"⏩ Промотано до конца недели. Дата: {new_date}")
    db.close()

@dp.message(Command("month"))
async def cmd_admin_month(message: types.Message):
    if str(message.from_user.id) != ADMIN_TELEGRAM_ID:
        await message.answer("⛔ У вас нет прав.")
        return
    db = Session(engine)
    state = db.query(GameState).first()
    if state:
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
        new_date_str = advance_game_date(db, delta_days)
        await message.answer(f"⏩ Промотан месяц. Дата: {new_date_str}")
    db.close()

@dp.message(Command("date"))
async def cmd_admin_date(message: types.Message, command: CommandObject):
    if str(message.from_user.id) != ADMIN_TELEGRAM_ID:
        await message.answer("⛔ У вас нет прав.")
        return
    if not command.args:
        await message.answer("⚠️ Укажите дату: /date 2026-09-15")
        return
    try:
        new_date = datetime.strptime(command.args.strip(), "%Y-%m-%d").date()
    except ValueError:
        await message.answer("⚠️ Неверный формат. Используйте ГГГГ-ММ-ДД.")
        return
    
    db = Session(engine)
    state = db.query(GameState).first()
    if state:
        curr = datetime.strptime(state.current_date, "%Y-%m-%d").date()
        if new_date < curr:
            await message.answer("⚠️ Нельзя промотать время назад.")
            db.close()
            return
        
        delta_days = (new_date - curr).days
        new_date_str = advance_game_date(db, delta_days)
        await message.answer(f"⏩ Установлена дата: {new_date_str}")
    db.close()

@dp.message(Command("reset"))
async def cmd_admin_reset(message: types.Message):
    if str(message.from_user.id) != ADMIN_TELEGRAM_ID:
        await message.answer("⛔ У вас нет прав.")
        return
    
    db = Session(engine)
    try:
        db.query(MatchEvent).delete()
        db.query(MatchPlayerStats).delete()
        db.query(Fixture).delete()
        db.query(Tactic).delete()
        db.query(Manager).delete()
        
        db.query(Player).update({
            Player.goals: 0, Player.assists: 0, Player.matches_played: 0,
            Player.rating_sum: 0.0, Player.fatigue: 0, Player.injury_weeks: 0,
            Player.fitness: "green", Player.morale: "green"
        }, synchronize_session=False)
        
        state = db.query(GameState).first()
        if state: 
            state.current_date = "2026-08-01"
            state.season = "2026/27"
            
        db.commit()
        await message.answer("💥 Карьера полностью сброшена! Время вернулось на 01.08.2026.")
    except Exception as e:
        db.rollback()
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        db.close()

async def start_bot():
    await dp.start_polling(bot)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/app")
def read_index():
    return FileResponse("static/index.html")

try:
    db_init = Session(engine)
    generate_england_fixtures(db_init)
    db_init.close()
except Exception as e:
    print("Error generating fixtures on startup:", e)