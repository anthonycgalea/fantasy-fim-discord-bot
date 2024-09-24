import discord, sqlalchemy
from discord import app_commands, Embed
from discord.ext import commands
import logging
import os
from models.scores import TeamOwned, TeamScore, FRCEvent, FantasyTeam, TeamStarted, PlayerAuthorized, League
from models.users import Player
from sqlalchemy import delete

logger = logging.getLogger('discord')
STATESWEEK = 6
STATESEXTRA = 1
MAXSTARTS = 2

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
                if int(frcEvent.week) < STATESWEEK:
                    if (weeks[int(frcEvent.week)-1] == "---------"):
                        weeks[int(frcEvent.week)-1] = event.event_key
                    else:
                        weeks[int(frcEvent.week)-1] = "2 Events"
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

    async def startTeamTask(self, interaction: discord.Interaction, frcteam: str, week: int, fantasyId: int):
        deferred = await interaction.original_response()
        session = await self.bot.get_session()
        fantasyteam: FantasyTeam = session.query(FantasyTeam).filter(FantasyTeam.fantasy_team_id==fantasyId).first()
        league: League = session.query(League).filter(League.league_id==fantasyteam.league_id).first()
        #is this a fim season long league?
        if (not league.is_fim):
            await deferred.edit("This league does not support starts/sits.")
            session.close()
            return
        #do you own the team?
        teamowned = session.query(TeamOwned)\
                .filter(TeamOwned.team_key==frcteam)\
                .filter(TeamOwned.league_id==league.league_id)\
                .filter(TeamOwned.fantasy_team_id==fantasyId)
        if (teamowned.count() == 0):
            await deferred.edit(content="You do not own this team.")
            session.close()
            return
        teamsStartedRecords = session.query(TeamStarted).filter(TeamStarted.fantasy_team==fantasyId).filter(TeamStarted.week==week)
        if ((league.team_starts <= teamsStartedRecords.count() and week < STATESWEEK) or (league.team_starts + STATESEXTRA <= teamsStartedRecords.count() and week == STATESWEEK)):
            await deferred.edit(content="Already starting max number of teams this week.")
        else:
            #get frc events in fim this week
            frcevents = session.query(FRCEvent).filter(FRCEvent.year==league.year).filter(FRCEvent.week==week).filter(FRCEvent.is_fim==True)
            eventList = [event.event_key for event in frcevents.all()]
            #does team compete in fim this week?
            teamcompeting = session.query(TeamScore).filter(TeamScore.team_key==frcteam)\
                .filter(TeamScore.event_key.in_(eventList))
            #is your team already starting?
            alreadyStarting = teamsStartedRecords.filter(TeamStarted.team==frcteam).count()
            #has your team been started twice this year already?
            teamStartedCount = session.query(TeamStarted)\
                .filter(TeamStarted.league==league.league_id)\
                .filter(TeamStarted.team==frcteam)\
                .filter(TeamStarted.week < STATESWEEK)
            if (teamcompeting.count() == 0):
                await deferred.edit(content="This team is not competing this week!")
            elif (teamcompeting.count() > 1):
                await deferred.edit(content="Please contact a fantasy admin to start your team. They are competing at multiple FiM events this week which is a special case.")
            elif (alreadyStarting > 0):
                await deferred.edit(content="This team is already starting this week!")
            elif (not week == STATESWEEK and teamStartedCount.count() >= MAXSTARTS):
                await deferred.edit(content=f"This team may not be started again until States, they have reached the maximum of {MAXSTARTS}")
            else:
                eventkey = teamcompeting.first().event_key
                frcevent: FRCEvent = session.query(FRCEvent).filter(FRCEvent.event_key==eventkey).first()
                teamStartedToAdd = TeamStarted(fantasy_team=fantasyId, team=frcteam, league=league.league_id, event=eventkey, week=week)
                session.add(teamStartedToAdd)
                session.commit()
                await deferred.edit(content=f"{fantasyteam.fantasy_team_name} is starting team {frcteam} competing at {frcevent.event_name} in week {week}!")
        session.close()

    async def sitTeamTask(self, interaction: discord.Interaction, frcteam: str, week: int, fantasyId: int):
        deferred = await interaction.original_response()
        session = await self.bot.get_session()
        fantasyteam: FantasyTeam = session.query(FantasyTeam).filter(FantasyTeam.fantasy_team_id==fantasyId).first()
        league: League = session.query(League).filter(League.league_id==fantasyteam.league_id).first()
        #is this a fim season long league?
        if (not league.is_fim):
            await deferred.edit("This league does not support starts/sits.")
            session.close()
            return
        #is this team actually starting for you?
        teamstarted = session.query(TeamStarted)\
                .filter(TeamStarted.team==frcteam)\
                .filter(TeamStarted.league==league.league_id)\
                .filter(TeamStarted.fantasy_team==fantasyId)\
                .filter(TeamStarted.week==week)
        if (teamstarted.count() == 0):
            await deferred.edit(content="You are not currently starting this team.")
        elif (teamstarted.count() > 1):
            await deferred.edit(content="Please contact a fantasy admin to sit your team. You are starting them at multiple FiM events this week which is a special case.")
        else:
            eventkey = teamstarted.first().event
            frcevent: FRCEvent = session.query(FRCEvent).filter(FRCEvent.event_key==eventkey).first()
            teamstarted.delete()
            session.commit()
            await deferred.edit(content=f"{fantasyteam.fantasy_team_name} is sitting team {frcteam} competing at {frcevent.event_name} in week {week}.")
        session.close()

    async def renameTeamTask(self, interaction: discord.Interaction, newname: str, fantasyId: int):
        deferred = await interaction.original_response()
        session = await self.bot.get_session()
        fantasyteam: FantasyTeam = session.query(FantasyTeam).filter(FantasyTeam.fantasy_team_id==fantasyId).first()
        oldname = fantasyteam.fantasy_team_name
        fantasyteam.fantasy_team_name=newname
        session.commit()
        await deferred.edit(content=f"Team **{oldname}** renamed to **{newname}** (Team id {fantasyteam.fantasy_team_id})")
        session.close()

    async def viewStartsTask(self, interaction: discord.Interaction, fantasyId: int):
        session = await self.bot.get_session()
        # retrieve league starts data
        fantasyteam: FantasyTeam = session.query(FantasyTeam).filter(FantasyTeam.fantasy_team_id==fantasyId).first()
        league: League = session.query(League).filter(League.league_id==fantasyteam.league_id).first()
        teamsToStart = league.team_starts
        #retrieve teamstarted for team
        teamsStarted = session.query(TeamStarted).filter(TeamStarted.fantasy_team==fantasyId)
        # for every week
        embed = Embed(title=f"**{fantasyteam.fantasy_team_name} Starting Lineups**", description=f"```{'':^8s}")
        for team in range(1, teamsToStart+STATESEXTRA+1):
            if team>league.team_starts:
                embed.description += f"{f'Team {team}':^7s}\n"
            else:
                embed.description += f"{f'Team {team}':^7s}{'':2s}"
        for week in range(1,STATESWEEK+1):
            # grab every started team and fill in embed
            weekTeamsStarted = teamsStarted.filter(TeamStarted.week==week).all()
            lineToAdd = ["-----" for _ in range(teamsToStart)]
            for _ in range(STATESEXTRA):
                if not week == STATESWEEK:
                    lineToAdd.append("")
                else:
                    lineToAdd.append("-----")
            count = 0
            for start in weekTeamsStarted:
                lineToAdd[count] = start.team
                count += 1
            embed.description+=f"{f'Week {week}':^8s}"
            for k in range(teamsToStart+STATESEXTRA):
                if k+1 > teamsToStart:
                    embed.description+=f"{lineToAdd[k]:^7s}\n"
                else:
                    embed.description+=f"{lineToAdd[k]:^7s}{'':2s}"
        # send embed
        response = await interaction.original_response()
        embed.description+="```"
        await response.edit(embed=embed, content="")
        session.close()

    async def addDropTeamTask(self, interaction: discord.Interaction, addTeam: str, dropTeam: str, fantasyId: int):
        #check if own dropTeam

        #check if addTeam is available to be picked up

        #remove dropTeam from any future starts

        #drop dropTeam and place dropTeam on waivers

        #add addTeam
        pass

    @app_commands.command(name="viewteam", description="View a fantasy team and when their FRC teams compete")
    async def viewATeam(self, interaction: discord.Interaction, fantasyteam: int):
        await interaction.response.send_message("Collecting fantasy team board")
        await self.postTeamBoard(interaction, fantasyteam)

    @app_commands.command(name="myteam", description="View your fantasy team and when their FRC teams compete")
    async def viewMyTeam(self, interaction: discord.Interaction):
        await interaction.response.send_message("Collecting fantasy team board")
        teamId = await self.getFantasyTeamIdFromInteraction(interaction=interaction)
        if not teamId == None:
            await self.postTeamBoard(interaction, teamId)
        else:
            message = await interaction.original_response()
            await message.edit(content="You are not part of any team in this league!")

    @app_commands.command(name="start", description="Put team in starting lineup for week")
    async def startTeam(self, interaction: discord.Interaction, week: int, frcteam: str):
        await interaction.response.send_message(f"Attempting to place {frcteam} in starting lineup.")
        originalResponse = await interaction.original_response()
        teamId = await self.getFantasyTeamIdFromInteraction(interaction)
        if teamId == None:
            await originalResponse.edit(content="You are not in this league!")
            return
        else:
            await self.startTeamTask(interaction=interaction, week=week, frcteam=frcteam, fantasyId=teamId)

    @app_commands.command(name="sit", description="Remove team from starting lineup for week")
    async def sitTeam(self, interaction: discord.Interaction, week: int, frcteam: str):
        await interaction.response.send_message(f"Attempting to remove {frcteam} from starting lineup.")
        originalResponse = await interaction.original_response()
        teamId = await self.getFantasyTeamIdFromInteraction(interaction)
        if teamId == None:
            await originalResponse.edit(content="You are not in this league!")
            return
        else:
            await self.sitTeamTask(interaction=interaction, week=week, frcteam=frcteam, fantasyId=teamId)

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

    @app_commands.command(name="rename", description="Rename your fantasy team!")
    async def renameTeam(self, interaction:discord.Interaction, newname: str):
        await interaction.response.send_message(f"Attempting to rename team to {newname}")
        originalResponse = await interaction.original_response()
        teamId = await self.getFantasyTeamIdFromInteraction(interaction)
        if teamId == None:
            await originalResponse.edit(content="You are not in this league!")
            return
        else:
            await self.renameTeamTask(interaction, newname, teamId)

    @app_commands.command(name="adddrop", description="Add/drop a team to/from your roster!")
    async def addDrop(self, interaction:discord.Interaction, addteam: int, dropteam: int):
        await interaction.response.send_message(f"Attempting to drop {dropteam} to add {addteam}")
        originalResponse = await interaction.original_response()
        teamId = await self.getFantasyTeamIdFromInteraction(interaction)
        if teamId == None:
            await originalResponse.edit(content="You are not in this league!")
            return
        else:
            await self.addDropTeamTask(interaction, addteam, dropteam, teamId)

    @app_commands.command(name="lineup", description="View your starting lineups")
    async def startingLineups(self, interaction:discord.Interaction):
        await interaction.response.send_message(f"Retrieving starting lineups...")
        originalResponse = await interaction.original_response()
        teamId = await self.getFantasyTeamIdFromInteraction(interaction)
        if teamId == None:
            await originalResponse.edit(content="You are not in this league!")
            return
        else:
            await self.viewStartsTask(interaction, teamId)


async def setup(bot: commands.Bot) -> None:
  cog = ManageTeam(bot)
  guild = await bot.fetch_guild(int(os.getenv("GUILD_ID")))
  assert guild is not None

  await bot.add_cog(
      cog,
    guilds=[guild]
  )