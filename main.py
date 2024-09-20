import discord
from discord.ext import commands
from discord import Embed
import os
import logging
import logging.handlers
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models.base import Base

load_dotenv()

logger = logging.getLogger('discord')

intents = discord.Intents.default()
intents.message_content = True

conn_str = os.getenv("DATABASE_URL")

class FantasyFiMBot(commands.Bot):

    def __init__(self):
        super().__init__(command_prefix="/",
                         intents=discord.Intents.all(),
                         applpication_id=os.getenv("DISCORD_APPLICATION_ID"))

        self.engine = create_engine(url=conn_str)
        self.session = self.engine.connect()
        Base.metadata.create_all(self.engine)

    async def log_message(self, title, message):
        logChannel = await self.fetch_channel(int(os.getenv("LOGGING_CHANNEL_ID")))
        embed = Embed(title=f"{title}", description=f"{message}")
        return await logChannel.send(embed = embed)

    async def get_session(self):
        Session = sessionmaker(bind=self.engine)
        return Session()
    
    async def setup_hook(self):
        await self.load_extension("cogs.general")
        await self.load_extension("cogs.scores")
        await self.load_extension("cogs.admin")
        await self.tree.sync(guild=discord.Object(id=os.getenv("GUILD_ID")))

    async def on_ready(self):
        logger.info("The bot is alive!")

        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.competing, name=str("Fantasy FiM!")))

        logger.info("Bot startup complete!")


bot = FantasyFiMBot()

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
