from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class DraftOrder(Base):
  __tablename__ = "draftorder"
  fantasy_team_id: Mapped[int] = mapped_column(ForeignKey("fantasyteam.fantasy_team_id") ,primary_key=True)
  league_id: Mapped[int] = mapped_column(ForeignKey("league.league_id"), primary_key=True)
  draft_slot: Mapped[int] = mapped_column(Integer(), nullable=False, default=0, primary_key=True)

class DraftPick(Base):
  __tablename__ = "draftpick"
  fantasy_team_id: Mapped[int] = mapped_column(ForeignKey("fantasyteam.fantasy_team_id"), primary_key=True)
  league_id: Mapped[int] = mapped_column(ForeignKey("league.league_id"), primary_key=True)
  pick_number: Mapped[int] = mapped_column(Integer(), nullable=False, primary_key=True)
  team_number: Mapped[str] = mapped_column(ForeignKey("teams.team_number"))
  