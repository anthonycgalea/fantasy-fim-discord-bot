from sqlalchemy import Boolean, ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column
import json
from .base import Base


class Team(Base):
  __tablename__ = "teams"

  team_number: Mapped[str] = mapped_column(primary_key=True)
  name: Mapped[str] = mapped_column(String(255), nullable=False)
  is_fim: Mapped[Boolean] = mapped_column(Boolean(), nullable=False, default=False)
  rookie_year: Mapped[int] = mapped_column(Integer(), nullable=True)

  def __str__(self):
    return str(self.teamnumber) + " " + self.name

class FRCEvent(Base):
  __tablename__ = "frcevent"

  event_key: Mapped[str] = mapped_column(primary_key=True)
  event_name: Mapped[str] = mapped_column(String(255), nullable=False)
  year: Mapped[int] = mapped_column(Integer(), nullable=False)
  week: Mapped[int] = mapped_column(Integer(), nullable=False)
  is_fim: Mapped[bool] = mapped_column(Boolean(), nullable=False)

  def __str__(self):
    return self.eventname

class TeamScore(Base):
  __tablename__ = "teamscore"
  team_key: Mapped[str] = mapped_column(ForeignKey("teams.team_number"), primary_key=True)
  event_key: Mapped[str] = mapped_column(ForeignKey("frcevent.event_key"), primary_key=True)
  qual_points: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
  alliance_points: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
  elim_points: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
  award_points: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
  rookie_points: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
  stat_correction: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
  event_finished: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)

  def score_team(self):
    return self.qual_points+self.alliance_points+self.elim_points+\
    self.award_points+self.rookie_points+self.stat_correction
  
  def __str__(self):
    return str(self.team_key) +" Competing at " + str(self.event_key) +\
    " has scored " + str(self.score_team()) + " points"
  
  def json(self):
    json_data = {}
    json_data["team_key"] = self.team_key
    json_data["event_key"] = self.event_key
    json_data["qual_points"] = self.qual_points
    json_data["alliance_points"] = self.alliance_points
    json_data["elim_points"] = self.elim_points
    json_data["award_points"] = self.award_points
    json_data["rookie_bonus"] = self.rookie_bonus
    json_data["stat_correction"] = self.stat_correction
    json_data["totalScore"] = self.score_team()
    return json.dumps(json_data)

class League(Base):
  __tablename__ = "league"
  league_id: Mapped[int] = mapped_column(primary_key=True)
  league_name: Mapped[str] = mapped_column(String(255), nullable=False)
  offseason: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
  team_limit: Mapped[int] = mapped_column(Integer(), nullable=False, default=8)
  team_starts: Mapped[int] = mapped_column(Integer(), nullable=False, default=3)
  is_fim: Mapped[bool] = mapped_column(Boolean(), default=False)
  year: Mapped[int] = mapped_column(Integer(), nullable=False)
  active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)

  def __str__(self):
    return self.league_name

class FantasyTeam(Base):
  __tablename__ = "fantasyteam"
  fantasy_team_id: Mapped[int] = mapped_column(Integer(), primary_key=True)
  fantasy_team_name: Mapped[str] = mapped_column(String(255), nullable=False)
  league_id: Mapped[int] = mapped_column(ForeignKey("league.league_id"), nullable=False)

class TeamOwned(Base):
  __tablename__ = "teamowned"
  team_key: Mapped[str] = mapped_column(ForeignKey("teams.team_number"), primary_key=True)
  fantasy_team_id: Mapped[int] = mapped_column(ForeignKey("fantasyteam.fantasy_team_id"),\
                                               primary_key=True)
  league_id: Mapped[int] = mapped_column(ForeignKey("league.league_id"),primary_key=True)
  
  def __str__(self):
    return str(self.team_key) + " is owned by " + str(self.fantasy_team_id) + " in " +\
                                str(self.league_id)

class TeamStarted(Base):
  __tablename__ = "teamstarted"
  fantasy_team: Mapped[int] = mapped_column(ForeignKey("fantasyteam.fantasy_team_id"),\
                                            primary_key=True)
  team: Mapped[str] = mapped_column(ForeignKey("teams.team_number"), primary_key=True)
  league: Mapped[int] = mapped_column(ForeignKey("league.league_id"), primary_key=True)
  event: Mapped[str] = mapped_column(ForeignKey("frcevent.event_key"), primary_key=True)
  week: Mapped[int] = mapped_column(Integer(), nullable=False, default=0, primary_key=True)

class PlayerAuthorized(Base):
  __tablename__ = "playerauthorized"
  player_id: Mapped[str] = mapped_column(ForeignKey("players.user_id"),
                                        primary_key=True)
  fantasy_team_id: Mapped[int] = mapped_column(ForeignKey("fantasyteam.fantasy_team_id"), primary_key=True)