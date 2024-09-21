import discord, sqlalchemy
from discord import app_commands, Embed
from discord.ext import commands
from models.draft import Draft, DraftPick, DraftOrder
from models.scores import League, PlayerAuthorized, FantasyTeam, TeamOwned
from sqlalchemy.sql import text
import logging
import os

logger = logging.getLogger('discord')

class Drafting(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  async def getCurrentPickTeamId(self, draft_id):
    session = await self.bot.get_session()
    unmadepicks = session.query(DraftPick).filter(draft_id==draft_id).filter(DraftPick.team_number=="-1").order_by(DraftPick.pick_number.asc())
    if (unmadepicks.count() == 0):
      session.close()
      return -1
    else:
      session.close()
      return unmadepicks.first().fantasy_team_id
    
  async def makeDraftPickTask(self, draft_id: int, team_number: str):
    session = await self.bot.get_session()
    pickToMake = session.query(DraftPick).filter(draft_id==draft_id).filter(DraftPick.team_number=="-1").order_by(DraftPick.pick_number.asc())
    pickToMake.first().team_number = team_number
    session.commit()
    session.close()

  async def teamIsUnpicked(self, draft_id: int, team_number: str):
    session = await self.bot.get_session()
    picksMade = session.query(DraftPick).filter(draft_id==draft_id).filter(DraftPick.team_number!="-1")
    teamsPicked = set()
    teamsPicked.update([pick.team_number for pick in picksMade.all()])
    session.close()
    return not team_number in teamsPicked
  
  async def teamIsInDraft(self, draft_id: int, team_number: str, eventKey: str, year: int, isFiM: bool):
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

  async def getDraft(self, draft_id):
    session = await self.bot.get_session()
    draft = session.query(Draft).filter(Draft.draft_id==draft_id)
    session.close()
    if (draft.count() > 0):
      return draft.first()
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
    unmadepicks = session.query(DraftPick).filter(draft_id==draft_id).filter(DraftPick.team_number=="-1").order_by(DraftPick.pick_number.asc())
    session.close()
    if (unmadepicks.count() == 0):
        return -1
    else:
        return unmadepicks.first().fantasy_team_id
    
  async def makeDraftPickHandler(self, interaction: discord.Interaction, draft_id: int, team_number: str, force: bool):
    message = await interaction.original_response()
    currentPickId = await self.getCurrentPickTeamId(draft_id)
    draft: Draft = await self.getDraft(draft_id)
    if (draft == None):
        await message.edit(content=f"Invalid draft id {draft_id}")
    league: League = await self.getLeague(draft_id)
    if (currentPickId == -1):
        await message.edit(content="Draft is complete! Invalid command.")
    elif (await self.bot.verifyTeamMember(currentPickId, interaction.user) or force):
        if (await self.teamIsUnpicked(draft_id=draft_id, team_number=team_number)):
            if (await self.teamIsInDraft(draft_id=draft_id, team_number=team_number, eventKey=draft.event_key, year=league.year, isFiM=league.is_fim)):
                await self.makeDraftPickTask(draft_id=draft_id, team_number=team_number)
                await message.edit(content=f"Team {team_number} has been successfully selected!")
            else:
                await message.edit(content=f"Team {team_number} is not able to be drafted in this draft.")
        else:
            await message.edit(content=f"Team {team_number} has already been picked. Please try again.")
        await self.postDraftBoard(interaction, draft_id)
        await self.notifyNextPick(interaction, draft_id)
    else:
        await message.edit(content="It is not your turn to pick!")
  
  async def postDraftBoard(self, interaction: discord.Interaction, draft_id):
    session = await self.bot.get_session()
    draftBoardEmbed = Embed(title=f"**Draft Board**", description="```")
    draft: Draft = await self.getDraft(draft_id=draft_id)
    if draft.rounds <= 4: #static
      draftBoardEmbed.description += f"{'Team':^15s}{'':3s}{'Pick 1':^6s}{'':3s}{'Pick 2':^6s}{'':3s}{'Pick 3':^6s}"
      if draft.rounds == 4:
        draftBoardEmbed.description += f"{'':3s}{'Pick 4':^5s}\n"
      else:
        draftBoardEmbed.description += "\n"
      draftOrder = session.query(DraftOrder).filter(DraftOrder.draft_id==draft_id).order_by(DraftOrder.draft_slot.asc())
      for draftSlot in draftOrder.all():
        fantasyteam = session.query(FantasyTeam).filter(FantasyTeam.fantasy_team_id==draftSlot.fantasy_team_id).first()
        draftPicks = session.query(DraftPick).filter(DraftPick.fantasy_team_id==draftSlot.fantasy_team_id).all()
        abbrevName = fantasyteam.fantasy_team_name
        if len(abbrevName) > 15:
          abbrevName = abbrevName[:15]
        draftBoardEmbed.description+=f"{abbrevName:<15s}{'':3s}"
        firstPickInd = True
        for pick in draftPicks:
          pickToAdd = "------"
          if pick.team_number == "-1" and ((await self.getCurrentPickTeamId(draft_id=draft_id)) == draftSlot.fantasy_team_id and firstPickInd):
            pickToAdd = "!PICK!"
            firstPickInd = False
          elif not pick.team_number == "-1":
            pickToAdd = pick.team_number
          draftBoardEmbed.description+=f"{pickToAdd:^6s}{'':3s}"
        draftBoardEmbed.description+="\n"
    draftBoardEmbed.description += "```"
    await interaction.channel.send(embed=draftBoardEmbed)
    session.close()
    
  async def finishDraft(self, draft_id):
    session = await self.bot.get_session()
    allDraftPicks = session.query(DraftPick).filter(DraftPick.draft_id==draft_id)
    for team in allDraftPicks.all():
      teamOwnedToAdd = TeamOwned(team_key=team.team_number, fantasy_team_id=team.fantasy_team_id, league_id=(await self.getLeague(draft_id)).league_id)
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
    else:
      usersToNotify = session.query(PlayerAuthorized).filter(PlayerAuthorized.fantasy_team_id==teamIdToPick)
      teamToNotify = session.query(FantasyTeam).filter(FantasyTeam.fantasy_team_id==teamIdToPick).first()
      for user in usersToNotify.all():
        msg+= f"<@{user.player_id}> "
      msg += f" **({teamToNotify.fantasy_team_name})** it is your turn to pick!"
    await interaction.channel.send(msg)
    session.close()

  @app_commands.command(name="pick", description="Make a draft pick!")
  async def make_pick(self, interaction: discord.Interaction, draft_id: int, team_number: str): 
    await interaction.response.send_message(f"Attempting to pick team {team_number}.")
    await self.makeDraftPickHandler(interaction=interaction, draft_id=draft_id, team_number=team_number, force=False)


  @app_commands.command(name="postdraftboard", description="Re-post the Draft Board")
  async def repost_draft_board(self, interaction: discord.Interaction, draft_id: int):
    await interaction.response.send_message("Sending draft board...")
    await self.postDraftBoard(interaction, draft_id)

async def setup(bot: commands.Bot) -> None:
  cog = Drafting(bot)
  guild = await bot.fetch_guild(int(os.getenv("GUILD_ID")))
  assert guild is not None

  await bot.add_cog(
      cog,
    guilds=[guild]
  )