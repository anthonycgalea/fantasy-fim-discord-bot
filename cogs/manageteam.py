import discord, sqlalchemy
from discord import app_commands, Embed
from discord.ext import commands
import requests
import logging
import os
from models.scores import TeamOwned, TeamScore, FRCEvent, FantasyTeam, TeamStarted, PlayerAuthorized, League
from models.users import Player

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

    async def getFantasyTeamIdFromInteraction(self, interaction: discord.Interaction):
        session = await self.bot.get_session()
        largeQuery = session.query(FantasyTeam)\
            .join(PlayerAuthorized, FantasyTeam.fantasy_team_id == PlayerAuthorized.fantasy_team_id)\
            .join(League, FantasyTeam.league_id == League.league_id)\
            .filter(PlayerAuthorized.player_id == str(interaction.user.id))\
            .filter(League.discord_channel == str(interaction.channel_id))
        team = largeQuery.first()
        session.close()
        if team:
            return team.fantasy_team_id
        else:
            return None


    @app_commands.command(name="viewteam", description="View a fantasy team and when their FRC teams compete")
    async def viewATeam(self, interaction: discord.Interaction, fantasyteam: int):
        await interaction.response.send_message("Collecting fantasy team board")
        await self.postTeamBoard(interaction, fantasyteam)

    @app_commands.command(name="viewmyteam", description="View your fantasy team and when their FRC teams compete")
    async def viewMyTeam(self, interaction: discord.Interaction):
        await interaction.response.send_message("Collecting fantasy team board")
        teamId = await self.getFantasyTeamIdFromInteraction(interaction=interaction)
        if not teamId == None:
            await self.postTeamBoard(interaction, teamId)
        else:
            message = await interaction.original_response()
            await message.edit(content="You are not part of any team in this league!")

    @app_commands.command(name="setstarter", description="Put team in starting lineup for week")
    async def startTeam(self, interaction: discord.Interaction, fantasyteam: int, frcteam: str):
        await interaction.response.send_message(f"Attempting to place {frcteam} in starting lineup.")
        if (self.bot.verifyTeamMember(interaction.user, fantasyteam)):
            pass
            await self.startTeamTask(interaction, fantasyteam, frcteam)

    @app_commands.command(name="addusertoteam", description="Add an authorized user to your fantasy team")
    async def authorizeUser(self, interaction: discord.Interaction, user: discord.User):
        if await self.bot.verifyTeamMember(interaction, interaction.user):
            session = await self.bot.get_session()
            player = session.query(Player).filter(Player.user_id == str(user.id))
            if player.count() == 0:
                session.add(Player(user_id=user.id, is_admin=False))
                session.commit()
            if await self.bot.verifyTeamMember(interaction, user):
                session.close()
                await interaction.response.send_message("You can't add someone already on your team!")
            elif not await self.bot.verifyNotInLeague(interaction, user):
                session.close()
                await interaction.response.send_message("You can't add someone who is already in another team in the league!")
            else:
                fantasyteamid = await self.getFantasyTeamIdFromInteraction(interaction)
                if fantasyteamid is None:
                    session.close()
                    await interaction.response.send_message("Could not find your fantasy team.")
                    return
                authorizeToAdd = PlayerAuthorized(fantasy_team_id=fantasyteamid, player_id=user.id)
                session.add(authorizeToAdd)
                session.commit()
                fantasyTeam = session.query(FantasyTeam).filter(FantasyTeam.fantasy_team_id == fantasyteamid).first()
                await interaction.response.send_message(f"Successfully added <@{user.id}> to {fantasyTeam.fantasy_team_name}!")
            session.close()
        else:
            await interaction.response.send_message("You are not part of any team in this league!")



async def setup(bot: commands.Bot) -> None:
  cog = ManageTeam(bot)
  guild = await bot.fetch_guild(int(os.getenv("GUILD_ID")))
  assert guild is not None

  await bot.add_cog(
      cog,
    guilds=[guild]
  )