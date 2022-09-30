# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 09:05:37 2022

@author: grega
"""
# Import the necessary standard libraries
import pandas as pd
import os
import datetime as dt

# Import the necessary custom scripts I've written
from FigureFrames import FigureFrames
from GameStats import GameStats
from GameScatter import GameScatter
from RinkScatter import RinkScatter
from PuckPlot import PuckPlot
from StatsTables import StatsTables
# from TeamStats import TeamStats
from DataPanePost import DataPane
from nhlstats import list_games

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 12)
pd.set_option('display.width', 1500)

class PreGameReport:
    
    def __init__(
            self, game_id, AltHomeColor=False, AltAwayColor=False,
            template='plotly_white', publish=True
        ):
        self.game_id      = game_id
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
        self.Games     = Games
        self.Home      = Home
        self.HomeAbrv  = HomeAbrv
        self.HCol      = Home_Color2 if AltHomeColor else Home_Color1
        self.Away      = Away
        self.AwayAbrv  = AwayAbrv
        self.ACol      = Away_Color2 if AltAwayColor else Away_Color1
        self.direct_of_attack = direct_of_attack
        
    def Collect_Games(self):
        
        Games   = self.Games
        Home    = self.Home
        Away    = self.Away
        game_id = self.game_id
        GameDay = self.GameDay
                
        # Subset out games where either of the two teams for the selected game played
        # Also only examine games marked as final, and occured before the date of this game
        both_team_games = Games.copy()
        both_team_games = both_team_games[
            (both_team_games.home_team.str.contains(f'{Home}|{Away}') | \
             both_team_games.away_team.str.contains(f'{Home}|{Away}')) & \
            (both_team_games.game_state == 'Final') & (both_team_games.date < GameDay)
        ]
        # Drop any pre-season games from the master games df
        # TODO: Figure out what to do with playoff games eventually
        both_team_games = both_team_games[
            both_team_games.game_id.astype('str').str.slice(4, 6) != '01'
        ]
        print(f'GP Across Both Teams: {both_team_games.shape[0]}')
        
        # Subset out the season series for these two teams
        # Start with games that have been played
        season_series_gp = both_team_games[
            both_team_games.home_team.str.contains(f'{Home}|{Away}') & \
            both_team_games.away_team.str.contains(f'{Home}|{Away}')
        ]
        # Then collect all games in the season series
        season_series = Games[
            Games.home_team.str.contains(f'{Home}|{Away}') & \
            Games.away_team.str.contains(f'{Home}|{Away}')
        ]
        print(f'GP in season series: {season_series_gp.shape[0]} of {season_series.shape[0]}')
        
        # Collect the game stats for each game played so far by each team in the season
        game_dict = dict()
        play_dict = dict()
        for game_id in both_team_games.game_id:
            gs = GameStats(game_id)
            gs.All()
            game_dict[game_id] = gs
            play_dict[game_id] = gs.plays
            print(f'Processed: {game_id}')
        
    def Report(self):
        
        GameStats = self.GameStats

game_id = 2021020871
pg = PreGameReport(game_id, publish=False)
pg.Report()
self = pg
