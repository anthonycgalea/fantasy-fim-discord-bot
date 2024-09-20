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
from models.scores import Team, League, FRCEvent

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

  def verifyAdmin(self, interaction: discord.Interaction):
    stmt = select(Player).where(Player.user_id == str(interaction.user.id))
    users = self.bot.session.execute(stmt)

    return not (users.rowcount == 0 or not users.first().is_admin)

  def getLeagueId(self):
    stmt = text("select max(league_id) from league")
    result = self.bot.session.execute(stmt).first()[0]
    if not result == None:
      return int(result) + 1
    else:
      return 1

  @app_commands.command(name="updateteamlist", description="Grabs all teams from TBA")
  async def updateTeamList(self, interaction: discord.Interaction):    
    if (not self.verifyAdmin(interaction)):
      await interaction.response.send_message("You are not authorized to use this command.")
      return
    else:
      asyncio.create_task(self.updateTeamsTask(interaction))
      
  @app_commands.command(name="addleague", description="Create a new league")
  async def createLeague(self, interaction: discord.Interaction, league_name: str, team_limit: int, team_starts: int, offseason: bool):
    if (self.verifyAdmin(interaction)):
      
      leagueToAdd = League(league_id=self.getLeagueId(), league_name=league_name, team_limit=team_limit,\
                           team_starts=team_starts, offseason=offseason)
      session = await self.bot.get_session()
      session.add(leagueToAdd)
      session.commit()
      await interaction.response.send_message(f"League created successfully! League Id: " +\
                                              str(leagueToAdd.league_id))
      
  @app_commands.command(name="updateevents", description="Update events for a given year")
  async def updateEvents(self, interaction: discord.Interaction, year: int):
    if (self.verifyAdmin(interaction)):
      asyncio.create_task(self.updateEventsTask(interaction, year))
    else:
      await interaction.response.send_message("You are not authorized to use this command.")
      return
      

async def setup(bot: commands.Bot) -> None:
  cog = Admin(bot)
  guild = await bot.fetch_guild(int(os.getenv("GUILD_ID")))
  assert guild is not None

  await bot.add_cog(
      cog,
    guilds=[guild]
  )
