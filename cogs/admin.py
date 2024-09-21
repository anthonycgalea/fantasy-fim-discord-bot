import discord, sqlalchemy
from discord import app_commands
from discord import Embed
from discord.ext import commands
from sqlalchemy import select
from sqlalchemy.sql import text
import requests
import logging
import traceback
import os
import asyncio
import random
import cogs.drafting as drafting
from models.users import Player
from models.scores import Team, League, FRCEvent, TeamScore, FantasyTeam, PlayerAuthorized
from models.draft import Draft, DraftOrder, DraftPick

logger = logging.getLogger('discord')
TBA_API_ENDPOINT = "https://www.thebluealliance.com/api/v3/"
TBA_AUTH_KEY = os.getenv("TBA_API_KEY")



class Admin(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    
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

  def getLeagueId(self):
    stmt = text("select max(league_id) from league")
    result = self.bot.session.execute(stmt).first()[0]
    if not result == None:
      return int(result) + 1
    else:
      return 1
    
  def getFantasyTeamId(self):
    stmt = text("select max(fantasy_team_id) from fantasyteam")
    result = self.bot.session.execute(stmt).first()[0]
    if not result == None:
      return int(result) + 1
    else:
      return 1
    
  def getDraftId(self):
    stmt = text("select max(draft_id) from draft")
    result = self.bot.session.execute(stmt).first()[0]
    if not result == None:
      return int(result) + 1
    else:
      return 1

  @app_commands.command(name="updateteamlist", description="Grabs all teams from TBA")
  async def updateTeamList(self, interaction: discord.Interaction, startpage: int):    
    if (await self.verifyAdmin(interaction)):
      asyncio.create_task(self.updateTeamsTask(interaction, startpage))
      
  @app_commands.command(name="addleague", description="Create a new league")
  async def createLeague(self, interaction: discord.Interaction, league_name: str, team_limit: int, team_starts: int, offseason: bool, year: int, is_fim: bool):
    if (await self.verifyAdmin(interaction)):      
      leagueToAdd = League(league_id=self.getLeagueId(), league_name=league_name, team_limit=team_limit,\
                           team_starts=team_starts, offseason=offseason, is_fim=is_fim, year=year)
      session = await self.bot.get_session()
      session.add(leagueToAdd)
      session.commit()
      await interaction.response.send_message(f"League created successfully! League Id: " +\
                                              str(leagueToAdd.league_id))
      session.close()

  @app_commands.command(name="registerteam", description="Register Fantasy Team")
  async def registerTeam(self, interaction:discord.Interaction, leagueid: int, teamname: str):
    if (await self.verifyAdmin(interaction)):
      session = await self.bot.get_session()
      leagues = session.query(League).filter(League.league_id==leagueid)
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

  @app_commands.command(name="populateleague", description="Populates a League to the max amount of teams with generic teams")
  async def populateLeague(self, interaction:discord.Interaction, leagueid: int):
      if (await self.verifyAdmin(interaction)):
        session = await self.bot.get_session()
        leagues = session.query(League).filter(League.league_id==leagueid)
        if (leagues.count() == 0):
          await interaction.response.send_message(f"No leagues exist with id {leagueid}.")
        teamsInLeague = session.query(FantasyTeam).filter(FantasyTeam.league_id==leagueid)
        teamLimit = leagues.first().team_limit
        if (teamLimit <= teamsInLeague.count()):
          await interaction.response.send_message(f"League with id {leagueid} is at max capacity.") 
          return
        while(teamLimit > teamsInLeague.count()):
          fantasyTeamToAdd = FantasyTeam(fantasy_team_id=self.getFantasyTeamId(), fantasy_team_name=f"Team {self.getFantasyTeamId()}", league_id=leagueid)
          session.add(fantasyTeamToAdd)
          session.commit()
          teamsInLeague = session.query(FantasyTeam).filter(FantasyTeam.league_id==leagueid)
        await interaction.response.send_message(f"Teams created successfully in league with id {leagueid}.")
        session.close()

  @app_commands.command(name="createdraft", description="Creates a fantasy draft for a given League and populates it with picks")
  async def createDraft(self, interaction:discord.Interaction, leagueid: int, rounds: int, event_key: str):
    if (await self.verifyAdmin(interaction)):
      session = await self.bot.get_session()
      leagues = session.query(League).filter(League.league_id==leagueid).filter(League.active == True)
      if (leagues.count() == 0):
        await interaction.response.send_message(f"No active leagues exist with id {leagueid}.")
        return
      
      teamsInLeague = session.query(FantasyTeam).filter(FantasyTeam.league_id==leagueid)
      if (teamsInLeague.count() == 0):
        await interaction.response.send_message(f"Cannot create draft with no teams to draft")
        return
      if (leagues.first().team_starts > rounds):
        await interaction.response.send_message(f"Don't have enough rounds to draft!")
        return
      draftToCreate = Draft(draft_id=self.getDraftId(), league_id=leagueid, rounds=rounds, event_key=event_key)
      session.add(draftToCreate)
      session.commit()
      await interaction.response.send_message(f"Draft generated! Draft id {draftToCreate.draft_id}")
      #generate draft order
      draftOrderEmbed = Embed(title=f"**Draft order for league id {leagueid}**", description="```Draft Slot    Team Name (id)\n")
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
      await interaction.channel.send(embed=draftOrderEmbed)
      session.commit()
      session.close()      

  @app_commands.command(name="startdraft", description="Starts the draft with the provided id")
  async def startDraft(self, interaction:discord.Interaction, draftid: int):
    if (await self.verifyAdmin(interaction)):
      session = await self.bot.get_session()
      drafts = session.query(Draft).filter(Draft.draft_id==draftid)
      if (drafts.count() == 0):
        await interaction.response.send_message(f"No drafts exist with id {draftid}.")
        return
      draftOrders = session.query(DraftOrder).filter(DraftOrder.draft_id==draftid)
      if (draftOrders.count() == 0):
        await interaction.response.send_message(f"Error generating draft picks.")
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
      session.close()
      await interaction.response.send_message(f"Draft rounds generated!") 

  @app_commands.command(name="updateevents", description="Update events for a given year")
  async def updateEvents(self, interaction: discord.Interaction, year: int):
    if (await self.verifyAdmin(interaction)):
      asyncio.create_task(self.updateEventsTask(interaction, year))
    
  @app_commands.command(name="importoffseasonevent", description="Imports offseason event and team list from TBA")
  async def importOffseasonEvent(self, interaction: discord.Interaction, eventkey: str):
    if (await self.verifyAdmin(interaction)):
      asyncio.create_task(self.importSingleEventTask(interaction, eventkey))

  @app_commands.command(name="importdistrict", description="Pull all registration data for district events and load db")
  async def importDistrict(self, interaction: discord.Interaction, district: str, year: str):
    if (await self.verifyAdmin(interaction)):
      asyncio.create_task(self.importFullDistrctTask(interaction, district, year))

  @app_commands.command(name="scoreweek", description="Score all teams that competed in a given week")
  async def scoreWeek(self, interaction:discord.Interaction, year: str, week: str):
    if (await self.verifyAdmin(interaction)):
      asyncio.create_task(self.scoreWeekTask(interaction, year, week))
  
  @app_commands.command(name="authorizeuser", description="Add an authorized user to a fantasy team")
  async def authorizeUser(self, interaction:discord.Interaction, fantasyteamid: int, user: discord.User):
    if (await self.bot.verifyTeamMember(fantasyteamid, interaction.user) or await self.verifyAdmin(interaction)):
      session = await self.bot.get_session()
      player = session.query(Player).filter(Player.user_id==str(user.id))
      if (player.count() == 0):
        session.add(Player(user_id=user.id, is_admin=False))
        session.commit()
      if not (await self.bot.verifyTeamMember(fantasyteamid, user)):
        authorizeToAdd = PlayerAuthorized(fantasy_team_id=fantasyteamid, player_id=user.id)
        session.add(authorizeToAdd)
        session.commit()
        session.close()
        fantasyTeam = session.query(FantasyTeam).filter(FantasyTeam.fantasy_team_id==fantasyteamid).first()
        await interaction.response.send_message(f"Successfully added <@{user.id}> to {fantasyTeam.fantasy_team_name}!")
      else:
        session.close()
        await interaction.response.send_message("You can't add someone already on it to your own team dummy!")
    
  @app_commands.command(name="forcepick", description="Admin ability to force a draft pick")
  async def forceDraftPick(self, interaction:discord.Interaction, draft_id: int, team_number: str):
    if (await self.verifyAdmin(interaction)):
      await interaction.response.send_message(f"Attempting to force pick team {team_number}.")
      draftCog = drafting.Drafting(self.bot)
      await draftCog.makeDraftPickHandler(interaction=interaction, draft_id=draft_id, team_number=team_number, force=True)
      

async def setup(bot: commands.Bot) -> None:
  cog = Admin(bot)
  guild = await bot.fetch_guild(int(os.getenv("GUILD_ID")))
  assert guild is not None

  await bot.add_cog(
      cog,
    guilds=[guild]
  )
