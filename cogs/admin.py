import discord, sqlalchemy
from discord import app_commands
from discord import Embed
from discord.ext import commands
from sqlalchemy import select, delete
from sqlalchemy.sql import text
import requests
import logging
import traceback
import os
import asyncio
import random, datetime
import cogs.drafting as drafting
import cogs.manageteam as manageteam
from models.users import Player
from models.scores import Team, League, FRCEvent, TeamScore, FantasyTeam, PlayerAuthorized, WeekStatus, TeamStarted, TeamOwned
from models.draft import Draft, DraftOrder, DraftPick, StatboticsData
from models.transactions import WaiverPriority, WaiverClaim, TeamOnWaivers

logger = logging.getLogger('discord')
TBA_API_ENDPOINT = "https://www.thebluealliance.com/api/v3/"
TBA_AUTH_KEY = os.getenv("TBA_API_KEY")
FORUM_CHANNEL_ID = os.getenv("DRAFT_FORUM_ID")
STATBOTICS_ENDPOINT = "https://api.statbotics.io/v3/team_year/"


class Admin(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    
  async def updateStatboticsTask(self, interaction, year):
    embed = Embed(title="Update Team List", description=f"Updating year end team data from Statbotics for {year}")
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    if (datetime.date.today().year < year or year < 2005):
      embed.description = "Invalid year. Please try again"
      await message.edit(embed=embed)
      return
    session = await self.bot.get_session()
    teams = session.query(Team).filter(Team.rookie_year <= year).all()
    i = 0
    session.query(StatboticsData).filter(StatboticsData.year==year).delete()
    teamcount = len(teams)
    for team in teams:
      try:
        requestURL = STATBOTICS_ENDPOINT+f"{team.team_number}/{year}"
        response = requests.get(requestURL)
        if response.status_code == 500:
          pass
        responsejson = response.json()
        unitlessEPA = int(responsejson["epa"]["unitless"])
        logger.info(f"Team number: {team.team_number} Year: {year} year_end_epa: {unitlessEPA}")
        session.add(StatboticsData(team_number=team.team_number, year=year, year_end_epa=unitlessEPA))
        session.commit()
      except Exception:
        logger.error(traceback.format_exc())
      i+=1
      if (i%50==0):
        embed.description=f"Processed {i}/{teamcount} Teams"
        await message.edit(embed=embed)
    session.close()

  async def updateTeamsTask(self, interaction, startPage):
    embed = Embed(title="Update Team List", description="Updating team list from The Blue Alliance")
    await interaction.response.send_message(embed=embed)
    reqheaders = {"X-TBA-Auth-Key": TBA_AUTH_KEY}
    session = await self.bot.get_session()
    teams = session.query(Team)
    i = startPage
    while(True):
      try:
        requestURL = TBA_API_ENDPOINT + "teams/" + str(i) 
        response = requests.get(requestURL, headers=reqheaders).json()
        if (len(response) == 0):
          break
        for team in response:
          teamNumber = str(team["team_number"])
          teamName = str(team["nickname"])
          rookieYear = team["rookie_year"]
          if teams.filter(Team.team_number == teamNumber).count() == 0:
            logger.info(f"Inserting team number {teamNumber}")
            isFiM = False
            if (team["state_prov"] == "Michigan"):
              isFiM = True
            teamToAdd = Team(team_number=teamNumber, name=teamName, is_fim=isFiM)
            session.add(teamToAdd)
          elif not (teams.filter(Team.team_number == teamNumber).first().name == teamName\
                    and teams.filter(Team.team_number==teamNumber).first().rookie_year==rookieYear): 
            logger.info(f"Updating team number {teamNumber}, team name {teamName}, rookie year {rookieYear}")
            teams.filter(Team.team_number == teamNumber).first().name = teamName
            teams.filter(Team.team_number == teamNumber).first().rookie_year = rookieYear
        i += 1
        embed.description = f"Updating team list: Processed {i*500} teams (Page {i})"
        await interaction.channel.send(embed = embed)
        session.commit()
      except Exception:
        embed.description = "Error updating team list from The Blue Alliance"
        await interaction.channel.send(embed = embed)
        logger.error(traceback.format_exc())
        return
    embed.description = "Updated team list from The Blue Alliance"
    await interaction.edit_original_response(embed = embed)
    session.close()

  async def updateEventsTask(self, interaction, year):
    embed = Embed(title="Update Event List", description=f"Updating event list for {year} from The Blue Alliance")
    newEventsEmbed = Embed(title="New Events", description="No new events")
    eventsLog = await self.bot.log_message("New Events", "No new events")
    await interaction.response.send_message(embed=embed)
    reqheaders = {"X-TBA-Auth-Key": TBA_AUTH_KEY}
    session = await self.bot.get_session()
    yearevents = session.query(FRCEvent).filter(FRCEvent.year == year)
    try:
      requestURL = TBA_API_ENDPOINT + "events/" + str(year)
      response = requests.get(requestURL, headers=reqheaders).json()
      totalEvents = len(response)
      i = 0
      for event in response:
        if (not event["event_type"] in [99, 100]):
          eventKey = str(event["key"])
          eventName = str(event["name"])
          if event["event_type"] in [3, 4]:
            week = 8
          else:
            week = str(event["week"]+1)
          filteredEvents = yearevents.filter(FRCEvent.event_key == eventKey)
          if filteredEvents.count() == 0:
            logger.info(f"Inserting event {eventKey}: {eventName}")
            newEventsEmbed.description = f"Found new event {eventKey}: {eventName}"
            eventsLog.edit(embed=newEventsEmbed)
            isFiM = False
            if (not event["district"] == None and event["district"]["abbreviation"] == "fim"):
              isFiM = True
            eventToAdd = FRCEvent(event_key=eventKey, event_name=eventName, year=year, week=week, is_fim=isFiM)
            session.add(eventToAdd)
          elif not (filteredEvents.first().event_name == eventName\
                    and str(filteredEvents.first().year) == str(year)\
                    and str(filteredEvents.first().week) == str(week)): 
            logger.info(f"Updating event {eventKey}")
            filteredEvents.first().event_name = eventName
            filteredEvents.first().year = year
            filteredEvents.first().week = week
        i+=1
        if (i%25 == 0):
          embed.description = f"Updating event list: Processed {i}/{totalEvents} events"
          await interaction.edit_original_response(embed = embed)
      session.commit()
    except Exception:
      logger.error(traceback.format_exc())
      embed.description = "Error updating event list from The Blue Alliance"
      await interaction.edit_original_response(embed = embed)
      return
    embed.description = "Updated event list from The Blue Alliance"
    await interaction.edit_original_response(embed = embed)
    session.close()

  async def importSingleEventTask(self, interaction, eventKey):
    embed = Embed(title=f"Import Event {eventKey}", description=f"Importing event info for key {eventKey} from The Blue Alliance")
    await interaction.response.send_message(embed = embed)
    reqheaders = {"X-TBA-Auth-Key": TBA_AUTH_KEY}
    session = await self.bot.get_session()
    eventResult = session.query(FRCEvent).filter(FRCEvent.event_key == eventKey)
    try:
      requestURL = TBA_API_ENDPOINT + "event/" + str(eventKey)
      response = requests.get(requestURL, headers=reqheaders).json()
      if (not "key" in response.keys()):
        await interaction.response.send_message(f"Event {eventKey} does not exist on The Blue Alliance")
        return
      eventKey = str(response["key"])
      eventName = str(response["name"])
      week=99
      year=eventKey[:4]
      if eventResult.count() == 0:
        logger.info(f"Inserting event {eventKey}: {eventName}")
        isFiM = False
        eventToAdd = FRCEvent(event_key=eventKey, event_name=eventName, year=year, week=week, is_fim=isFiM)
        session.add(eventToAdd)
      elif not (eventResult.first().event_name == eventName\
                and str(eventResult.first().year) == str(year)\
                and str(eventResult.first().week) == str(week)): 
        logger.info(f"Updating event {eventKey}")
        eventResult.first().event_name = eventName
        eventResult.first().year = year
        eventResult.first().week = week
      embed.description = f"Retrieving {eventKey} teams"
      await interaction.edit_original_response(embed=embed)
      requestURL += "/teams/simple"
      response = requests.get(requestURL, headers=reqheaders).json()
      teamscores = session.query(TeamScore).filter(TeamScore.event_key==eventKey)
      for team in response:
        teamNumber = str(team["team_number"])
        if teamscores.filter(TeamScore.team_key == teamNumber).count() == 0:
          logger.info(f"Team {teamNumber} registered for {eventKey}")
          teamScoreToAdd = TeamScore(team_key=teamNumber, event_key=eventKey)
          session.add(teamScoreToAdd)
      session.commit()
      embed.description = f"Retrieved all {eventKey} information"
      await interaction.edit_original_response(embed=embed)
      session.close()
    except Exception:
      embed.description = f"Error retrieving offseason event {eventKey} from The Blue Alliance"
      await interaction.edit_original_response(embed=embed)
      logger.error(traceback.format_exc())
      session.close()
      return

  async def importFullDistrctTask(self, interaction, district, year):
    embed = Embed(title=f"Importing {district} District", description=f"Importing event info for all {district} districts from The Blue Alliance")
    await interaction.response.send_message(embed = embed)
    newEventsEmbed = Embed(title="New Events", description="No new events")
    eventsLog = await self.bot.log_message("New Events", "No new events")
    reqheaders = {"X-TBA-Auth-Key": TBA_AUTH_KEY}
    session = await self.bot.get_session()
    try:
      requestURL = TBA_API_ENDPOINT + "district/" + str(year) + str(district) + "/events"
      response = requests.get(requestURL, headers=reqheaders).json()
      if (not isinstance(response, list)):
        embed.description = f"District {district} does not exist on The Blue Alliance"
        await interaction.edit_original_response(embed=embed)
        return
      numberOfEvents = len(response)
      i = 1
      for event in response:
        week=int(event["week"])+1
        if week < 6:
          eventKey = str(event["key"])
          eventName = str(event["name"])
          year=eventKey[:4]
          eventResult = session.query(FRCEvent).filter(FRCEvent.event_key == eventKey)
          if eventResult.count() == 0:
            logger.info(f"Inserting event {eventKey}: {eventName}")
            newEventsEmbed.description = f"Found new event {eventKey}: {eventName}"
            await eventsLog.edit(embed=newEventsEmbed)
            isFiM = False
            eventToAdd = FRCEvent(event_key=eventKey, event_name=eventName, year=year, week=week, is_fim=isFiM)
            session.add(eventToAdd)
          elif not (eventResult.first().event_name == eventName\
                    and str(eventResult.first().year) == str(year)\
                    and str(eventResult.first().week) == str(week)): 
            logger.info(f"Updating event {eventKey}")
            eventResult.first().event_name = eventName
            eventResult.first().year = year
            eventResult.first().week = week
          embed.description = f"Retrieving {eventKey} teams (Event {i}/{numberOfEvents})"
          await interaction.edit_original_response(embed=embed)
          requestURL = TBA_API_ENDPOINT + "event/" + str(eventKey) + "/teams/simple"
          response = requests.get(requestURL, headers=reqheaders).json()
          teamscores = session.query(TeamScore).filter(TeamScore.event_key==eventKey)
          teamlist = set()
          teamRegistrationChangeEmbed = None
          teamRegistrationChangeMsg = None
          embedSentYet=False
          for team in response:
            teamNumber = str(team["team_number"])
            teamlist.add(teamNumber)
            if teamscores.filter(TeamScore.team_key == teamNumber).count() == 0:
              if not embedSentYet:
                teamRegistrationChangeMsg = await self.bot.log_message(f"{eventKey} registration changes", f"Team {teamNumber} registered for {eventKey}")
                teamRegistrationChangeEmbed = Embed(title=f"{eventKey} registration changes", description=f"Team {teamNumber} registered for {eventKey}")
                embedSentYet = True
              else:
                teamRegistrationChangeEmbed.description+=f"\nTeam {teamNumber} registered for {eventKey}"
                await teamRegistrationChangeMsg.edit(embed=teamRegistrationChangeEmbed)
              logger.info(f"Team {teamNumber} registered for {eventKey}")
              teamScoreToAdd = TeamScore(team_key=teamNumber, event_key=eventKey)
              session.add(teamScoreToAdd)
          for team in teamscores.all():
            if not str(team.team_key) in teamlist:
              logger.info(f"Team {team.team_key} un-registered from {team.event_key}")
              session.delete(team)
              if not embedSentYet:
                teamRegistrationChangeMsg = await self.bot.log_message(f"{eventKey} registration changes", f"Team {team.team_key} un-registered from {team.event_key}")
                teamRegistrationChangeEmbed = Embed(title=f"{eventKey} registration changes", description=f"Team {team.team_key} un-registered from {team.event_key}")
                embedSentYet = True
              else:
                teamRegistrationChangeEmbed.description+=f"Team {team.team_key} un-registered from {team.event_key}"
                await teamRegistrationChangeMsg.edit(embed=teamRegistrationChangeEmbed)
        i+=1
      session.commit()
      embed.description = f"Retrieved all {district} information"
      await interaction.edit_original_response(embed=embed)
      session.close()
    except Exception:
      embed.description = f"Error retrieving offseason event {eventKey} from The Blue Alliance"
      await interaction.edit_original_response(embed=embed)
      logger.error(traceback.format_exc())
      session.close()
      return

  async def scoreWeekTask(self, interaction: discord.Interaction, year, week):
    session = await self.bot.get_session()
    weekStatus = session.query(WeekStatus).filter(WeekStatus.week==week).filter(WeekStatus.year==year)
    if (weekStatus.count() == 0):
      await interaction.response.send_message("No week to score.")
      return
    elif (weekStatus.first().scores_finalized == True):
      await interaction.response.send_message("Scores are already finalized.")
      return
    eventsToScore = session.query(FRCEvent).filter(FRCEvent.year==year).filter(FRCEvent.is_fim==True).filter(FRCEvent.week==week)
    embed = Embed(title=f"Scoring week {week} for {year}", description=f"Importing event info for all {year} week {week} districts from The Blue Alliance")
    await interaction.response.send_message(embed = embed)
    embed.description = ""
    logger.info(f"Events to score: {eventsToScore.count()}")
    for event in eventsToScore.all():
      requestURL = TBA_API_ENDPOINT + "event/" + event.event_key + "/district_points"
      reqheaders = {"X-TBA-Auth-Key": TBA_AUTH_KEY}
      eventresponse = requests.get(requestURL, headers=reqheaders).json()
      currentScores = session.query(TeamScore).filter(TeamScore.event_key==event.event_key)
      for team in eventresponse["points"]:
        teamscore = None
        if currentScores.filter(TeamScore.team_key==team[3:]).count() == 0:
          teamscore = TeamScore(team_key=team[3:], event_key=event.event_key)
          session.add(teamscore)
        else:
          teamscore = currentScores.filter(TeamScore.team_key==team[3:]).first()
        teamscore.qual_points=eventresponse["points"]["frc"+teamscore.team_key]["qual_points"]
        teamscore.alliance_points=eventresponse["points"]["frc"+teamscore.team_key]["alliance_points"]
        teamscore.elim_points=eventresponse["points"]["frc"+teamscore.team_key]["elim_points"]
        teamscore.award_points=eventresponse["points"]["frc"+teamscore.team_key]["award_points"]
        if (teamscore.award_points == 10):
          teamscore.award_points += 10
        elif(teamscore.award_points == 30):
          teamscore.award_points += 30
        team = session.query(Team).filter(Team.team_number==teamscore.team_key).first()
        if (not week == 6):
          if (int(team.rookie_year) == int(year)):
            teamscore.rookie_points = 5
          elif (int(team.rookie_year) == int(year)-1):
            teamscore.rookie_points = 2
        embed.description += f"Successfully scored **{event.event_name}**\n"
      await interaction.edit_original_response(embed=embed)
      session.commit() 
    embed.description += f"**All events scored for week {week}**"
    await interaction.edit_original_response(embed=embed)
    session.close()

  async def verifyAdmin(self, interaction: discord.Interaction):
    stmt = select(Player).where(Player.user_id == str(interaction.user.id))
    users = self.bot.session.execute(stmt)
    if (users.rowcount == 0 or not users.first().is_admin):
      await interaction.response.send_message("You are not authorized to use this command.")
      return False
    else:
      return True
    
  async def getForum(self):
    return self.bot.get_channel(int(FORUM_CHANNEL_ID))

  def getLeagueId(self): #league id generation for primary key
    stmt = text("select max(league_id) from league")
    result = self.bot.session.execute(stmt).first()[0]
    if not result == None:
      return int(result) + 1
    else:
      return 1
    
  def getFantasyTeamId(self): #fantasy team id generation for primary key
    stmt = text("select max(fantasy_team_id) from fantasyteam")
    result = self.bot.session.execute(stmt).first()[0]
    if not result == None:
      return int(result) + 1
    else:
      return 1
    
  def getDraftId(self): #draft id generation for primary key
    stmt = text("select max(draft_id) from draft")
    result = self.bot.session.execute(stmt).first()[0]
    if not result == None:
      return int(result) + 1
    else:
      return 1

  async def getFantasyTeamIdFromUserAndInteraction(self, interaction: discord.Interaction, user: discord.User):
        session = await self.bot.get_session()
        largeQuery = session.query(FantasyTeam)\
            .join(PlayerAuthorized, FantasyTeam.fantasy_team_id == PlayerAuthorized.fantasy_team_id)\
            .join(League, FantasyTeam.league_id == League.league_id)\
            .filter(PlayerAuthorized.player_id == str(user.id))\
            .filter(League.discord_channel == str(interaction.channel_id))
        team = largeQuery.first()
        session.close()
        if team:
            return team.fantasy_team_id
        else:
            return None

  @app_commands.command(name="updateteamlist", description="Grabs all teams from TBA (ADMIN)")
  async def updateTeamList(self, interaction: discord.Interaction, startpage: int = 0):    
    if (await self.verifyAdmin(interaction)):
      asyncio.create_task(self.updateTeamsTask(interaction, startpage))
      
  @app_commands.command(name="addleague", description="Create a new league (ADMIN)")
  async def createLeague(self, interaction: discord.Interaction, league_name: str, team_limit: int, year: int, is_fim: bool = False, team_starts: int = 3, offseason: bool = False, team_size_limit: int = 3):
    if (await self.verifyAdmin(interaction)):
      forum = await self.getForum()
      nameOfDraft = f"{league_name} League Thread"
      thread = (await forum.create_thread(content="test",name=nameOfDraft))[0]
      threadId = thread.id      
      leagueToAdd = League(league_id=self.getLeagueId(), league_name=league_name, team_limit=team_limit,\
                           team_starts=team_starts, offseason=offseason, is_fim=is_fim, year=year, discord_channel=threadId, team_size_limit=team_size_limit)
      session = await self.bot.get_session()
      session.add(leagueToAdd)
      session.commit()
      await interaction.response.send_message(f"League created successfully! <#{threadId}>")
      session.close()

  @app_commands.command(name="registerteam", description="Register Fantasy Team (ADMIN)")
  async def registerTeam(self, interaction:discord.Interaction, teamname: str):
    if (await self.verifyAdmin(interaction)):
      session = await self.bot.get_session()
      leagues = session.query(League).filter(League.discord_channel==str(interaction.channel_id))
      leagueid = leagues.first().league_id
      teamsInLeague = session.query(FantasyTeam).filter(FantasyTeam.league_id==leagueid)
      if (leagues.count() == 0):
        await interaction.response.send_message(f"No leagues exist with id {leagueid}.")
        return
      elif (leagues.first().team_limit <= teamsInLeague.count()):
        await interaction.response.send_message(f"League with id {leagueid} is at max capacity.") 
        return
      fantasyTeamToAdd = FantasyTeam(fantasy_team_id=self.getFantasyTeamId(), fantasy_team_name=teamname, league_id=leagueid)
      session = await self.bot.get_session()
      session.add(fantasyTeamToAdd)
      session.commit()
      session.close()
      await interaction.response.send_message(f"Team {teamname} created successfully in league with id {leagueid}. Team id is {fantasyTeamToAdd.fantasy_team_id}")

  @app_commands.command(name="fillleague", description="Populates a League to the max amount of teams with generic teams (ADMIN)")
  async def populateLeague(self, interaction:discord.Interaction):
      if (await self.verifyAdmin(interaction)):
        session = await self.bot.get_session()
        leagues = session.query(League).filter(League.discord_channel==str(interaction.channel_id))
        if (leagues.count() == 0):
          await interaction.response.send_message(f"No league exists in this channel.")
        leagueid = leagues.first().league_id
        teamsInLeague = session.query(FantasyTeam).filter(FantasyTeam.league_id==leagueid)
        teamLimit = leagues.first().team_limit
        if (teamLimit <= teamsInLeague.count()):
          await interaction.response.send_message(f"League is at max capacity.") 
          return
        while(teamLimit > teamsInLeague.count()):
          fantasyTeamToAdd = FantasyTeam(fantasy_team_id=self.getFantasyTeamId(), fantasy_team_name=f"Team {self.getFantasyTeamId()}", league_id=leagueid)
          session.add(fantasyTeamToAdd)
          session.commit()
          teamsInLeague = session.query(FantasyTeam).filter(FantasyTeam.league_id==leagueid)
        await interaction.response.send_message(f"Teams created successfully!.")
        session.close()

  @app_commands.command(name="createdraft", description="Creates a fantasy draft for a given League and populates it with picks (ADMIN)")
  async def createDraft(self, interaction:discord.Interaction, event_key: str):
    if (await self.verifyAdmin(interaction)):
      session = await self.bot.get_session()
      leagues = session.query(League).filter(League.discord_channel==str(interaction.channel_id)).filter(League.active == True)
      rounds = leagues.first().team_size_limit
      if (leagues.count() == 0):
        await interaction.response.send_message(f"No active leagues exist in current channel.")
        return
      leagueid = leagues.first().league_id
      teamsInLeague = session.query(FantasyTeam).filter(FantasyTeam.league_id==leagueid)
      if (teamsInLeague.count() == 0):
        await interaction.response.send_message(f"Cannot create draft with no teams to draft")
        return
      if (leagues.first().team_starts > rounds):
        await interaction.response.send_message(f"Don't have enough rounds to draft!")
        return
      forum = await self.getForum()
      nameOfDraft = f"{leagues.first().league_name} draft for {event_key}"
      thread = (await forum.create_thread(content="test",name=nameOfDraft))[0]
      threadId = thread.id
      draftToCreate = Draft(draft_id=self.getDraftId(), league_id=leagueid, rounds=rounds, event_key=event_key, discord_channel=threadId)
      session.add(draftToCreate)
      session.commit()
      await interaction.response.send_message(f"Draft generated! <#{threadId}>")
      #generate draft order
      draftOrderEmbed = Embed(title=f"**Draft order**", description="```Draft Slot    Team Name (id)\n")
      randomizedteams = [fantasyTeam.fantasy_team_id for fantasyTeam in teamsInLeague]
      random.shuffle(randomizedteams)
      i = 1
      for team in randomizedteams:
        draftOrder = DraftOrder(draft_id = draftToCreate.draft_id, draft_slot = i, fantasy_team_id=team)
        teamname = teamsInLeague.filter(FantasyTeam.fantasy_team_id==team).first().fantasy_team_name
        draftOrderEmbed.description+=f"{i:>10d}    {teamname} ({team})\n"
        session.add(draftOrder)
        i+=1
      draftOrderEmbed.description+="```"
      await thread.send(embed=draftOrderEmbed)
      session.commit()
      session.close()      

  @app_commands.command(name="startdraft", description="Starts the draft in the current channel (ADMIN)")
  async def startDraft(self, interaction:discord.Interaction):
    if (await self.verifyAdmin(interaction)):
      session = await self.bot.get_session()
      drafts = session.query(Draft).filter(Draft.discord_channel==str(interaction.channel_id))
      if (drafts.count() == 0):
        await interaction.response.send_message(f"This is not an active draft channel.")
        return
      await interaction.response.send_message(f"Generating draft picks")
      message = await interaction.original_response()
      draftid = drafts.first().draft_id
      draftOrders = session.query(DraftOrder).filter(DraftOrder.draft_id==draftid)
      if (draftOrders.count() == 0):
        await message.edit(content=f"Error generating draft picks.")
        return
      for teamDraftOrder in draftOrders.all():
        for k in range(drafts.first().rounds):
          pickNumber = k*draftOrders.count()
          if k%2 == 0: #handle serpentine
            pickNumber += teamDraftOrder.draft_slot
          else:
            pickNumber += (draftOrders.count()-teamDraftOrder.draft_slot)+1
          draftPickToAdd = DraftPick(draft_id=draftid, fantasy_team_id=teamDraftOrder.fantasy_team_id, pick_number=pickNumber, team_number=-1)
          session.add(draftPickToAdd)
      session.commit()
      await message.edit(content=f"Draft rounds generated!") 
      session.close()
      draftCog = drafting.Drafting(self.bot)
      await draftCog.postDraftBoard(interaction=interaction)

  @app_commands.command(name="resetdraft", description="Resets an already started draft. (ADMIN)")
  async def resetDraft(self, interaction:discord.Interaction):
    if (await self.verifyAdmin(interaction)):
      session = await self.bot.get_session()
      drafts = session.query(Draft).filter(Draft.discord_channel==str(interaction.channel_id))
      if (drafts.count() == 0):
        await interaction.response.send_message(f"This is not a draft channel.")
        return
      draftid = drafts.first().draft_id
      session.query(DraftPick).filter(DraftPick.draft_id==draftid).delete()
      session.commit()
    await interaction.response.send_message(f"Successfully reset draft! Use command /startdraft to restart the draft.")

  @app_commands.command(name="updateevents", description="Update events for a given year (ADMIN)")
  async def updateEvents(self, interaction: discord.Interaction, year: int):
    if (await self.verifyAdmin(interaction)):
      asyncio.create_task(self.updateEventsTask(interaction, year))
    
  @app_commands.command(name="importoffseasonevent", description="Imports offseason event and team list from TBA (ADMIN)")
  async def importOffseasonEvent(self, interaction: discord.Interaction, eventkey: str):
    if (await self.verifyAdmin(interaction)):
      asyncio.create_task(self.importSingleEventTask(interaction, eventkey))

  @app_commands.command(name="importdistrict", description="Pull all registration data for district events and load db (ADMIN)")
  async def importDistrict(self, interaction: discord.Interaction, year: str, district: str = "fim"):
    if (await self.verifyAdmin(interaction)):
      asyncio.create_task(self.importFullDistrctTask(interaction, district, year))

  @app_commands.command(name="scoreweek", description="Score all teams that competed in a given week (ADMIN)")
  async def scoreWeek(self, interaction:discord.Interaction, year: str, week: str):
    if (await self.verifyAdmin(interaction)):
      asyncio.create_task(self.scoreWeekTask(interaction, year, week))
  
  @app_commands.command(name="authorize", description="Add an authorized user to a fantasy team (ADMIN)")
  async def authorizeUser(self, interaction:discord.Interaction, fantasyteamid: int, user: discord.User):
    if (await self.verifyAdmin(interaction)):
      session = await self.bot.get_session()
      player = session.query(Player).filter(Player.user_id==str(user.id))
      if (player.count() == 0):
        session.add(Player(user_id=user.id, is_admin=False))
        session.commit()
      if not (await self.bot.verifyTeamMemberByTeamId(fantasyteamid, user)):
        authorizeToAdd = PlayerAuthorized(fantasy_team_id=fantasyteamid, player_id=user.id)
        session.add(authorizeToAdd)
        session.commit()
        session.close()
        fantasyTeam = session.query(FantasyTeam).filter(FantasyTeam.fantasy_team_id==fantasyteamid).first()
        await interaction.response.send_message(f"Successfully added <@{user.id}> to {fantasyTeam.fantasy_team_name}!", ephemeral=True)
      else:
        session.close()
        await interaction.response.send_message("You can't add someone already on it to their own team dummy!", ephemeral=True)
    
  @app_commands.command(name="forcepick", description="Admin ability to force a draft pick (ADMIN)")
  async def forceDraftPick(self, interaction:discord.Interaction, team_number: str):
    if (await self.verifyAdmin(interaction)):
      await interaction.response.send_message(f"Attempting to force pick team {team_number}.")
      draftCog = drafting.Drafting(self.bot)
      await draftCog.makeDraftPickHandler(interaction=interaction, team_number=team_number, force=True)

  @app_commands.command(name="autopick", description="Admin ability to force an auto draft pick (ADMIN)")    
  async def forceAutoPick(self, interaction:discord.Interaction):
    if (await self.verifyAdmin(interaction)):
      await interaction.response.send_message(f"Attempting to force pick best available team.")
      draftCog = drafting.Drafting(self.bot)
      draft: Draft = await draftCog.getDraftFromChannel(interaction=interaction)
      if (draft == None):
          await interaction.channel.send(content="No draft associated with this channel.")
          return
      league: League = await draftCog.getLeague(draft_id=draft.draft_id)
      suggestedTeams = await draftCog.getSuggestedTeamsList(eventKey=draft.event_key, year=league.year, isFiM=league.is_fim, draft_id=draft.draft_id)
      teamToPick = suggestedTeams[0][0]
      await draftCog.makeDraftPickHandler(interaction=interaction, team_number=teamToPick, force=True)

  @app_commands.command(name="statboticsupdate", description="Updates cache of Statbotics data (ADMIN)")    
  async def updateStatbotics(self, interaction:discord.Interaction, year: int):
    if (await self.verifyAdmin(interaction)):
      asyncio.create_task(self.updateStatboticsTask(interaction, year))

  @app_commands.command(name="deauthplayer", description="Remove a player from a team (ADMIN)")
  async def deauthPlayer(self, interaction:discord.Interaction, user: discord.User):
    if (await self.verifyAdmin(interaction)):
      if not await self.bot.verifyNotInLeague(interaction, user):
        session = await self.bot.get_session()
        fantasyId = await self.getFantasyTeamIdFromUserAndInteraction(interaction, user)
        playerAuthToDelete = session.query(PlayerAuthorized).filter(PlayerAuthorized.player_id==str(user.id)).filter(PlayerAuthorized.fantasy_team_id==fantasyId)
        playerAuthToDelete.delete()
        session.commit()
        session.close()
        await interaction.response.send_message(f"Successfully removed <@{user.name}> from league.", ephemeral=True)
      else:
        await interaction.response.send_message("Player is not on a team.")

  @app_commands.command(name="forcestart", description="Admin ability to force a team into a starting lineup (ADMIN)")
  async def forceStart(self, interaction:discord.Interaction, fantasyteamid: int, week: int, team_number: str):
    if (await self.verifyAdmin(interaction)):
      await interaction.response.send_message(f"Attempting to force start team {team_number}.")
      manageTeamCog = manageteam.ManageTeam(self.bot)
      await manageTeamCog.startTeamTask(interaction, team_number, week, fantasyteamid)

  @app_commands.command(name="forcesit", description="Admin ability to force a team out of a starting lineup (ADMIN)")
  async def forceSit(self, interaction:discord.Interaction, fantasyteamid: int, week: int, team_number: str):
    if (await self.verifyAdmin(interaction)):
      await interaction.response.send_message(f"Attempting to force sit team {team_number}.")
      manageTeamCog = manageteam.ManageTeam(self.bot)
      await manageTeamCog.sitTeamTask(interaction, team_number, week, fantasyteamid)

  @app_commands.command(name="viewteamlineup", description="Admin ability to view a team's starting lineup (ADMIN)")
  async def viewStartingLineup(self, interaction:discord.Interaction, fantasyteamid: int):
    if (await self.verifyAdmin(interaction)):
      await interaction.response.send_message(f"Attempting to view starting lineup of team {fantasyteamid}.")
      manageTeamCog = manageteam.ManageTeam(self.bot)
      await manageTeamCog.viewStartsTask(interaction, fantasyteamid)

  @app_commands.command(name="adminrenameteam", description="Admin ability to rename a team (ADMIN)")
  async def renameFantasyTeam(self, interaction:discord.Interaction, fantasyteamid: int, newname: str):
    if (await self.verifyAdmin(interaction)):
      await interaction.response.send_message(f"Attempting to rename team {fantasyteamid} to {newname}.")
      manageTeamCog = manageteam.ManageTeam(self.bot)
      await manageTeamCog.renameTeamTask(interaction, fantasyId=fantasyteamid, newname=newname)

  @app_commands.command(name="locklineups", description="Admin ability to lock lineups for the week (ADMIN)")
  async def lockLineups(self, interaction:discord.Interaction):
    if (await self.verifyAdmin(interaction)):
      currentWeek = await self.bot.getCurrentWeek()
      if currentWeek == None:
        await interaction.response.send_message("No active week")
        return
      session = await self.bot.get_session()
      weekToMod = session.query(WeekStatus).filter(WeekStatus.year==currentWeek.year).filter(WeekStatus.week==currentWeek.week).first()
      weekToMod.lineups_locked=True
      session.commit()
      session.close()
      await interaction.response.send_message(f"Locked lineups for week {currentWeek.week} in {currentWeek.year}")

  @app_commands.command(name="finishweek", description="Admin ability to deactivate the currently active week (ADMIN)")
  async def finishWeek(self, interaction:discord.Interaction):
    if (await self.verifyAdmin(interaction)):
      currentWeek = await self.bot.getCurrentWeek()
      if currentWeek == None:
        await interaction.response.send_message("No active week")
        return
      session = await self.bot.get_session()
      weekToMod = session.query(WeekStatus).filter(WeekStatus.year==currentWeek.year).filter(WeekStatus.week==currentWeek.week).first()
      weekToMod.active=False
      session.commit()
      session.close()
      await interaction.response.send_message(f"Deactivated week {currentWeek.week} in {currentWeek.year}")

  @app_commands.command(name="finalizescores", description="Admin ability to deactivate the currently active week (ADMIN)")
  async def finalizeScores(self, interaction:discord.Interaction, week: int):
    if (await self.verifyAdmin(interaction)):
      currentWeek = await self.bot.getCurrentWeek()
      if currentWeek == None:
        await interaction.response.send_message("No active season")
        return
      session = await self.bot.get_session()
      weekToMod = session.query(WeekStatus).filter(WeekStatus.year==currentWeek.year).filter(WeekStatus.week==week).first()
      weekToMod.active=False
      session.commit()
      session.close()
      await interaction.response.send_message(f"Finalized week {currentWeek.week} scores in {currentWeek.year}")
  
  @app_commands.command(name="remind", description="Remind players to set their lineups (ADMIN)")
  async def remindPlayers(self, interaction:discord.Interaction):
    if (await self.verifyAdmin(interaction)):
      await interaction.response.send_message("Reminding all users with unfilled lineups to fill them.")
      session = await self.bot.get_session()
      leagues = session.query(League).where(League.active == True)
      if (leagues.count() == 0):
        await interaction.channel.send(content="There are no active leagues!")
      else:  
        for league in leagues.all():
          sendReminder = False
          reminderMessage = "Teams with unfilled lineups:\n"
          leagueTeams = session.query(FantasyTeam).where(FantasyTeam.league_id==league.league_id)
          for team in leagueTeams.all():
            numberOfStarters = session.query(TeamStarted).filter(TeamStarted.fantasy_team_id == team.fantasy_team_id)
            if (numberOfStarters.count() < league.team_starts):
              sendReminder = True
              playersToNotify = session.query(PlayerAuthorized).filter(PlayerAuthorized.fantasy_team_id == team.fantasy_team_id)
              reminderMessage+=f"{team.fantasy_team_name} "
              for player in playersToNotify.all():
                reminderMessage+=f"<@{player.player_id}> "
              reminderMessage+=f"currently starting {numberOfStarters.count()} of {league.team_starts}\n"
          if sendReminder:
            channel = await self.bot.fetch_channel(int(league.discord_channel))
            if not channel == None:
              await channel.send(content=reminderMessage)
      session.close()

  @app_commands.command(name="processwaivers", description="Process all waivers (ADMIN)")
  async def processWaivers(self, interaction: discord.Interaction):
    if (await self.verifyAdmin(interaction)):
      await interaction.response.send_message(f"Attempting to process waivers")
      message = await interaction.original_response()
      session = await self.bot.get_session()
      leagues = session.query(League).where(League.active == True)
      week: WeekStatus = await self.bot.getCurrentWeek()
      if (week.waivers_complete):
        await message.edit("Waivers are already complete for this week.")
        return
      if (leagues.count() == 0):
        await message.edit(content="There are no active leagues!")
      else:  
        for league in leagues.all():
          waiverReportEmbed = Embed(title=f"**{league.league_name} Week {week.week} Waiver Report**", description="")
          waiverClaims = session.query(WaiverClaim).filter(WaiverClaim.league_id==league.league_id)
          if (waiverClaims.count() > 0):
            waiverNum=1
            waiverPriorities = session.query(WaiverPriority).filter(WaiverPriority.league_id==league.league_id).order_by(WaiverPriority.priority.asc())
            lastTeam = waiverPriorities.count()
            while(waiverNum <= lastTeam):
              waiverPriorities = session.query(WaiverPriority).filter(WaiverPriority.league_id==league.league_id).order_by(WaiverPriority.priority.asc())
              currentPriority = waiverPriorities.filter(WaiverPriority.priority==waiverNum)
              priorityToCheck = currentPriority.first()
              fantasyTeam: FantasyTeam = priorityToCheck.fantasy_team
              waiverClaims = session.query(WaiverClaim).filter(WaiverClaim.fantasy_team_id==fantasyTeam.fantasy_team_id).order_by(WaiverClaim.priority.asc())
              if (waiverClaims.count() > 0):
                for waiverclaim in waiverClaims.all():
                  isTeamOnWaivers = session.query(TeamOnWaivers).filter(TeamOnWaivers.league_id==league.league_id).filter(TeamOnWaivers.team_number==waiverclaim.team_claimed)
                  isDropTeamOnRoster = session.query(TeamOwned).filter(TeamOwned.fantasy_team_id==fantasyTeam.fantasy_team_id).filter(TeamOwned.team_key==waiverclaim.team_to_drop)
                  if (isTeamOnWaivers.count() > 0 and isDropTeamOnRoster.count() > 0):
                    newWaiver = TeamOnWaivers(league_id=fantasyTeam.league_id, team_number=waiverclaim.team_to_drop)
                    session.add(newWaiver)
                    isTeamOnWaivers.delete()
                    session.flush()
                    session.query(TeamStarted).filter(TeamStarted.league_id==fantasyTeam.league_id)\
                    .filter(TeamStarted.team_number==waiverclaim.team_to_drop).filter(TeamStarted.week >= week.week).delete()
                    session.flush()
                    session.query(TeamOwned).filter(TeamOwned.league_id==fantasyTeam.league_id).filter(TeamOwned.team_key==waiverclaim.team_to_drop).delete()
                    draftSoNotFail: Draft = session.query(Draft).filter(Draft.league_id==fantasyTeam.league_id).filter(Draft.event_key=="fim").first()
                    session.flush()
                    newTeamToAdd = TeamOwned(
                        team_key=str(waiverclaim.team_claimed),
                        fantasy_team_id=fantasyTeam.fantasy_team_id,
                        league_id=fantasyTeam.league_id,
                        draft_id=draftSoNotFail.draft_id
                    )
                    session.add(newTeamToAdd)
                    session.flush()  
                    waiverReportEmbed.description+=f"{fantasyTeam.fantasy_team_name} successfully added team {waiverclaim.team_claimed} and dropped {waiverclaim.team_to_drop}!\n"
                    session.flush()
                    #move waiver priority
                    # Temporary placeholder value (e.g., set to -1 for the current priority)
                    priorityToCheck.priority = -1
                    session.flush()

                    # Now adjust all priorities (e.g., shift them down)
                    for prio in waiverPriorities.filter(WaiverPriority.priority > waiverNum).all():
                        prio.priority -= 1
                        session.flush()

                    # Finally, assign the last priority to the current team
                    priorityToCheck.priority = lastTeam
                    session.flush()
                    break
                  elif (isTeamOnWaivers.count() == 0):
                    waiverReportEmbed.description+=f"{fantasyTeam.fantasy_team_name} tried to claim team {waiverclaim.team_claimed}, however they are no longer on waivers, unable to process\n"
                    session.delete(waiverclaim)
                    session.flush()
                  else:
                    waiverReportEmbed.description+=f"{fantasyTeam.fantasy_team_name} tried to claim team {waiverclaim.team_claimed} but their designated drop team {waiverclaim.team_to_drop} is no longer on the team, unable to process\n"
                    session.delete(waiverclaim)
                    session.flush()
              else:
                waiverNum+=1
          else:
            waiverReportEmbed.description+="No waiver claims to process"
          channel = await self.bot.fetch_channel(int(league.discord_channel))
          if not channel == None:
            await channel.send(embed=waiverReportEmbed)
          session.query(TeamOnWaivers).filter(TeamOnWaivers.league_id==league.league_id).delete()
          session.flush()
      session.commit()
      session.close()

  @app_commands.command(name="forceadddrop", description="Force an add/drop (ADMIN)")
  async def forceAddDrop(self, interaction: discord.Interaction, fantasyteamid: int, addteam: str, dropteam: str, towaivers: bool = True):
    if (await self.verifyAdmin(interaction)):
      await interaction.response.send_message(f"Attempting to admin drop {dropteam} to add {addteam} from team id {fantasyteamid}", ephemeral=True)
      manageTeamCog = manageteam.ManageTeam(self.bot)
      await manageTeamCog.addDropTeamTask(interaction, addTeam=addteam,dropTeam=dropteam, fantasyId=fantasyteamid, force=True, toWaivers=towaivers)

async def setup(bot: commands.Bot) -> None:
  cog = Admin(bot)
  guild = await bot.fetch_guild(int(os.getenv("GUILD_ID")))
  assert guild is not None

  await bot.add_cog(
      cog,
    guilds=[guild]
  )
