from flask import Flask, jsonify, abort
from flasgger import Swagger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from models.base import Base
from models.scores import *
from models.draft import *
from models.transactions import *
#from models.models import Base, User, Message  # Import your models

app = Flask(__name__)
swagger = Swagger(app)

# Configure the database
DATABASE_URL = os.getenv("DATABASE_URL")  # or your database URL
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

@app.route('/api/leagues', methods=['GET'])
def get_leagues():
    """
    Retrieve a list of active FIM leagues.
    ---
    tags:
        - Leagues

    responses:
      200:
        description: A list of active FIM leagues.
        schema:
          type: array
          items:
            properties:
              league_id:
                type: integer
                example: 1
              league_name:
                type: string
                example: "FRC 2024"
      500:
        description: Internal server error.
    """
    session = Session()
    leagues = session.query(League).filter(League.active==True, League.is_fim==True).all()
    session.close()
    return jsonify([{"league_id": league.league_id, "league_name": league.league_name} for league in leagues])

@app.route('/api/leagues/<int:leagueId>/fantasyTeams', methods=['GET'])
def get_fantasy_teams(leagueId):
    """
    Retrieve a list of fantasy teams for a specific league.
    ---
    tags:
        - Leagues
    parameters:
      - name: leagueId
        in: path
        type: integer
        required: true
        description: The ID of the league for which to retrieve fantasy teams.
    responses:
      200:
        description: A list of fantasy teams for the specified league.
        schema:
          type: array
          items:
            properties:
              fantasy_team_id:
                type: integer
                example: 1
              team_name:
                type: string
                example: "Team Awesome"
      404:
        description: League not found.
      500:
        description: Internal server error.
    """
    session = Session()
    teams = session.query(FantasyTeam).filter(FantasyTeam.league_id==leagueId).order_by(FantasyTeam.fantasy_team_id.asc()).all()
    session.close()
    return jsonify([{"fantasy_team_id": team.fantasy_team_id, "team_name": team.fantasy_team_name} for team in teams])

@app.route('/api/leagues/<int:leagueId>/teamsOnWaivers', methods=['GET'])
def get_waiver_teams(leagueId):
    """
    Retrieve a list of teams on waivers for a specific league.
    ---
    tags:
        - Leagues
        - Waivers
    parameters:
      - name: leagueId
        in: path
        type: integer
        required: true
        description: The ID of the league for which to retrieve teams on waivers.
    responses:
      200:
        description: A list of teams on waivers for the specified league.
        schema:
          type: object
          properties:
            league_id:
              type: integer
              example: 1
            waiver_teams:
              type: array
              items:
                type: integer
                example: 1234
      404:
        description: League not found.
      500:
        description: Internal server error.
    """
    session = Session()
    waiverTeams = session.query(TeamOnWaivers).filter(TeamOnWaivers.league_id==leagueId).all()
    session.close()
    return jsonify({"league_id": leagueId, "waiver_teams": [team.team_number for team in waiverTeams]})

@app.route('/api/leagues/<int:leagueId>/rosters', methods=["GET"])
def get_rosters(leagueId):
    """
    Retrieve the rosters for all fantasy teams in a specific league.
    ---
    tags:
        - Leagues
    parameters:
      - name: leagueId
        in: path
        type: integer
        required: true
        description: The ID of the league for which to retrieve team rosters.
    responses:
      200:
        description: A list of rosters for all fantasy teams in the specified league.
        schema:
          type: array
          items:
            properties:
              fantasy_team_id:
                type: integer
                example: 1
              fantasy_team_name:
                type: string
                example: "Team Awesome"
              roster:
                type: array
                items:
                  type: string
                  example: "frc1234"
      404:
        description: League not found.
      500:
        description: Internal server error.
    """
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
    """
    Retrieve a list of draft picks for a specific draft.
    ---
    tags:
        - Drafts
    parameters:
      - name: draftId
        in: path
        type: integer
        required: true
        description: The ID of the draft for which to retrieve draft picks.
    responses:
      200:
        description: A list of draft picks for the specified draft.
        schema:
          type: array
          items:
            properties:
              pick_number:
                type: integer
                example: 1
              fantasy_team_id:
                type: integer
                example: 2
              team_picked:
                type: string
                example: "frc1234"
      404:
        description: Draft not found.
      500:
        description: Internal server error.
    """
    session = Session()
    draftPicks = session.query(DraftPick).filter(DraftPick.draft_id==draftId).order_by(DraftPick.pick_number.asc()).all()
    session.close()

    return jsonify([{"pick_number": pick.pick_number, "fantasy_team_id": pick.fantasy_team_id, "team_picked":pick.team_number} for pick in draftPicks])

