# -*- coding: utf-8 -*-
"""
Created on Mon May  2 21:30:36 2022

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
import numpy as np

# Import the necessary plotly modules
# from plotly.subplots import make_subplots
from plotly.offline import download_plotlyjs, init_notebook_mode, plot

# Adjust some pandas display options for when I'm working in this individual script
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 10)
pd.set_option('display.width', 1500)

class PlayoffRecaps:
    def __init__(
            self, game_id, series_recap = True, AltHomeColor=False, AltAwayColor=False,
            template='plotly_white', publish=True
    ):
        # Assign input variables as class attributes
        self.game_id      = game_id
        self.AltHomeColor = AltHomeColor
        self.AltAwayColor = AltAwayColor
        self.template     = template
        self.publish      = publish
        
        # Identify the game day, as well as the home and away team for the game
        Games = pd.DataFrame(
            list_games(
                start_date=f'{str(game_id)[:4]}-07-21',
                end_date=dt.date.today() + dt.timedelta(days = 7)
            )
        )
        Teams     = Games[Games.game_id == game_id]
        GameDay   = Teams.date.iloc[0]
        GameState = Teams.game_state.iloc[0]
        Home = Teams.home_team.iloc[0]
        Away = Teams.away_team.iloc[0]
        
        # Subset out all games played between the two teams in the regular season
        Season_Series = Games[
            (Games.home_team.isin([Home, Away])) & (Games.away_team.isin([Home, Away]))
        ]
        season_key = '03' if series_recap else '02'
        Season_Series = Season_Series[
            Season_Series.game_id.astype(str).str.slice(4, 6) == season_key
        ]
        Season_Series.reset_index(inplace = True, drop = True)
        
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
        self.season_key         = season_key
        self.Season_Series_Full = Season_Series
        self.GameDay            = GameDay
        self.GameState          = GameState
        self.Home               = Home
        self.HomeAbrv           = HomeAbrv
        self.HCol               = Home_Color2 if AltHomeColor else Home_Color1
        self.Away               = Away
        self.AwayAbrv           = AwayAbrv
        self.ACol               = Away_Color2 if AltAwayColor else Away_Color1
        self.direct_of_attack   = direct_of_attack

    def Aggregate(self):
        
        # Collect class attributes
        Season_Series_Full = self.Season_Series_Full
        game_id            = self.game_id
        template           = self.template
        txtColor           = '#FFFFFF' if template == 'plotly_dark' else '#000000'
        GameDay            = self.GameDay
        GameState          = self.GameState
        Home               = self.Home
        HomeAbrv           = self.HomeAbrv
        HCol               = self.HCol
        Away               = self.Away
        AwayAbrv           = self.AwayAbrv
        ACol               = self.ACol
        direct_of_attack   = self.direct_of_attack
        
        # Clean up the season series table
        Season_Series = Season_Series_Full.drop(columns = ['season', 'game_state'])
        Season_Series.loc[:, 'Game']   = Season_Series.index + 1
        Season_Series.loc[:, 'Winner'] = Season_Series.apply(
            lambda x: x['home_team'] if x['home_score'] > x['away_score'] else x['away_team'],
            axis = 1
        )
        for col in ['home_team', 'away_team', 'Winner']:
            Season_Series.loc[:, col] = Season_Series[col].apply(
                lambda x: HomeAbrv if x == Home else AwayAbrv
            )
        Season_Series = Season_Series[['Game'] + [c for c in Season_Series.columns if c != 'Game']]
        
        # Collect stats for each game
        game_stor = list()
        for i, game in enumerate(Season_Series.game_id):
            print(f'Gameid: {game}')
            gs = GameStats(game, game_type = self.season_key)
            gs.All()
            game_stor.append(gs)
            
            # Append shots and OT info to the season series table
            Season_Series.loc[i, 'home_shots'] = int(gs.SumStats['Game Total'][gs.HomeAbrv]['Shots'])
            Season_Series.loc[i, 'away_shots'] = int(gs.SumStats['Game Total'][gs.AwayAbrv]['Shots'])
            Season_Series.loc[i, 'OT'] = 'X' if gs.OT else ''
            Season_Series.loc[i, 'SO'] = 'X' if gs.SO else ''
        
        # Iterate over the collected game stats objects to collect desired attributes
        xy_GSA_home_dic  = dict()
        xy_GSA_away_dic  = dict()
        xy_HTG_home_dic  = dict()
        xy_HTG_away_dic  = dict()
        SumStat_lst      = list()
        plays_lst        = list()
        for gs in game_stor:
            
            # Collect the game_id
            gid = gs.game_id
            
            # Collect GSA and HTGF data for the home and away teams based off game 1 of playoffs
            if gs.HomeAbrv == HomeAbrv:
                # Home team in game being iterated over is same as the home team for gm 1 of playoffs
                xy_GSA_home_dic[gid] = [gs.HomeG, gs.HomeS, gs.HomeSA]
                xy_HTG_home_dic[gid] = [gs.HomeH, gs.HomeT, gs.HomeGA, gs.HomeFO]
                
                # Same situation with the away team as above
                xy_GSA_away_dic[gid] = [gs.AwayG, gs.AwayS, gs.AwaySA]
                xy_HTG_away_dic[gid] = [gs.AwayH, gs.AwayT, gs.AwayGA, gs.AwayFO]
                
            else:
                # Otherwise home team for gm 1 is the away team in this game being iterated over
                xy_GSA_home_dic[gid] = [gs.AwayG, gs.AwayS, gs.AwaySA]
                xy_HTG_home_dic[gid] = [gs.AwayH, gs.AwayT, gs.AwayGA, gs.AwayFO]
                
                xy_GSA_away_dic[gid] = [gs.HomeG, gs.HomeS, gs.HomeSA]
                xy_HTG_away_dic[gid] = [gs.HomeH, gs.HomeT, gs.HomeGA, gs.HomeFO]
                
            # Collect the game summary stats for the summary table
            ss_temp = gs.SumStats
            # Reorder the columns
            old_cols = ss_temp.columns
            new_cols = list()
            for i in range(0, len(old_cols), 2):
                if old_cols[i][1] == HomeAbrv:
                    new_cols.append(old_cols[i])
                    new_cols.append(old_cols[i + 1])
                    
                else:
                    new_cols.append(old_cols[i + 1])
                    new_cols.append(old_cols[i])
            
            SumStat_lst.append(ss_temp[new_cols])
            
            # Collect the player stats for the sunburst charts
            gs_plays = gs.plays
            plays_lst.append(gs_plays)
            
        # Concat the plays list into one master plays df for the puck plots
        plays = pd.concat(plays_lst, axis = 0)
        plays.reset_index(inplace = True, drop = True)
        
        self.Season_Series    = Season_Series
        self.game_stor        = game_stor
        self.xy_GSA_home_dic  = xy_GSA_home_dic
        self.xy_GSA_away_dic  = xy_GSA_away_dic
        self.xy_HTG_home_dic  = xy_HTG_home_dic
        self.xy_HTG_away_dic  = xy_HTG_away_dic
        self.SumStat_lst      = SumStat_lst
        self.plays            = plays
        
    def XY_Data(self):
        
        # Collect class attributes
        HomeAbrv        = self.HomeAbrv
        Season_Series   = self.Season_Series
        xy_GSA_home_dic = self.xy_GSA_home_dic
        xy_GSA_away_dic = self.xy_GSA_away_dic
        xy_HTG_home_dic = self.xy_HTG_home_dic
        xy_HTG_away_dic = self.xy_HTG_away_dic
        
        # Aggregate game df's into one list
        agg_xy_GSA_home_dct = {'Goals': [], 'Shots': [], 'Attempts': []}
        agg_xy_GSA_away_dct = {'Goals': [], 'Shots': [], 'Attempts': []}
        agg_xy_HTG_home_dct = {'Hits': [], 'Takes': [], 'Gives': [], 'Faceoffs': []}
        agg_xy_HTG_away_dct = {'Hits': [], 'Takes': [], 'Gives': [], 'Faceoffs': []}
        for gid in Season_Series.game_id:
            
            # Collect stats for individual games and store in relevant lists
            GSA_home = xy_GSA_home_dic[gid]
            GSA_away = xy_GSA_away_dic[gid]
            HTG_home = xy_HTG_home_dic[gid]
            HTG_away = xy_HTG_away_dic[gid]
            
            # Goals, shots, attempts dicts
            for i, item in enumerate(agg_xy_GSA_home_dct.keys()):
                if GSA_home[i].shape[0]:
                    temp_GSA_h = GSA_home[i]
                    temp_GSA_h.loc[:, 'game_id'] = gid
                    agg_xy_GSA_home_dct[item].append(temp_GSA_h)
                
                if GSA_away[i].shape[0]:
                    temp_GSA_a = GSA_away[i]
                    temp_GSA_a.loc[:, 'game_id'] = gid
                    agg_xy_GSA_away_dct[item].append(temp_GSA_a)
            
            # Hits, takeaways, giveaaways, faceoffs
            for i, item in enumerate(agg_xy_HTG_home_dct.keys()):
                if HTG_home[i].shape[0]:
                    temp_HTG_h = HTG_home[i]
                    temp_HTG_h.loc[:, 'game_id'] = gid
                    agg_xy_HTG_home_dct[item].append(temp_HTG_h)
                
                if HTG_away[i].shape[0]:
                    temp_HTG_a = HTG_away[i]
                    temp_HTG_a.loc[:, 'game_id'] = gid
                    agg_xy_HTG_away_dct[item].append(temp_HTG_a)
        
        # Concat stats across all games into one df
        HomeG  = pd.concat(agg_xy_GSA_home_dct['Goals'])
        HomeS  = pd.concat(agg_xy_GSA_home_dct['Shots'])
        HomeSA = pd.concat(agg_xy_GSA_home_dct['Attempts'])
        AwayG  = pd.concat(agg_xy_GSA_away_dct['Goals'])
        AwayS  = pd.concat(agg_xy_GSA_away_dct['Shots'])
        AwaySA = pd.concat(agg_xy_GSA_away_dct['Attempts'])
        
        HomeH  = pd.concat(agg_xy_HTG_home_dct['Hits'])
        HomeTA = pd.concat(agg_xy_HTG_home_dct['Takes'])
        HomeGA = pd.concat(agg_xy_HTG_home_dct['Gives'])
        HomeFO = pd.concat(agg_xy_HTG_home_dct['Faceoffs'])
        AwayH  = pd.concat(agg_xy_HTG_away_dct['Hits'])
        AwayTA = pd.concat(agg_xy_HTG_away_dct['Takes'])
        AwayGA = pd.concat(agg_xy_HTG_away_dct['Gives'])
        AwayFO = pd.concat(agg_xy_HTG_away_dct['Faceoffs'])
        
        # Clean up the collected dfs
        for df in [HomeG, HomeS, HomeSA, AwayG, AwayS, AwaySA,
                   HomeH, HomeTA, HomeGA, HomeFO, AwayH, AwayTA, AwayGA, AwayFO]:
            df.reset_index(drop = True, inplace = True)
        
            # Transpose data as necessary
            for gid in Season_Series.game_id.unique():
                # home team for gm 1 of playoffs is not home team of game being iterated over
                if Season_Series[Season_Series.game_id == gid]['home_team'].values[0] != HomeAbrv:
                    df.loc[df.game_id == gid, 'x'] *= -1
                    df.loc[df.game_id == gid, 'y'] *= -1
        
        # Assign home and away team stats as individual class attributes
        self.HomeG, self.HomeS, self.HomeSA = HomeG, HomeS, HomeSA
        self.AwayG, self.AwayS, self.AwaySA = AwayG, AwayS, AwaySA
        self.HomeH, self.HomeT, self.HomeGA, self.HomeFO = HomeH, HomeTA, HomeGA, HomeFO
        self.AwayH, self.AwayT, self.AwayGA, self.AwayFO = AwayH, AwayTA, AwayGA, AwayFO        
        
    def SumStats(self):
        
        # Collect class attributes
        SumStat_lst   = self.SumStat_lst
        Season_Series = self.Season_Series
        HomeAbrv      = self.HomeAbrv
        AwayAbrv      = self.AwayAbrv
        
        # Create an empty OT df for the game which did not go to OT - aligns all df sizes
        # Define standard columns and index
        ot_cols = pd.MultiIndex.from_tuples(
            [('OT', HomeAbrv), ('OT', AwayAbrv)],
            names=['Period', 'Team']
        )
        ot_index = SumStat_lst[0].index
        
        # Define the empty df
        empty_ot_df = pd.DataFrame(
            data = np.NaN,
            index = ot_index,
            columns = ot_cols
        )
        
        # Ensure proper dtypes for the empty df
        for i in empty_ot_df.index:
            if i in ['Shot %', 'S/SA %', 'Faceoff Wins']:
                empty_ot_df.loc[i, :] = ['', '']
            else:
                empty_ot_df.loc[i, :] = [0, 0]
        
        # Identify games that need OT columns included and concat them with the empty df - if needed
        non_ot_games = Season_Series[Season_Series.OT == ''].index.tolist()
        cleaned_games = list()
        for i, ss in enumerate(SumStat_lst):
            if (i in non_ot_games) and (len(non_ot_games) != len(SumStat_lst)):
                ss = pd.concat([ss, empty_ot_df], axis = 1)
                cleaned_games.append(ss)
                
            else:
                cleaned_games.append(ss)
        
        # Create a master sum stats table
        SumStats_Master = cleaned_games[0].copy()
        for df in cleaned_games[1:]:
            SumStats_Master += df
        
        # Duplicate the master to use as a per-game (avg) stats table
        n_games = Season_Series.shape[0]
        SumStats_avg = SumStats_Master.copy()
        for i in SumStats_avg.index:
            if i not in ['Shot %', 'S/SA %', 'Faceoff Wins']:
                SumStats_avg.loc[i, :] = SumStats_avg.loc[i, :].apply(
                    lambda x: round(x / n_games, 1)
                )
            elif i == 'Faceoff Wins':
                continue
            else:
                SumStats_avg.loc[i, :] = ''
        
        # Define a function to calculate percentage stats for each of the sum stats tables
        def calc_percentage_stats(df, n_games = 1):
            
            # Shot percentage
            df.loc['Shot %', :] = 100 * df.loc['Goals', :] / df.loc['Shots', :]
            df.loc['Shot %', :] = df.loc['Shot %', :].apply(lambda x: f'{round(x, 1)}%')
            
            # Shot attempt percentage
            df.loc['S/SA %', :] = 100 * df.loc['Shots', :] / df.loc['Shot Attempts', :]
            df.loc['S/SA %', :] = df.loc['S/SA %', :].apply(lambda x: f'{round(x, 1)}%')
            
            # Faceoff percentages - a bit more wonky...
            # First get the total faceoffs across all games
            for col in df.columns:
                of_entry = re.findall('\(.*?\)', df.loc['Faceoff Wins', col])
                of_entry = [int(re.sub('\(|\)', '', of)) for of in of_entry]
                df.loc['Faceoff Wins', col] = sum(of_entry)
            
            # Then format it so that the total number is shown, and the percentage
            row = 9  # Need to figure out a way to dynamically define this variable
            for i in range(0, len(df.columns), 2):
                HFO = df.iloc[row, i] / n_games
                AFO = df.iloc[row, i + 1] / n_games
                TFO = HFO + AFO
                TFO = 1 if TFO == 0 else TFO
                
                df.iloc[row, i] = f'{str(round(100 * HFO / TFO, 1))}%<br>({str(HFO)})'
                df.iloc[row, i + 1] = f'{str(round(100 * AFO / TFO, 1))}%<br>({str(AFO)})'
                
            return df
        
        # Adjust the percentage stats for both sum stats dfs
        SumStats_Master = calc_percentage_stats(SumStats_Master)
        SumStats_avg = calc_percentage_stats(SumStats_avg, n_games = n_games)
        
        self.SumStats_Master = SumStats_Master
        self.SumStats_avg    = SumStats_avg
        
    def PreviewFigure(self):
        
        # Collect necessary class attributes
        template  = self.template
        txtColor  = '#FFFFFF' if template == 'plotly_dark' else '#000000'
        # GameDay   = self.GameDay
        # GameState = self.GameState
        Home      = self.Home
        HomeAbrv  = self.HomeAbrv
        HCol      = self.HCol
        Away      = self.Away
        AwayAbrv  = self.AwayAbrv
        ACol      = self.ACol
        direct_of_attack = self.direct_of_attack
        
        SumStats_Master = self.SumStats_Master
        SumStats_avg    = self.SumStats_avg
        
        # Create the master game recap figure
        # ------------------------------------------------------------------------
        # ------------------------------------
        fig = FigureFrames.PlayoffPreviewFigure(HomeAbrv, AwayAbrv, txtColor, template)
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Add the rink map plots to figure
        # ------------------------------------------------------------------------
        # ------------------------------------
        RScatter = RinkScatter(self, fig, 1, 1, 1, HCol, ACol, txtColor)
        RScatter.Append(vertically_aligned = False)
        fig = RScatter.fig
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Add the summary stats tables to figure
        # ------------------------------------------------------------------------
        # ------------------------------------
        
        # Add the Points puck plot
        ts = TeamStats
        points = ts.PuckPlot_Points(self)
        fig = PuckPlot(self, fig, 2, 1, 'POINT', HCol, ACol, points, horiz_aligned = False)
        
        # Add the Goals puck plot
        fig = PuckPlot(self, fig, 2, 2, 'GOAL', HCol, ACol, horiz_aligned = False)
        
        # Add the Goals, Shots, Attempts puck plot
        fig = PuckPlot(self, fig, 2, 3, 'GSA', HCol, ACol, horiz_aligned = False)
        
        # Add the Goals, Shots, Attempts puck plot
        fig = PuckPlot(self, fig, 2, 4, 'HTG', HCol, ACol, horiz_aligned = False)
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Add the summary stats tables to figure
        # ------------------------------------------------------------------------
        # ------------------------------------
        ST = StatsTables(self, fig, 4, 1, HCol, ACol)
        fig = ST.SumStats(playoffs = True, po_table = 'Master')
        ST = StatsTables(self, fig, 4, 3, HCol, ACol)
        fig = ST.SumStats(playoffs = True, po_table = 'Avg')
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Attach the figure object as a class attribute
        self.fig = fig
        
        # If the user does not want to publish to DataPane,
        # display the figure using the plotly.offline
        if not self.publish:
            plot(fig)
        
    def All(self):
        
        self.Aggregate()
        self.XY_Data()
        self.SumStats()
        self.PreviewFigure()

# game_id = 2021030151
game_id = 2021030231
pp = PlayoffRecaps(game_id, series_recap = False, publish = False)
pp.All()
