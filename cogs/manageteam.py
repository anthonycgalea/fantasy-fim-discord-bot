import discord, sqlalchemy
from discord import app_commands, Embed
from discord.ext import commands
import requests
import logging
import os
from models.scores import TeamOwned, TeamScore, FRCEvent, FantasyTeam, TeamStarted

logger = logging.getLogger('discord')

class ManageTeam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def postTeamBoard(self, interaction: discord.Interaction, fantasyTeam: int):
        session = await self.bot.get_session()
        fantasyTeamResult = session.query(FantasyTeam).filter(FantasyTeam.fantasy_team_id==fantasyTeam)
        if (fantasyTeamResult.count() == 0):
            await interaction.channel.send("Invalid team id")
            return
        fTeamFirst = fantasyTeamResult.first()
        teamBoardEmbed = Embed(title=f"**{fTeamFirst.fantasy_team_name} Week-by-Week board**", description="```")
        teamBoardEmbed.description += f"{'Team':^4s}{'':1s}{'Week 1':^9s}{'':1s}{'Week 2':^9s}{'':1s}{'Week 3':^9s}{'':1s}{'Week 4':^9s}{'':1s}{'Week 5':^9}\n"
        teamsOwned = session.query(TeamOwned).filter(TeamOwned.fantasy_team_id==fantasyTeam).order_by(TeamOwned.team_key.asc())
        for team in teamsOwned.all():
            teamEvents = session.query(TeamScore).filter(TeamScore.team_key==team.team_key)
            weeks = ["---------" for k in range(5)]
            for event in teamEvents.all():
                frcEvent = session.query(FRCEvent).filter(FRCEvent.event_key==event.event_key).first()
                if int(frcEvent.week) < 6:
                    weeks[int(frcEvent.week)-1] = event.event_key
            teamBoardEmbed.description+=f"{team.team_key:>4s}{'':1s}{weeks[0]:^9s}{'':1s}{weeks[1]:^9s}{'':1s}{weeks[2]:^9s}{'':1s}{weeks[3]:^9s}{'':1s}{weeks[4]:^9}\n"
        teamBoardEmbed.description += "```"
        await interaction.channel.send(embed=teamBoardEmbed)
        session.close()

    @app_commands.command(name="viewmyteam", description="View a fantasy team and when their FRC teams compete")
    async def viewMyTeam(self, interaction: discord.Interaction, fantasyteam: int):
        await interaction.response.send_message("Collecting fantasy team board")
        await self.postTeamBoard(interaction, fantasyteam)

    @app_commands.command(name="setstarter", description="Put team in starting lineup for week")
    async def startTeam(self, interaction: discord.Interaction, fantasyteam: int, frcteam: str):
        await interaction.response.send_message(f"Attempting to place {frcteam} in starting lineup.")
        if (self.bot.verifyTeamMember(interaction.user, fantasyteam)):
            pass
            await self.startTeamTask(interaction, fantasyteam, frcteam)


async def setup(bot: commands.Bot) -> None:
  cog = ManageTeam(bot)
  guild = await bot.fetch_guild(int(os.getenv("GUILD_ID")))
  assert guild is not None

  await bot.add_cog(
      cog,
    guilds=[guild]
  )