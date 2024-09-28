from flask import Flask, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from models.base import Base
from models.scores import *
from models.draft import *
from models.transactions import *
#from models.models import Base, User, Message  # Import your models

app = Flask(__name__)

# Configure the database
DATABASE_URL = os.getenv("DATABASE_URL")  # or your database URL
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

@app.route('/api/leagues', methods=['GET'])
def get_leagues():
    session = Session()
    leagues = session.query(League).filter(League.active==True, League.is_fim==True).all()
    session.close()
    return jsonify([{"league_id": league.league_id, "league_name": league.league_name} for league in leagues])

@app.route('/api/leagues/<int:leagueId>/fantasyTeams', methods=['GET'])
def get_fantasy_teams(leagueId):
    session = Session()
    teams = session.query(FantasyTeam).filter(FantasyTeam.league_id==leagueId).order_by(FantasyTeam.fantasy_team_id.asc()).all()
    session.close()
    return jsonify([{"fantasy_team_id": team.fantasy_team_id, "team_name": team.fantasy_team_name} for team in teams])

@app.route('/api/leagues/<int:leagueId>/teamsOnWaivers', methods=['GET'])
def get_waiver_teams(leagueId):
    session = Session()
    waiverTeams = session.query(TeamOnWaivers).filter(TeamOnWaivers.league_id==leagueId).all()
    session.close()
    return jsonify({"league_id": leagueId, "waiver_teams": [team.team_number for team in waiverTeams]})

@app.route('/api/leagues/<int:leagueId>/rosters', methods=["GET"])
def get_rosters(leagueId):
    session = Session()
    teams = session.query(FantasyTeam).filter(FantasyTeam.league_id==leagueId).order_by(FantasyTeam.fantasy_team_id.asc()).all()
    teamsOwnedInLeague = session.query(TeamOwned).filter(TeamOwned.league_id==leagueId)
    output = []
    for team in teams:
        output.append({"fantasy_team_id":team.fantasy_team_id,\
                       "fantasy_team_name":team.fantasy_team_name,\
                        "roster": [frcteam.team_key for frcteam in teamsOwnedInLeague.filter(TeamOwned.fantasy_team_id==team.fantasy_team_id).all()]})
    session.close()
    return jsonify(output)

@app.route('/api/drafts/<int:draftId>/picks', methods=["GET"])
def get_draft_picks(draftId):
    session = Session()
    draftPicks = session.query(DraftPick).filter(DraftPick.draft_id==draftId).order_by(DraftPick.pick_number.asc()).all()
    session.close()

    return jsonify([{"pick_number": pick.pick_number, "fantasy_team_id": pick.fantasy_team_id, "team_picked":pick.team_number} for pick in draftPicks])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Bind to all IPs
