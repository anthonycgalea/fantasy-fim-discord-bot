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
from models.scores import League
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
    embed = Embed(title="**League Listing**", description="```League ID   League Name\n")
    if (leagues.count() == 0):
      embed.description+="No active leagues```"
      await interaction.response.send_message(embed=embed)
      return
    for league in leagues.all():
      embed.description += f'{league.league_id:>9d}   {league.league_name}\n'
    embed.description += "```"
    await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot) -> None:
  cog = General(bot)
  guild = await bot.fetch_guild(int(os.getenv("GUILD_ID")))
  assert guild is not None

  await bot.add_cog(
      cog,
    guilds=[guild]
  )