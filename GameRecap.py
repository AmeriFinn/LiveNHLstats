# -*- coding: utf-8 -*-
"""
This script will utilize `GameStats.py`, `GameMap.py`, `GameScatter.py`, `RinkScatter.py`,
`StatsTable.py`, & `PuckPlot.py` to summarize an individual game and create relevant figures
to be included in the interactive visual.
Created on Sun Aug  8 13:31:12 2021

@author: grega
"""
# Import the necessary modules for myNHLstats
from FigureFrames import FigureFrames
from GameStats import GameStats
from GameScatter import GameScatter
from RinkScatter import RinkScatter
from PuckPlot import PuckPlot
from StatsTables import StatsTables
from TeamStats import TeamStats
from DataPanePost import DataPane
from nhlstats import list_games

# Import the necessary standard modules
import pandas as pd
import datetime as dt
import time
import os
import re

# Import the necessary plotly modules
# from plotly.subplots import make_subplots
from plotly.offline import download_plotlyjs, init_notebook_mode, plot

# Adjust some pandas display options for when I'm working in this individual script
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 12)
pd.set_option('display.width', 1500)

class GameRecap:
    def __init__(
            self, game_id, game_type, AltHomeColor=False, AltAwayColor=False,
            template='plotly_white', publish=True
    ):
        
        # Assign input variables as class attributes
        self.game_id      = game_id
        self.game_type    = game_type
        self.AltHomeColor = AltHomeColor
        self.AltAwayColor = AltAwayColor
        self.template     = template
        self.publish      = publish
        
        # Identify the game day, as well as the home and away team for the game
        Games = pd.DataFrame(
            list_games(
                start_date=f'{str(game_id)[:4]}-07-21',
                end_date=dt.date.today()
            )
        )
        Teams     = Games[Games.game_id == game_id]
        GameDay   = Teams.date.iloc[0]
        GameState = Teams.game_state.iloc[0]
        Home = Teams.home_team.iloc[0]
        Away = Teams.away_team.iloc[0]
        
        # Collect the team abbreviations and colors, and direction of attack for the relevant arena
        # Collect team info provided in teamList.csv file in my github repo.
        tLUrl = 'https://raw.githubusercontent.com/AmeriFinn/LiveNHLstats/master/teamList.csv'
        tL = pd.read_csv(tLUrl, index_col=0)
        
        # Collect team abbreviations recognized by the NHL
        HomeAbrv = tL[tL.team_name == Home].team_abbrv.values[0]
        AwayAbrv = tL[tL.team_name == Away].team_abbrv.values[0]
        
        # Collect the two primary colors (in Hex code format) listed in team logo copyright
        Home_Color1 = tL[tL.team_abbrv == HomeAbrv].home_c.values[0]
        Home_Color2 = tL[tL.team_abbrv == HomeAbrv].away_c.values[0]
        
        Away_Color1 = tL[tL.team_abbrv == AwayAbrv].away_c.values[0]
        Away_Color2 = tL[tL.team_abbrv == AwayAbrv].home_c.values[0]
        
        # Determine if this teams arena records x/y stat data the "normal" way, or backwards.
        # Note: Some arenas are less consistent about x/y stat data.
        # Both within games (where goals/shots/hits/etc. aren't recorded properly by period)
        # or between games (where the home team will have 1st period stats recorded on
        # opposite ends of the rink). This is the best solution I have currently.
        direct_of_attack = tL[tL.team_abbrv == HomeAbrv].normal_direct_of_play.values[0]
        
        # Assign class attributes
        self.GameDay   = GameDay
        self.GameState = GameState
        self.Home      = Home
        self.HomeAbrv  = HomeAbrv
        self.HCol      = Home_Color2 if AltHomeColor else Home_Color1
        self.Away      = Away
        self.AwayAbrv  = AwayAbrv
        self.ACol      = Away_Color2 if AltAwayColor else Away_Color1
        self.direct_of_attack = direct_of_attack
        
    def Recap(self):
        #
        game_id   = self.game_id
        game_type = self.game_type
        template  = self.template
        txtColor  = '#FFFFFF' if template == 'plotly_dark' else '#000000'
        GameDay   = self.GameDay
        GameState = self.GameState
        Home      = self.Home
        HomeAbrv  = self.HomeAbrv
        HCol      = self.HCol
        Away      = self.Away
        AwayAbrv  = self.AwayAbrv
        ACol      = self.ACol
        direct_of_attack = self.direct_of_attack
        
        # Utilize GameStats to aggregate all stats for the desired game
        gs = GameStats(game_id, game_type = game_type)
        gs.All()
        
        # Assign the GameStats class as an attribute of GameRecap
        ## TODO !!!
        ## Investigate if there's a better (more appropriate?)
        ## or more efficient way to do this
        self.gs = gs
        
        # Create the master game recap figure
        # ------------------------------------------------------------------------
        # ------------------------------------
        fig = FigureFrames.GameRecapMaster(GameDay, HomeAbrv, AwayAbrv, txtColor, template)
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Add GameScatter plots to the figure
        # ------------------------------------------------------------------------
        # ------------------------------------
        GScatter = GameScatter(gs, fig, 1, 1, 1, HCol, ACol, txtColor)
        GScatter.GSAscatter()
        GScatter.Momentum()
        GScatter.P5Shots()
        GScatter.P5Hits()
        fig = GScatter.fig
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Add the rink map plots to figure
        # ------------------------------------------------------------------------
        # ------------------------------------
        RScatter = RinkScatter(gs, fig, 1, 2, 1, HCol, ACol, txtColor)
        RScatter.Append()
        fig = RScatter.fig
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Add the Puck Plots to relevant rows of the subplot
        # ------------------------------------------------------------------------
        # ------------------------------------
        # Start with GSA (Goals, Shots, Attempts)
        myCol = 2
        fig = PuckPlot(gs, fig, 2, myCol, 'GSA', HCol, ACol)
        
        # Then HTG (Hits, Takeaways, Giveaways)
        fig = PuckPlot(gs, fig, 4, myCol, 'HTG', HCol, ACol)
        
        # Next, add the Goals sunbursts
        fig = PuckPlot(gs, fig, 5, myCol, 'GOAL', HCol, ACol)
        
        # Next, add the Shots sunbursts
        fig = PuckPlot(gs, fig, 7, myCol, 'SHOT', HCol, ACol)
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Add the Team Summary stats table of the subplot
        # ------------------------------------------------------------------------
        # ------------------------------------
        ST = StatsTables(gs, fig, 6, 1, HCol, ACol)
        fig = ST.SumStats()
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Create the frame for the player summary stats figure
        # ------------------------------------------------------------------------
        # ------------------------------------
        GameTable = FigureFrames.GameRecapTable(GameDay, HomeAbrv, AwayAbrv, txtColor, template)
        
        # Create and collect the GameTable for each team
        ts = TeamStats
        ts.Summarize_Game(ts, game_id, gs)
        
        # Format the data into the plotly subplots object
        GameTable = ST.PlayerSummary(GameTable, ts, AwayAbrv)
        self.GameTable = GameTable
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Create and add the Puck Plot for player points to the game visual
        # ------------------------------------------------------------------------
        # ------------------------------------
        # Collect the relevant df for the player stats
        points = ts.PuckPlot_Points(gs)
        
        # Create and add the POINTS puck plot
        fig = PuckPlot(gs, fig, 6, myCol, 'POINT', HCol, ACol, points)
        
        # Attach the figure object as a class attribute
        self.fig = fig
        
        # If the user does not want to publish to DataPane,
        # display the figure using the plotly.offline
        if not self.publish:
            plot(fig)
            time.sleep(1.5)
            plot(GameTable)
        # Note: Not sure why I can't use this in an else statement
        #       with all three figures in the following `if self.publish`
        #       statement...
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Create the frame for the team summary stats figure
        # ------------------------------------------------------------------------
        # ------------------------------------
        if self.publish:
            SeasonTable = FigureFrames.GameRecapTable(GameDay, HomeAbrv, AwayAbrv, txtColor, template)
            
            # Create and collect the GameTable for each team - only if publishing to DataPane
            # if self.publish:
            ts = TeamStats
            for team, teamCol, col in zip([Away, Home], [ACol, HCol], [1, 2]):
                # Create the summary table for the desired team
                print(f'\nSummarizing Team Stats [Season Wide]: {team}\n')
                ts.Summarize_Season(ts, team, gs, teamCol)
                
                # Format the data into the plotly subplots object
                SeasonTable = ST.TeamSummary(SeasonTable, ts, col, teamCol)
            self.SeasonTable = SeasonTable
        
        # If the user does not want to publish to DataPane,
        # display the figure using the plotly.offline
        # if not self.publish:
        #     plot(SeasonTable)
        # Note: Not sure why I can't use this in an else statement
        #       with all three figures in the following `if self.publish`
        #       statement...
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Publish the report to DataPane if desired
        if self.publish:
            
            # Create a cleaned df to include in the DataPane report
            df = gs.plays.copy()
            
            # Drop unnecessary columns
            df.drop(
                columns = ['datetime', 'period_type', 'Hour', 'Minute', 'Second'],
                inplace = True
            )
            
            # Fill relevant NaN cells
            df.period.fillna(method='ffill', inplace=True)
            
            # Reorder the columns
            col_order = ['period', 'Time'] + \
                [c for c in df.columns if c not in ['period', 'Time']]
            df = df[col_order]
            
            # Publish the report to DataPane
            DP = DataPane()
            DP.Game(gs, fig, df, GameTable, SeasonTable, HCol, ACol)
        
        # Save the figures locally
        save_path = os.path.join(
            os.getcwd(), 'HTML Outputs', 'Game Recaps', f'{AwayAbrv}_@_{HomeAbrv}_{GameDay}'
        )
        
        # Create the local directories if necessary
        if not os.path.exists(os.path.join(os.getcwd(), 'HTML Outputs')):
            os.mkdir(os.path.join(os.getcwd(), 'HTML Outputs'))
        if not os.path.exists(os.path.join(os.getcwd(), 'HTML Outputs', 'Game Recaps')):
            os.mkdir(os.path.join(os.getcwd(), 'HTML Outputs', 'Game Recaps'))
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        
        fig.write_html(
            os.path.join(
                save_path,
                'Game_Plots.html'
            )
        )
        GameTable.write_html(
            os.path.join(
                save_path,
                'Player_Stats.html'
            )
        )
        if self.publish:
            SeasonTable.write_html(
                os.path.join(
                    save_path,
                    'Team_Stats.html'
                )
            )
#

# game_id = 2021021180


# # gs = GameStats(game_id)
# gr = GameRecap(game_id, AltHomeColor=True, AltAwayColor=False, publish=False)
# gr.Recap()


# gs = gr.gs
# # gs.All()
# # gs.plays.to_csv('test_plays.csv')
# gs.shots
# gs.SumStats
# gs.Goals
# gs.Momentum

# p = gs.plays
# p = p[p.event_type == 'BLOCKED_SHOT']
# p.iloc[:, [7, 8, 9, 13, 16, 17]]

# gs.plays[[col for col in gs.plays.columns if 'shot' in col.lower()][3:]]