@app.route('/api/drafts/<int:draftId>/draftOrder', methods=['GET'])
def get_draft_order(draftId):
    """
    Get Draft Order for a Specific Draft
    ---
    tags:
      - Drafts
    parameters:
      - name: draftId
        in: path
        type: integer
        required: true
        description: The ID of the draft to retrieve the order for
    responses:
      200:
        description: A list of fantasy teams with their draft slots for the specified draft
        schema:
          type: array
          items:
            type: object
            properties:
              fantasy_team_id:
                type: integer
                description: The ID of the fantasy team
              draft_slot:
                type: integer
                description: The slot of the team in the draft
      404:
        description: Draft not found
    """
    session = Session()
    
    # Query draft order for the specified draftId
    draft_order = session.query(DraftOrder).filter(DraftOrder.draft_id == draftId).order_by(DraftOrder.draft_slot.asc()).all()
    session.close()

    if not draft_order:
        return jsonify({"error": "Draft not found"}), 404

    # Convert the DraftOrder objects to a list of dictionaries for the JSON response
    return jsonify([{
        "fantasy_team_id": draft.fantasy_team_id,
        "draft_slot": draft.draft_slot
    } for draft in draft_order])

@app.route('/api/leagues/<int:leagueId>/fantasyScores/<int:week>', methods=['GET'])
def get_fantasy_scores(leagueId, week):
    """
    Retrieve the fantasy scores for all fantasy teams in a specified league for a specific week.

    ---
    tags:
      - FantasyScores
    parameters:
      - name: leagueId
        in: path
        required: true
        description: The ID of the league to retrieve fantasy scores for.
        type: integer
      - name: week
        in: path
        required: true
        description: The week for which to retrieve the fantasy scores.
        type: integer
    responses:
      200:
        description: A list of fantasy teams with their weekly scores and breakdown of teams started.
        schema:
          type: array
          items:
            type: object
            properties:
              fantasy_team_id:
                type: integer
                description: The ID of the fantasy team.
              fantasy_team_name:
                type: string
                description: The name of the fantasy team.
              weekly_score:
                type: integer
                description: The total score of the fantasy team for the week.
              rank_points:
                type: integer
                description: Ranking points for the fantasy team.
              week:
                type: integer
                description: The week number for which the scores are being retrieved.
              teams:
                type: array
                items:
                  type: object
                  properties:
                    team_number:
                      type: string
                      description: The number of the team started.
                    weekly_score:
                      type: integer
                      description: The total score of the team for the week.
                    qual_points:
                      type: integer
                      description: Qualification points scored by the team.
                    alliance_points:
                      type: integer
                      description: Alliance points scored by the team.
                    elim_points:
                      type: integer
                      description: Elimination points scored by the team.
                    award_points:
                      type: integer
                      description: Award points scored by the team.
                    rookie_points:
                      type: integer
                      description: Rookie points scored by the team.
                    stat_correction:
                      type: integer
                      description: Statistical corrections applied to the team's score.
      404:
        description: No fantasy teams found for the specified league and week.
      500:
        description: Internal server error.
    """
    session = Session()
    
    # Query to get fantasy scores for the given league and week
    fantasy_scores = session.query(FantasyScores).filter(
        FantasyScores.league_id == leagueId,
        FantasyScores.week == week
    ).order_by(FantasyScores.fantasy_team_id.asc()).all()
    
    # Prepare the output
    output = []
    for score in fantasy_scores:
        # Get the fantasy team details
        fantasy_team = session.query(FantasyTeam).filter(FantasyTeam.fantasy_team_id == score.fantasy_team_id).first()
        
        # Get the teams started by this fantasy team for the specified week
        started_teams = session.query(TeamStarted).filter(
            TeamStarted.fantasy_team_id == score.fantasy_team_id,
            TeamStarted.week == week
        ).all()
        
        # Prepare a breakdown of scores
        team_scores_breakdown = []
        for started_team in started_teams:
            # Get the team score for the started team
            team_score = session.query(TeamScore).filter(
                TeamScore.team_key == started_team.team_number,
                TeamScore.event_key == started_team.event_key  # Assuming the event_key relates to the TeamScore table
            ).first()
            
            if team_score:
                team_scores_breakdown.append({
                    "team_number": started_team.team_number,
                    "weekly_score": team_score.score_team(),
                    "breakdown": {
                    "qual_points": team_score.qual_points,
                    "alliance_points": team_score.alliance_points,
                    "elim_points": team_score.elim_points,
                    "award_points": team_score.award_points,
                    "rookie_points": team_score.rookie_points,
                    "stat_correction": team_score.stat_correction
                    }  # Calculate total score using the method in TeamScore
                })
        
        # Append to the output if any teams were started
        if team_scores_breakdown:
            output.append({
                "fantasy_team_id": fantasy_team.fantasy_team_id,
                "fantasy_team_name": fantasy_team.fantasy_team_name,
                "weekly_score": score.weekly_score,
                "rank_points": score.rank_points,
                "week": week,
                "teams": team_scores_breakdown
            })
    
    session.close()
    return jsonify(output)

