import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import requests
import logging
import os
import threading
import aiohttp
import json
from models.scores import League, FantasyTeam
from discord import Embed

logger = logging.getLogger('discord')

class General(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @app_commands.command(name="ping", description="Shows the bot is active")
  async def ping(self, interaction: discord.Interaction):
    latency = round(self.bot.latency * 1000, 2)
    await interaction.response.send_message(f"Pong! Latency: {latency}ms")

  @app_commands.command(name="getleagues", description="Reports on active leagues and their league ids.")
  async def getLeagues(self, interaction: discord.Interaction):
    session = await self.bot.get_session()
    leagues = session.query(League).where(League.active == True)
    embed = Embed(title="**League Listing**", description="")
    if (leagues.count() == 0):
      embed.description+="No active leagues```"
      await interaction.response.send_message(embed=embed)
      return
    for league in leagues.all():
      embed.description += f'{league.league_name:>15s}   <#{league.discord_channel}>\n'
    await interaction.response.send_message(embed=embed)
    session.close()

  @app_commands.command(name="teamids", description="Reports on teams in the channel's league and their team IDs.")
  async def getTeamsInLeagues(self, interaction: discord.Interaction):
    session = await self.bot.get_session()
    league = session.query(League).where(League.discord_channel==str(interaction.channel_id))
    if (league.count() == 0):
      await interaction.response.send_message("No league associated with this channel")
    leagueid = league.first().league_id
    fantasyTeams = session.query(FantasyTeam).where(FantasyTeam.league_id==leagueid).order_by(FantasyTeam.fantasy_team_id.asc()).all()
    draftOrderEmbed = Embed(title=f"**Teams in {league.first().league_name}**", description="```Team ID     Team Name (id)\n")
    for team in fantasyTeams:
      draftOrderEmbed.description+=f"{team.fantasy_team_id:>7d}:    {team.fantasy_team_name}\n"
    draftOrderEmbed.description+="```"
    await interaction.response.send_message(embed=draftOrderEmbed)
    session.close()

async def setup(bot: commands.Bot) -> None:
  cog = General(bot)
  guild = await bot.fetch_guild(int(os.getenv("GUILD_ID")))
  assert guild is not None

  await bot.add_cog(
      cog,
    guilds=[guild]
  )