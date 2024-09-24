import discord, sqlalchemy
from discord import app_commands, Embed
from discord.ext import commands
from models.draft import Draft, DraftPick, DraftOrder
from models.scores import League, PlayerAuthorized, FantasyTeam, TeamOwned
from sqlalchemy.sql import text
import logging
import os
from discord.ui import Button, View
from math import ceil

logger = logging.getLogger('discord')

class Drafting(commands.Cog):

  class DraftPaginationView(View):
    def __init__(self, bot, interaction, session, draftOrder, draft, rounds_per_page, total_pages):
        super().__init__(timeout=5000)
        self.bot = bot
        self.interaction = interaction
        self.session = session
        self.draftOrder = draftOrder
        self.draft = draft
        self.rounds_per_page = rounds_per_page
        self.total_pages = total_pages
        self.current_page = 0
    
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_embed(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.update_embed(interaction)

    async def update_embed(self, interaction: discord.Interaction):
        draftCog = Drafting(self.bot)
        new_embed = await draftCog.createDraftBoardEmbed(self.session, self.draftOrder, self.draft, self.current_page, self.total_pages, self.rounds_per_page)
        self.children[0].disabled = self.current_page <= 0
        self.children[1].disabled = self.current_page >= self.total_pages - 1       
        await interaction.message.edit(embed=new_embed, view=self)

    async def on_timeout(self):
      for child in self.children:
        child.disabled = True
      await self.interaction.message.edit(view=self)

  def __init__(self, bot):
    self.bot = bot

  async def getCurrentPickTeamId(self, draft_id):
    session = await self.bot.get_session()
    unmadepicks = session.query(DraftPick).filter(DraftPick.draft_id==draft_id).filter(DraftPick.team_number=="-1").order_by(DraftPick.pick_number.asc())
    if (unmadepicks.count() == 0):
      session.close()
      return -1
    else:
      session.close()
      return unmadepicks.first().fantasy_team_id
    
  async def getCurrentPickNumber(self, draft_id):
    session = await self.bot.get_session()
    unmadepicks = session.query(DraftPick).filter(DraftPick.draft_id==draft_id).filter(DraftPick.team_number=="-1").order_by(DraftPick.pick_number.asc())
    if (unmadepicks.count() == 0):
      session.close()
      return -1
    else:
      session.close()
      return unmadepicks.first().pick_number

  async def makeDraftPickTask(self, draft_id: int, team_number: str):
    session = await self.bot.get_session()
    pickToMake = session.query(DraftPick).filter(DraftPick.draft_id==draft_id).filter(DraftPick.team_number=="-1").order_by(DraftPick.pick_number.asc())
    pickToMake.first().team_number = team_number
    session.commit()
    session.close()

  async def teamIsUnpicked(self, draft_id: int, team_number: str):
    session = await self.bot.get_session()
    picksMade = session.query(DraftPick).filter(DraftPick.draft_id==draft_id).filter(DraftPick.team_number!="-1")
    teamsPicked = set()
    teamsPicked.update([pick.team_number for pick in picksMade.all()])
    session.close()
    return not team_number in teamsPicked
  
  async def teamIsInDraft(self, team_number: str, eventKey: str, year: int, isFiM: bool):
    teamsEligible = set()
    if (isFiM):
      stmt = text(f"""select distinct
                      teams.team_number
                      from
                      teams
                      join 
                      teamscore
                      on 
                      teams.team_number=teamscore.team_key
                      join 
                      frcevent
                      on
                      teamscore.event_key=frcevent.event_key
                      where 
                      teams.is_fim={isFiM}
                      and frcevent.year={year}""")
    else:
      stmt = f"""
              select distinct
              team_key
              from
              teamscore
              where 
              event_key={eventKey}
              """
    result = self.bot.session.execute(stmt).all()
    teamsEligible.update([team[0] for team in result])
    return team_number in teamsEligible
  
  async def getSuggestedTeamsList(self, eventKey: str, year: int, isFiM: bool, draft_id: int, isOffseason: bool=False):
    if (isFiM):
      stmt = text(f"""select distinct
                      teams.team_number,
                      year_end_epa
                      from
                      teams
                      join 
                      teamscore
                      on 
                      teams.team_number=teamscore.team_key
                      join 
                      frcevent
                      on
                      teamscore.event_key=frcevent.event_key
                      join
                      statboticsdata
                      on
                      teams.team_number=statboticsdata.team_number
                      where 
                      teams.is_fim={isFiM}
                      and frcevent.year={year}
                      and statboticsdata.year={year+1}
                      and teams.team_number not in (
                      select team_number from draftpick
                      where draft_id={draft_id}
                      and not team_number = '-1' 
                      )
                      order by year_end_epa desc""")
    elif (isOffseason==False):
      stmt = f"""
              select distinct
              team_key,
              year_end_epa
              from
              teamscore
              join
              statboticsdata
              on
              teamscore.team_key=statboticsdata.team_number
              where 
              event_key={eventKey}
              and statboticsdata.year={year+1}
              and team_key not in (
              select team_number from draftpick
              where draft_id={draft_id}
              and not team_number = '-1'
              )
              order by year_end_epa desc
              """
    else:
       stmt = f"""
              select distinct
              team_key,
              year_end_epa
              from
              teamscore
              join
              statboticsdata
              on
              teamscore.team_key=statboticsdata.team_number
              where 
              event_key={eventKey}
              and statboticsdata.year={year}
              and team_key not in (
              select team_number from draftpick
              where draft_id={draft_id}
              and not team_number = '-1'
              )
              order by year_end_epa desc
              """
    result = self.bot.session.execute(stmt).all()
    return result

  async def getAllAvailableTeamsList(self, eventKey: str, year: int, isFiM: bool, draft_id: int):
    if (isFiM):
      stmt = text(f"""select distinct
                      CAST(teams.team_number AS INT)
                      from
                      teams
                      join 
                      teamscore
                      on 
                      teams.team_number=teamscore.team_key
                      join 
                      frcevent
                      on
                      teamscore.event_key=frcevent.event_key
                      where 
                      teams.is_fim={isFiM}
                      and frcevent.year={year}
                      and teams.team_number not in (
                      select team_number from draftpick
                      where draft_id={draft_id}
                      and not team_number = '-1' 
                      )
                      order by CAST(teams.team_number AS INT) asc""")
    else:
      stmt = f"""
              select distinct
              team_key
              from
              teamscore
              where 
              event_key={eventKey}
              and team_key not in (
              select team_number from draftpick
              where draft_id={draft_id}
              and not team_number = '-1'
              )
              order by CAST(team_key AS INT) asc
              """
    result = self.bot.session.execute(stmt).all()
    return result

  async def postSuggestedTeams(self, interaction: discord.Interaction):
    draft: Draft = await self.getDraftFromChannel(interaction=interaction)
    message = await interaction.original_response()
    if (draft == None):
        await message.edit(content="No draft associated with this channel.")
        return
    league: League = await self.getLeague(draft_id=draft.draft_id)
    suggestedTeams = await self.getSuggestedTeamsList(eventKey=draft.event_key, year=league.year, isFiM=league.is_fim, draft_id=draft.draft_id)
    embed = Embed(title="**Suggested teams (autodraft)**", description=f"```{'Team':>10s}{f'{league.year-1} EPA':>12s}\n")
    teamsRemaining = len(suggestedTeams)
    teamsToReport = 10
    if (teamsRemaining < 10):
       teamsToReport = teamsRemaining
    for k in range(teamsToReport):
       embed.description+=f"{suggestedTeams[k][0]:>10s}{suggestedTeams[k][1]:>12d}\n"
    embed.description += "```"
    await message.edit(embed=embed)

  async def getDraft(self, draft_id):
    session = await self.bot.get_session()
    draft = session.query(Draft).filter(Draft.draft_id==draft_id)
    session.close()
    if (draft.count() > 0):
      return draft.first()
    else:
      return None

  async def getDraftFromChannel(self, interaction: discord.Interaction):
    session = await self.bot.get_session()
    draft = session.query(Draft).filter(Draft.discord_channel==str(interaction.channel_id))
    session.close()
    if (draft.count() > 0):
      return draft.first()
    else:
      return None

  async def getFantasyTeamIdFromDraftInteraction(self, interaction: discord.Interaction):
        session = await self.bot.get_session()
        largeQuery = session.query(FantasyTeam)\
            .join(PlayerAuthorized, FantasyTeam.fantasy_team_id == PlayerAuthorized.fantasy_team_id)\
            .join(League, FantasyTeam.league_id == League.league_id)\
            .join(Draft, League.league_id == Draft.league_id)\
            .filter(PlayerAuthorized.player_id == str(interaction.user.id))\
            .filter(Draft.discord_channel == str(interaction.channel_id))
        team = largeQuery.first()
        session.close()
        if team:
            return team.fantasy_team_id
        else:
            return None

  async def getLeague(self, draft_id):
    draft: Draft = await self.getDraft(draft_id)
    if draft == None:
      return None
    session = await self.bot.get_session()
    league = session.query(League).filter(League.league_id==draft.league_id)
    session.close()
    if (league.count() > 0):
      return league.first()
    else:
      return None
  
  async def getCurrentPickTeamId(self, draft_id):
    session = await self.bot.get_session()
    unmadepicks = session.query(DraftPick).filter(DraftPick.draft_id==draft_id).filter(DraftPick.team_number=="-1").order_by(DraftPick.pick_number.asc())
    session.close()
    if (unmadepicks.count() == 0):
        return -1
    else:
        return unmadepicks.first().fantasy_team_id
    
  async def makeDraftPickHandler(self, interaction: discord.Interaction, team_number: str, force: bool):
    message = await interaction.original_response()
    draft: Draft = await self.getDraftFromChannel(interaction=interaction)
    if (draft == None):
        await message.edit(content=f"Invalid draft channel")
    draft_id=draft.draft_id
    currentPickId = await self.getCurrentPickTeamId(draft_id)
    league: League = await self.getLeague(draft_id)
    userFantasyTeamId = await self.getFantasyTeamIdFromDraftInteraction(interaction)
    if (currentPickId == -1):
        await message.edit(content="Draft is complete! Invalid command.")
    elif (force or currentPickId==userFantasyTeamId):
        if (await self.teamIsUnpicked(draft_id=draft_id, team_number=team_number)):
            if (await self.teamIsInDraft(team_number=team_number, eventKey=draft.event_key, year=league.year, isFiM=league.is_fim)):
                await self.makeDraftPickTask(draft_id=draft_id, team_number=team_number)
                await message.edit(content=f"Team {team_number} has been successfully selected!")
            else:
                await message.edit(content=f"Team {team_number} is not able to be drafted in this draft.")
        else:
            await message.edit(content=f"Team {team_number} has already been picked. Please try again.")
        await self.postDraftBoard(interaction)
        await self.postSuggestedTeams(interaction)
        await self.notifyNextPick(interaction, draft_id=draft_id)
        if (await self.getCurrentPickTeamId(draft_id=draft_id) == '-1'):
           await interaction.channel.edit(archived=True, locked=True)
    else:
        await message.edit(content="It is not your turn to pick!")
    
  async def postDraftBoard(self, interaction: discord.Interaction):
      session = await self.bot.get_session()
      draft: Draft = await self.getDraftFromChannel(interaction=interaction)
      if (draft == None):
         ogresponse = await interaction.original_response()
         await ogresponse.edit(content="No draft associated with this channel.")
         return
      draft_id = draft.draft_id
      draftOrder = session.query(DraftOrder)\
          .filter(DraftOrder.draft_id == draft_id)\
          .order_by(DraftOrder.draft_slot.asc()).all()
      total_rounds = draft.rounds
      rounds_per_page = 4
      total_pages = ceil(total_rounds / rounds_per_page)
      currentPick = await self.getCurrentPickNumber(draft_id=draft_id)
      currentPage = int((currentPick-1)/(rounds_per_page*len(draftOrder)))
      if currentPage >= total_pages:
         currentPage=total_pages-1
      draftBoardEmbed = await self.createDraftBoardEmbed(session, draftOrder, draft, currentPage, total_pages, rounds_per_page)
      view = self.DraftPaginationView(self.bot, interaction, session, draftOrder, draft, rounds_per_page, total_pages)
      await interaction.channel.send(embed=draftBoardEmbed, view=view)
      
      session.close()

  async def postFullDraftBoard(self, interaction: discord.Interaction):
      session = await self.bot.get_session()
      draft: Draft = await self.getDraftFromChannel(interaction=interaction)
      if (draft == None):
         ogresponse = await interaction.original_response()
         await ogresponse.edit(content="No draft associated with this channel.")
         return
      draft_id = draft.draft_id
      draftOrder = session.query(DraftOrder)\
          .filter(DraftOrder.draft_id == draft_id)\
          .order_by(DraftOrder.draft_slot.asc()).all()
      total_rounds = draft.rounds
      rounds_per_page = 4
      total_pages = ceil(total_rounds / rounds_per_page)
      for k in range(total_pages):
        draftBoardEmbed = await self.createDraftBoardEmbed(session, draftOrder, draft, k, total_pages, rounds_per_page)
        view = self.DraftPaginationView(self.bot, interaction, session, draftOrder, draft, rounds_per_page, total_pages)
        await interaction.channel.send(embed=draftBoardEmbed, view=view)      
      session.close()

  async def createDraftBoardEmbed(self, session, draftOrder, draft, current_page, total_pages, rounds_per_page):
      draft_id = draft.draft_id
      draftBoardEmbed = Embed(title=f"**Draft Board - Page {current_page+1}/{total_pages}**", description="```")
      header = f"{'Team':^15s}{'':3s}"
      for round_num in range(1 + current_page * rounds_per_page, min((current_page + 1) * rounds_per_page, draft.rounds) + 1):
          header += f"{'Pick ' + str(round_num):>7s}{'':2s}"
      draftBoardEmbed.description += header + "\n"
      for draftSlot in draftOrder:
          fantasyteam = session.query(FantasyTeam).filter(FantasyTeam.fantasy_team_id == draftSlot.fantasy_team_id).first()
          draftPicks = session.query(DraftPick)\
              .filter(DraftPick.fantasy_team_id == draftSlot.fantasy_team_id)\
              .filter(DraftPick.pick_number > current_page*rounds_per_page*len(draftOrder))\
              .filter(DraftPick.pick_number <= (current_page + 1)*rounds_per_page*len(draftOrder))\
              .filter(DraftPick.draft_id == draft_id)\
              .order_by(DraftPick.pick_number.asc()).all()

          abbrevName = fantasyteam.fantasy_team_name[:15]  # Limit team name to 15 characters
          draftBoardEmbed.description += f"{abbrevName:<15s}{'':3s}"
          for pick in draftPicks:
              pickToAdd = "-------"
              if pick.team_number == "-1" and ((await self.getCurrentPickNumber(draft_id=draft_id)) == pick.pick_number):
                pickToAdd = "!PICK!"
              elif not pick.team_number == "-1":
                pickToAdd = pick.team_number
              draftBoardEmbed.description+=f"{pickToAdd:>7s}{'':2s}"
          draftBoardEmbed.description += "\n"
      draftBoardEmbed.description += "```"
      return draftBoardEmbed
    
  async def postAllAvailableTeams(self, interaction: discord.Interaction):
      teamcount=0
      draft: Draft = await self.getDraftFromChannel(interaction)
      league: League = await self.getLeague(draft.draft_id)
      allavailableteams = await self.getAllAvailableTeamsList(draft.event_key, league.year, league.is_fim, draft.draft_id)
      #logger.info(allavailableteams)
      embed = None
      totalteams = len(allavailableteams)
      while(teamcount < totalteams):
        if (teamcount%168 == 0):
           if not embed == None:
              embed.description+="```"
              await interaction.channel.send(embed=embed)
           embed = Embed(description="```")
        teamnumber = allavailableteams[teamcount][0]
        embed.description+=f"{teamnumber:>7d}"
        teamcount+=1
        if (teamcount%8 == 0):
           embed.description+="\n"
      if not embed == None:
         embed.description+="```"
         await interaction.channel.send(embed=embed)
     #embed = Embed(description="```")
     

  async def finishDraft(self, draft_id):
    session = await self.bot.get_session()
    allDraftPicks = session.query(DraftPick).filter(DraftPick.draft_id==draft_id)
    for team in allDraftPicks.all():
      teamOwnedToAdd = TeamOwned(team_key=team.team_number, fantasy_team_id=team.fantasy_team_id, league_id=(await self.getLeague(draft_id)).league_id, draft_id=draft_id)
      session.add(teamOwnedToAdd)
    session.commit()
    session.close()

  async def notifyNextPick(self, interaction: discord.Interaction, draft_id):
    session = await self.bot.get_session()
    teamIdToPick = await self.getCurrentPickTeamId(draft_id=draft_id)
    msg = ""
    if teamIdToPick == -1:
      msg += "Draft is complete!"
      await self.finishDraft(draft_id=draft_id)
      await self.postFullDraftBoard(interaction=interaction)
    else:
      usersToNotify = session.query(PlayerAuthorized).filter(PlayerAuthorized.fantasy_team_id==teamIdToPick)
      teamToNotify = session.query(FantasyTeam).filter(FantasyTeam.fantasy_team_id==teamIdToPick).first()
      for user in usersToNotify.all():
        msg+= f"<@{user.player_id}> "
      msg += f" **({teamToNotify.fantasy_team_name})** it is your turn to pick!"
    await interaction.channel.send(msg)
    session.close()

  @app_commands.command(name="pick", description="Make a draft pick!")
  async def make_pick(self, interaction: discord.Interaction, team_number: str): 
    await interaction.response.send_message(f"Attempting to pick team {team_number}.")
    await self.makeDraftPickHandler(interaction=interaction, team_number=team_number, force=False)


  @app_commands.command(name="draftboard", description="Re-post the Draft Board")
  @commands.cooldown(rate=1, per=60)
  async def repost_draft_board(self, interaction: discord.Interaction):
    await interaction.response.send_message("Sending draft board...")
    await self.postDraftBoard(interaction)

  @app_commands.command(name="suggest", description="Provides a list of suggested teams based on the previous season's year-end EPA.")
  @commands.cooldown(rate=1, per=60)
  async def suggestTenTeams(self, interaction: discord.Interaction):
     await interaction.response.defer()
     await self.postSuggestedTeams(interaction=interaction)

  @app_commands.command(name="available", description="Posts all available teams in current draft.")
  @commands.cooldown(rate=1, per=60)
  async def getAllAvailable(self, interaction: discord.Interaction):
     await interaction.response.send_message("**Fetching all available teams**")
     await self.postAllAvailableTeams(interaction)

async def setup(bot: commands.Bot) -> None:
  cog = Drafting(bot)
  guild = await bot.fetch_guild(int(os.getenv("GUILD_ID")))
  assert guild is not None

  await bot.add_cog(
      cog,
    guilds=[guild]
  )