@app.route('/api/leagues/<int:leagueId>/waiverPriority', methods=['GET'])
def get_waiver_priority(leagueId):
    """
    Get Waiver Priority for a Specific League
    ---
    tags:
      - Waivers
      - Leagues
    parameters:
      - name: leagueId
        in: path
        type: integer
        required: true
        description: The ID of the league to retrieve the waiver priority for
    responses:
      200:
        description: A list of fantasy teams with their waiver priority in the specified league
        schema:
          type: array
          items:
            type: object
            properties:
              fantasy_team_id:
                type: integer
                description: The ID of the fantasy team
              priority:
                type: integer
                description: The waiver priority of the fantasy team
      404:
        description: League not found
    """
    session = Session()
    
    # Query waiver priority for the specified leagueId
    waiver_priority = session.query(WaiverPriority).filter(WaiverPriority.league_id == leagueId).order_by(WaiverPriority.priority.asc()).all()
    session.close()

    if not waiver_priority:
        return jsonify({"error": "League not found or no waiver priorities"}), 404

    # Convert the WaiverPriority objects to a list of dictionaries for the JSON response
    return jsonify([{
        "fantasy_team_id": waiver.fantasy_team_id,
        "priority": waiver.priority
    } for waiver in waiver_priority])

@app.route('/api/leagues/<int:leagueId>/rankings', methods=['GET'])
def get_league_rankings(leagueId):
    """
    Retrieve cumulative rankings per week for every team in a league, sorted by cumulative ranking points,
    only including weeks with finalized scores.
    ---
    tags:
      - Leagues
      - FantasyScores
    parameters:
      - name: leagueId
        in: path
        type: integer
        required: true
        description: ID of the league to retrieve rankings for.
    responses:
      200:
        description: A list of teams with their cumulative ranking points and weekly breakdowns.
        schema:
          type: array
          items:
            type: object
            properties:
              fantasy_team_id:
                type: integer
                description: The ID of the fantasy team.
              fantasy_team_name:
                type: string
                description: The name of the fantasy team.
              total_ranking_points:
                type: number
                description: Cumulative ranking points for the team.
              weekly_scores:
                type: array
                items:
                  type: object
                  properties:
                    week:
                      type: integer
                      description: The week number.
                    ranking_points:
                      type: number
                      description: The ranking points for that week.
                    weekly_score:
                      type: integer
                      description: The weekly score for that week.
    """
    session = Session()

    # Query the league to get the league year
    league = session.query(League).filter(League.league_id == leagueId).first()
    
    if not league:
        session.close()
        return jsonify({"error": "League not found"}), 404

    # Query for the weeks with finalized scores for the league's year
    finalized_weeks = session.query(WeekStatus).filter(
        WeekStatus.year == league.year,
        WeekStatus.scores_finalized == True
    ).all()

    finalized_week_numbers = {week.week for week in finalized_weeks}

    # Query for the fantasy teams in the specified league
    fantasy_teams = session.query(FantasyTeam).filter(FantasyTeam.league_id == leagueId).all()

    result = []

    for team in fantasy_teams:
        # Get all the scores for the fantasy team, filtering by finalized weeks
        scores = session.query(FantasyScores).filter(
            FantasyScores.fantasy_team_id == team.fantasy_team_id,
            FantasyScores.week.in_(finalized_week_numbers)
        ).order_by(FantasyScores.week.asc()).all()

        total_ranking_points = sum(score.rank_points for score in scores)
        
        weekly_scores = [{"week": score.week,
                          "ranking_points": score.rank_points,
                          "weekly_score": score.weekly_score} for score in scores]

        result.append({
            "fantasy_team_id": team.fantasy_team_id,
            "fantasy_team_name": team.fantasy_team_name,
            "total_ranking_points": total_ranking_points,
            "weekly_scores": weekly_scores
        })

    # Sort by total ranking points in descending order
    result.sort(key=lambda x: x["total_ranking_points"], reverse=True)

    session.close()

    return jsonify(result)

