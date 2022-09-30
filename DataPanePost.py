# -*- coding: utf-8 -*-
"""
Will create and configure the DataPane post for the appropriate report type.
Created on Sat Nov 13 20:44:02 2021

@author: grega
"""
import datapane as dp
from datetime import datetime as dt
from datetime import date
import os
from Standings import NHLstandings

DataPane_key = os.environ.get("DataPane Token")
Logo_Root    = r'C:\Users\grega\Google Drive\Python\NHLstats\Team Logos'

class DataPane:
    
    def __init__(self, DataPane_key=DataPane_key):
        
        dp.login(token=DataPane_key)
        
    def Game(self, gs, fig, plays, GameTable, SeasonTable, HCol, ACol, Playoffs = True):
        
        # Collect the team names and colors
        game_id  = gs.game_id
        Home     = gs.Home
        HomeAbrv = gs.HomeAbrv
        HomeGoal = gs.Goals[2]
        HomeImge = os.path.sep.join([Logo_Root, f'{HomeAbrv}.png'])
        Away     = gs.Away
        AwayAbrv = gs.AwayAbrv
        AwayGoal = gs.Goals[3]
        AwayImge = os.path.sep.join([Logo_Root, f'{AwayAbrv}.png'])
        
        # Collect team standings to use in logo captions
        ns = NHLstandings(str(date.today()))
        HomeRcrd = ns.team_record(HomeAbrv)
        AwayRcrd = ns.team_record(AwayAbrv)
                
        if HomeGoal > AwayGoal:
            HomeChng, HomeChngColor = "W", True
            AwayChng, AwayChngColor = "L", False
        else:
            HomeChng, HomeChngColor = "L", False
            AwayChng, AwayChngColor = "W", True
        
        # Define the author's note
        with open('Author Note - Game.txt') as f:
            myNote = f.readlines()
        myNote = ''.join(myNote)
        myNote = myNote.replace('PLACEHOLDER', str(game_id))
            
        # Create the first page of the report
        ## TODO figure out why this doesn't work as intended (plugging `Logo_Group` into dp.Page())
        if Playoffs:
            Logo_Group = dp.Group(
                # Away logo
                dp.Attachment(file = AwayImge, caption = '', name = ''),
                # Playoff logo
                dp.Attachment(
                    file = os.path.sep.join([Logo_Root, 'Playoff_Logo_New.png']),
                    caption = '',
                    name = ''
                ),
                # Home logo
                dp.Attachment(file = HomeImge, caption = '', name = ''),
                columns=3
            )
            
        else:
            Logo_Group = dp.Group(
                dp.Attachment(file = AwayImge, caption = AwayRcrd, name = AwayAbrv),
                dp.Attachment(file = HomeImge, caption = HomeRcrd, name = HomeAbrv),
                columns=2
            )
        
        # TEST
        # Try displaying season records as text boxes
        Rcrd_Group = dp.Group(
            dp.HTML(
                f'<html><font color="{HCol}" size="7"><center><b>{HomeAbrv}</b> ' + \
                f'{HomeRcrd}</center></font></html>'
            ),
            dp.HTML(
                f'<html><font color="{ACol}" size="7"><center><b>{AwayAbrv}</b> ' + \
                f'{AwayRcrd}</center></font></html>'
            ),
            columns = 2 
        )
        
        page1 = dp.Page(
            title  = 'Game Plots & Notes',
            blocks = [
                # Add the team logos - dependent on if game is a playoff game
                # Add the team scores & winner labels
                Logo_Group,
                Rcrd_Group,
                dp.Group(
                    dp.HTML('<html> <h/tml>'),
                    dp.BigNumber(
                        heading = AwayAbrv,
                        value = AwayGoal,
                        change = AwayChng,
                        is_upward_change = AwayChngColor
                    ),
                    dp.HTML('<html> <h/tml>'),
                    dp.HTML('<html> <h/tml>'),
                    dp.HTML('<html> <h/tml>'),
                    dp.BigNumber(
                        heading = HomeAbrv,
                        value = HomeGoal,
                        change = HomeChng,
                        is_upward_change = HomeChngColor
                    ),
                    dp.HTML('<html> <h/tml>'),
                    columns = 7,
                ),
                fig,
                f'_Built using data from the NHL Stats API on {date.today()}_',
                myNote,
                plays
            ]
        )
        
        # Create the frames for the player stats pages (for the individual game & season totals)
        page2 = dp.Page(
            title  = 'Player Stats (Game Total)',
            blocks = ['### WORK IN PROGRESS', GameTable, plays]
        )
        page3 = dp.Page(
            title = 'Player Stats (Season Total)',
            blocks = ['### WORK IN PROGRESS', SeasonTable, plays]
        )
        
        # Create the DataPane report
        dp.enable_logging()
        r = dp.Report(
            page1,
            page2,
            page3
        )
        
        # Upload the DataPane report
        r.upload(
            name           = f"{Away} @ {Home} | {gs.gameDay.strftime('%d-%b-%Y')}",
            open           = True,
            # visibility     = dp.Visibility.PORTFOLIO,
            formatting     = dp.ReportFormatting(
                accent_color   = HCol,
                width          = dp.ReportWidth.FULL,
                font           = dp.FontChoice.SANS,
                text_alignment = dp.TextAlignment.JUSTIFY
            )
        )
        
    def Night(self, GameDay, fig):
        
        # Reformat the GameDay string for the substitution of myNote
        GameDay_url = dt.strptime(GameDay, '%d-%b-%y').strftime('%Y-%m-%d')
        
        # Define the author's note
        with open('Author Note - Night.txt') as f:
            myNote = f.readlines()
        myNote = ''.join(myNote)
        myNote = myNote.replace('PLACEHOLDER', str(GameDay_url))
        
        # Create the page object to be published
        page1 = dp.Page(
            title  = 'Game Summaries & Notes',
            blocks = [
                fig,
                f'_Built using data from the NHL Stats API on {date.today()}_',
                myNote
            ]
        )
        
        # Create the report
        dp.enable_logging()
        r = dp.Report(
            page1
        )
        
        # Upload the DataPane report
        r.upload(
            name           = f"{GameDay} All NHL Games Recap",
            open           = True,
            # visibility     = dp.Visibility.PORTFOLIO,
            formatting     = dp.ReportFormatting(
                accent_color   = '#8F7E4F',
                width          = dp.ReportWidth.FULL,
                font           = dp.FontChoice.SANS,
                text_alignment = dp.TextAlignment.JUSTIFY
            )
        )
        