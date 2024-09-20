import discord, sqlalchemy
from discord import app_commands
from discord.ext import commands
import requests
import logging
import os

logger = logging.getLogger('discord')

class Scores(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @app_commands.command(name="scores", description="Retrieve Scores")
  async def get_scores(self, interaction: discord.Interaction):
    latency = round(self.bot.latency * 1000, 2)
    embed = discord.Embed(
      color=0x34dceb,
      title="Ping result",
      description=f"Pong! Latency: {latency}ms"
    )
    await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot) -> None:
  cog = Scores(bot)
  guild = await bot.fetch_guild(int(os.getenv("GUILD_ID")))
  assert guild is not None

  await bot.add_cog(
      cog,
    guilds=[guild]
  )