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
from models.users import Player
from models.scores import Team, League, FRCEvent, TeamScore

logger = logging.getLogger('discord')
TBA_API_ENDPOINT = "https://www.thebluealliance.com/api/v3/"
TBA_AUTH_KEY = os.getenv("TBA_API_KEY")



class Admin(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    
  async def updateTeamsTask(self, interaction):
    embed = Embed(title="Update Team List", description="Updating team list from The Blue Alliance")
    await interaction.response.send_message(embed=embed)
    reqheaders = {"X-TBA-Auth-Key": TBA_AUTH_KEY}
    session = await self.bot.get_session()
    teams = session.query(Team)
    i = 0
    while(True):
      try:
        requestURL = TBA_API_ENDPOINT + "teams/" + str(i) + "/simple"
        response = requests.get(requestURL, headers=reqheaders).json()
        if (len(response) == 0):
          break
        for team in response:
          teamNumber = str(team["team_number"])
          teamName = str(team["nickname"])
          if teams.filter(Team.team_number == teamNumber).count() == 0:
            logger.info(f"Inserting team number {teamNumber}")
            isFiM = False
            if (team["state_prov"] == "Michigan"):
              isFiM = True
            teamToAdd = Team(team_number=teamNumber, name=teamName, is_fim=isFiM)
            session.add(teamToAdd)
          elif not teams.filter(Team.team_number == teamNumber).first().name == teamName: 
            logger.info(f"Updating team number {teamNumber}, new team name {teamName}")
            teams.filter(Team.team_number == teamNumber).first().name = teamName
        session.commit()
        i += 1
        embed.description = f"Updating team list: Processed {i*500} teams"
        await interaction.edit_original_response(embed = embed)
      except Exception:
        logger.error(traceback.format_exc())
        embed.description = "Error updating team list from The Blue Alliance"
        await interaction.edit_original_response(embed = embed)
        return
    embed.description = "Updated team list from The Blue Alliance"
    await interaction.edit_original_response(embed = embed)

  async def updateEventsTask(self, interaction, year):
    embed = Embed(title="Update Event List", description=f"Updating event list for {year} from The Blue Alliance")
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
    except Exception:
      embed.description = f"Error retrieving offseason event {eventKey} from The Blue Alliance"
      await interaction.edit_original_response(embed=embed)
      logger.error(traceback.format_exc())
      return

  async def importFullDistrctTask(self, interaction, district, year):
    embed = Embed(title=f"Importing {district} District", description=f"Importing event info for all {district} districts from The Blue Alliance")
    await interaction.response.send_message(embed = embed)
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
          for team in response:
            teamNumber = str(team["team_number"])
            teamlist.add(teamNumber)
            if teamscores.filter(TeamScore.team_key == teamNumber).count() == 0:
              logger.info(f"Team {teamNumber} registered for {eventKey}")
              teamScoreToAdd = TeamScore(team_key=teamNumber, event_key=eventKey)
              session.add(teamScoreToAdd)
          for team in teamscores.all():
            if not str(team.team_key) in teamlist:
              logger.info(f"Team {team.team_key} un-registered from {team.event_key}")
              session.delete(team)
        i+=1
      session.commit()
      embed.description = f"Retrieved all {district} information"
      await interaction.edit_original_response(embed=embed)
    except Exception:
      embed.description = f"Error retrieving offseason event {eventKey} from The Blue Alliance"
      await interaction.edit_original_response(embed=embed)
      logger.error(traceback.format_exc())
      return
    pass

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

  @app_commands.command(name="updateteamlist", description="Grabs all teams from TBA")
  async def updateTeamList(self, interaction: discord.Interaction):    
    if (self.verifyAdmin(interaction)):
      asyncio.create_task(self.updateTeamsTask(interaction))
      
  @app_commands.command(name="addleague", description="Create a new league")
  async def createLeague(self, interaction: discord.Interaction, league_name: str, team_limit: int, team_starts: int, offseason: bool):
    if (await self.verifyAdmin(interaction)):
      
      leagueToAdd = League(league_id=self.getLeagueId(), league_name=league_name, team_limit=team_limit,\
                           team_starts=team_starts, offseason=offseason)
      session = await self.bot.get_session()
      session.add(leagueToAdd)
      session.commit()
      await interaction.response.send_message(f"League created successfully! League Id: " +\
                                              str(leagueToAdd.league_id))
      
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


      

async def setup(bot: commands.Bot) -> None:
  cog = Admin(bot)
  guild = await bot.fetch_guild(int(os.getenv("GUILD_ID")))
  assert guild is not None

  await bot.add_cog(
      cog,
    guilds=[guild]
  )