@app.route('/api/leagues/<int:leagueId>/drafts', methods=['GET'])
def get_league_drafts(leagueId):
    """
    Retrieve all drafts in a league with their draft ID, round, and event key.
    ---
    tags:
      - Leagues
      - Drafts
    parameters:
      - name: leagueId
        in: path
        type: integer
        required: true
        description: ID of the league to retrieve drafts for.
    responses:
      200:
        description: A list of drafts with their ID, round, and event key.
        schema:
          type: array
          items:
            type: object
            properties:
              draft_id:
                type: integer
                description: The ID of the draft.
              rounds:
                type: integer
                description: The amound of rounds in the draft.
              event_key:
                type: string
                description: The event key for the draft.
      404:
        description: League not found.
    """
    session = Session()

    # Check if the league exists
    league = session.query(League).filter(League.league_id == leagueId).first()

    if not league:
        session.close()
        return jsonify({"error": "League not found"}), 404

    # Query for drafts associated with the league
    drafts = session.query(Draft).filter(Draft.league_id == leagueId).all()

    # Structure the response data
    result = [{
        "draft_id": draft.draft_id,
        "round": draft.rounds,
        "event_key": draft.event_key
    } for draft in drafts]

    session.close()

    return jsonify(result)

@app.route('/api/drafts/<int:draftId>/availableTeams', methods=['GET'])
def get_available_teams(draftId):
    """
    Retrieve all available teams for a specific draft.
    ---
    tags:
      - Drafts
    parameters:
      - name: draftId
        in: path
        type: integer
        required: true
        description: ID of the draft to retrieve available teams for.
    responses:
      200:
        description: A list of available teams for the draft.
        schema:
          type: array
          items:
            type: object
            properties:
              team_number:
                type: integer
                description: The number of the available team.
      404:
        description: Draft not found
    """
    # Create a new session
    with Session() as session:
        # Retrieve the draft to ensure it exists
        draft = session.query(Draft).filter(Draft.draft_id == draftId).first()

        if draft is None:
            abort(404, description="Draft not found")

        # Determine if the league is FIM
        isFiM = draft.league.is_fim
        eventKey = draft.event_key
        year = draft.league.year
        
        if isFiM:
            stmt = text(f"""
                SELECT DISTINCT CAST(teams.team_number AS INT) AS team_number
                FROM teams
                JOIN teamscore ON teams.team_number = teamscore.team_key
                JOIN frcevent ON teamscore.event_key = frcevent.event_key
                WHERE teams.is_fim = {isFiM}
                AND frcevent.year = {year}
                AND teams.team_number NOT IN (
                    SELECT team_number FROM draftpick
                    WHERE draft_id = :draftId
                    AND NOT team_number = '-1'
                )
                ORDER BY CAST(teams.team_number AS INT) ASC
            """)
        else:
            stmt = text(f"""
                SELECT DISTINCT team_key AS team_number
                FROM teamscore
                WHERE event_key = :eventKey
                AND team_key NOT IN (
                    SELECT team_number FROM draftpick
                    WHERE draft_id = :draftId
                    AND NOT team_number = '-1'
                )
                ORDER BY CAST(team_key AS INT) ASC
            """)
        
        # Execute the statement with parameters
        result = session.execute(stmt, {"draftId": draftId, "eventKey": eventKey}).fetchall()
        
        # Extract team numbers from the result
        available_teams = [row.team_number for row in result]
        
        return jsonify(available_teams)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Bind to all IPs
