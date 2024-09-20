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

logger = logging.getLogger('discord')

class General(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @app_commands.command(name="ping", description="Shows the bot is active")
  async def ping(self, interaction: discord.Interaction):
    latency = round(self.bot.latency * 1000, 2)
    await interaction.response.send_message(f"Pong! Latency: {latency}ms")

async def setup(bot: commands.Bot) -> None:
  cog = General(bot)
  guild = await bot.fetch_guild(int(os.getenv("GUILD_ID")))
  assert guild is not None

  await bot.add_cog(
      cog,
    guilds=[guild]
  )