# -*- coding: utf-8 -*-
"""
Created on Sun Nov 14 17:35:37 2021

@author: grega
"""
# Import necessary modules
import os
import pickle
import pandas as pd
from math import floor
from datetime import *
import requests, re
from datetime import datetime

# import nhlstats
from nhlstats import list_plays, list_shots, list_games, list_shifts

from GameStats import GameStats

# Adjust pandas display options for working with IPython consoles
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 20)
pd.set_option('display.width', 1500)

class TeamStats:
    """Calculate player stats (G, A, SA, Hits, etc.) for an individual game or entire season."""
    
    def PuckPlot_Points(gs):
        """
        Create a summary df of points in an individual game.
        
        The summary df can then be manipulated to visualize points in the puck plots / sunburst
        charts used in the game recap visualizations.

        Parameters
        ----------
        gs : Gamestats.Gamestats
            The Gamestats class that has been fully executed and has the necessary attributes.

        Returns
        -------
        points : pd.DataFrame
            The aggregated pandas dataframe.

        """
        # Collect and refine the relevant data
        plays = gs.plays.copy()
        plays = plays[plays.event_type == 'GOAL']
        plays.reset_index(drop=True, inplace=True)
        cols  = ['team_for', 'period'] + \
                [f'player_{i}' for i in range(1, 4)] + \
                [f'player_{i}_type' for i in range(1, 4)]
        plays = plays[[c for c in cols if c in plays.columns]]
        plays['count'] = 1
        
        # Filter out any instances of a goalie being mentioned
        for i in plays.index:
            for j in [2, 3]:
                if plays.loc[i, f'player_{j}_type'] == 'Goalie':
                    plays.loc[i, f'player_{j}_type'] = None
                    plays.loc[i, f'player_{j}'] = None
        plays = plays[[col for col in plays.columns if 'type' not in col]]
        
        # Pivot the table so that each goal and assist has its own row
        ptype_dict = {1: 'GOAL', 2: 'PRIMARY A', 3: 'SECONDARY A'}
        df_dict    = dict()
        x = 0
        for i in plays.index:
            team_for, period = plays.loc[i, ['team_for', 'period']]
            for j in [1, 2, 3]:
                if plays.loc[i, f'player_{j}'] is not None:
                    event_type = ptype_dict[j]
                    player     = plays.loc[i, f'player_{j}']
                    stor_lst   = [team_for, period, event_type, player]
                    df_dict[x] = stor_lst
                    x += 1
        
        points = pd.DataFrame.from_dict(df_dict, orient = 'index')
        points.columns = ['team_for', 'period', 'event_type', 'player']
        
        return points
        
    def Summarize_Game(self, game_id, gs, ping_nhl=True):
        """
        Summarize stats for all players on both teams that had at least 1 shift.
        
        Back-up goalies who do not play or a skater who never touches the ice
        (which is extremely rare) will not be included in the summary tables.
        
        Parameters
        ----------
        game_id : int
            The 10 digit game id for which stats need to be summarized for.
        
        gs : Gamestats.Gamestats
            The Gamestats class that has been fully executed and has the necessary attributes.
        
        ping_nhl : bool, optional
            If true, ping the NHL website to collect player info (i.e. #, name, etc.).
            This value should only be true if Summarize_Game is being called independently,
            and not as part of `Summarize_Season`
            The default is True.
            
        Returns
        -------
        None.
        
        """
        # Collect relevant stats for the game
        plays = gs.plays.copy()
        shift = pd.DataFrame(list_shifts(game_id))
        
        # Define the columns that will be displayed in the dataframe
        df_cols = [
            'Player', 'ID', '#', 'Pos.', 'G', '1A', '2A', 'P',
            '+/-', 'S', 'SA', 'H', 'TA', 'GA', 'PIM', 'TOI', 'PPG', 'SHG'
        ]
        
        if 'first_name' in shift.columns:
            # If this routine is being called while a game is being played,
            # there's a chance the NHL API has not been updated with shift data from the
            # live game and a placeholder table will need to be created instead.
            # If `first_name` is in the columns of the shift df, the desired stats
            # table can be created
            
            # In the `shift` df, concat the first and last name columns to have a full name column
            shift['player'] = shift.first_name + ' ' + shift.last_name
            # Drop the first and last name columns, while also reordering the columns so
            # a players full name is the first column
            shift = shift[
                ['player'] + [c for c in shift.columns if c not in ['first_name', 'last_name', 'player']]
            ]
            
            # Assign the main df's as class attributes
            self.plays = plays
            self.shift = shift
            
            # Create a dictionary of player ids
            players_lst  = list(shift.player.unique())
            players_dict = {}
            for player in players_lst:
                
                for i in range(1, 5):
                    if f'player_{i}' in plays.columns:
                        if player in plays[f'player_{i}'].unique():
                            players_dict[player] = int(
                                plays[plays[f'player_{i}'] == player][f'player_{i}_id'].values[0]
                            )
                    
            # Print a list of any players who did not have a player_id identified
            print_lst = []
            if len(players_dict) != len(players_lst):
                
                # Notify users of unidentified players
                print_lst = [p for p in players_lst if p not in players_dict.keys()]
                print(f'Game: {game_id}\nPlayers with no id identified:\n\t', print_lst[0])
                for i in print_lst[1:]:
                    print('\t', i)
                print('\n')
            
            # Create a storage df of player stats for each team
            Team1 = shift.team_abbreviation.unique()[0]
            Team1_df = pd.DataFrame(
                data=None,
                columns = df_cols
            )
            Team1_df['Player'] = shift[shift.team_abbreviation == Team1]['player'].unique()
            Team1_df = Team1_df[~Team1_df.Player.isin(print_lst)]  # Drop unidentified players
            Team1_df['ID'] = Team1_df.Player.apply(lambda x: players_dict[x])
            
            Team2 = shift.team_abbreviation.unique()[1]
            Team2_df = pd.DataFrame(
                data=None,
                columns = df_cols
            )
            Team2_df['Player'] = shift[shift.team_abbreviation == Team2]['player'].unique()
            Team2_df = Team2_df[~Team2_df.Player.isin(print_lst)]  # Drop unidentified players
            Team2_df['ID'] = Team2_df.Player.apply(lambda x: players_dict[x])
            
            if ping_nhl:
                # Collect each players jersey number and position
                NHL_url = 'https://www.nhl.com/player/'
                for df in [Team1_df, Team2_df]:
                    for i in df.index:
                        
                        # Determine the appropriate NHL url to ping
                        player = df.loc[i, 'Player']
                        player = player.replace(' ', '-').lower()
                        ID     = df.loc[i, 'ID']
                        player_url = NHL_url + player + '-' + str(ID)
                        
                        # Collect the relevant info for the player
                        page = requests.get(player_url).text
                        page = page.replace('\n', '..')
                        
                        # Determine the players jersey number
                        search_me = r'<h3 class="player-jumbotron-vitals__name-num">.*?</h3>'
                        info = re.search(search_me, page).group(0)
                        
                        info = re.sub('<.*?>| {1,}|\.{1,}|#', ' ', info)
                        try:
                            jersey = info.split('|')[1].strip()
                        except IndexError:
                            jersey = ''
                        df.loc[i, '#'] = jersey
                        
                        # Determine the players position
                        search_me = r'<div class="player-jumbotron-vitals__attributes">.*?</div>'
                        info = re.search(search_me, page).group(0)
                        
                        info = re.sub('<.*?>| {1,}|\.{1,}', ' ', info)
                        position = info.split('|')[0].strip()
                        df.loc[i, 'Pos.'] = position
                    
            # Now get into collecting player specific stats
            for team, df in zip([Team1, Team2], [Team1_df, Team2_df]):
                for i in df.index:
                    
                    # Determine which player stats are being recorded for
                    player = df.loc[i, 'Player']
                    player_id = df.loc[i, 'ID']
                    
                    ### Goals Calculation
                    temp = plays[
                        (plays.player_1 == player) & (plays.event_type == 'GOAL')
                    ]
                    goals = temp.shape[0]
                    df.loc[i, 'G'] = goals
                    
                    ### Primary Assists Calculation
                    temp = plays[
                        (plays.player_2 == player) &
                        (plays.event_type == 'GOAL') &
                        (plays.team_for == team)
                    ]
                    primaries = temp.shape[0]
                    df.loc[i, '1A'] = primaries
                    
                    ### Secondary Assists Calculation
                    if 'player_3' in plays.columns:
                        temp = plays[
                            (plays.player_3 == player) &
                            (plays.event_type == 'GOAL') &
                            (plays.team_for == team)
                        ]
                        secondaries = temp.shape[0]
                    else:
                        secondaries = 0
                    df.loc[i, '2A'] = secondaries
                    
                    ### Points Calculation
                    df.loc[i, 'P'] = goals + primaries + secondaries
                    
                    ### +/- Calculation
                    # Really not sure how to go about this yet...
                    
                    ### Shots Calculation
                    temp = plays[
                        (plays.player_1 == player) & (plays.event_type == 'SHOT')
                    ]
                    shots = goals + temp.shape[0]
                    df.loc[i, 'S'] = shots
                    
                    ### Shot Attempts Calculation
                    temp = plays[
                        ((plays.player_1 == player) & (plays.event_type == 'MISSED_SHOT')) |
                        ((plays.player_2 == player) & (plays.event_type == 'BLOCKED_SHOT'))
                    ]
                    attempts = shots + temp.shape[0]
                    df.loc[i, 'SA'] = attempts
                    
                    ### Hits calculation
                    temp = plays[
                        (plays.player_1 == player) & (plays.event_type == 'HIT')
                    ]
                    hits = temp.shape[0]
                    df.loc[i, 'H'] = hits
                    
                    ### Takeaways calculation
                    temp = plays[
                        (plays.player_1 == player) & (plays.event_type == 'TAKEAWAY')
                    ]
                    takes = temp.shape[0]
                    df.loc[i, 'TA'] = takes
                    
                    ### Giveaways calculation
                    temp = plays[
                        (plays.player_1 == player) & (plays.event_type == 'GIVEAWAY')
                    ]
                    gives = temp.shape[0]
                    df.loc[i, 'GA'] = gives
                    
                    ### TOI Calculation
                    temp = shift[shift.player == player].copy()
                    temp = temp.dropna(subset=['duration'])
                    temp['duration'] = temp['duration'].apply(lambda x: '00:' + x)
                    temp['duration'] = pd.to_timedelta(temp['duration'])
                    TOI = temp.duration.sum()
                    TOI = TOI.total_seconds()
                    if ping_nhl:
                        # Presumably, if `ping_nhl` is True, Summarize_Game must be
                        # being called from outside of `Summarize_Season` and we can
                        # go straight to returning the TOI calculation as a string
                        TOI = datetime.utcfromtimestamp(TOI).strftime('%H:%M:%S')
                    df.loc[i, 'TOI'] = TOI
                    
                    ### PIM Calculation
                    # Have a thought on how to do this. May be tedious
                    
                    ### PPG Calculation
                    temp = plays[
                        (plays.player_1 == player) &
                        (plays.event_type == 'GOAL') &
                        (plays[f'{team} is_ppg'] == True)
                    ]
                    goals = temp.shape[0]
                    df.loc[i, 'PPG'] = goals
                    
                    ### SHG Calculation
                    temp = plays[
                        (plays.player_1 == player) &
                        (plays.event_type == 'GOAL') &
                        (plays[f'{team} is_shg'] == True)
                    ]
                    goals = temp.shape[0]
                    df.loc[i, 'SHG'] = goals
            
            # Sort each teams df
            for df in [Team1_df, Team2_df]:
                df.sort_values(by=['P', 'G', '1A', '2A', 'S', '#'], ascending=False, inplace=True)
                df.reset_index(inplace = True, drop = True)
        else:
            # Create the placeholder tables in the event the game is currently being played
            Team1, Team1_df = gs.HomeAbrv, pd.DataFrame(columns = df_cols)
            Team2, Team2_df = gs.AwayAbrv, pd.DataFrame(columns = df_cols)
            
        # Assign team dfs as class attributes
        self.Team1 = [Team1, Team1_df]
        self.Team2 = [Team2, Team2_df]
        
        # Save the summary stats to the relevant directory for each team
        # Only save the data if the `Summarize_Game` has been called independently
        if ping_nhl:
            data_dir = gs.data_dir
            
            # Save the player stats dataframes
            with open(os.path.join(data_dir, f'{Team1}_player_data.bin'), 'wb') as f:
                pickle.dump(Team1_df, f)
                f.close()
            with open(os.path.join(data_dir, f'{Team2}_player_data.bin'), 'wb') as f:
                pickle.dump(Team2_df, f)
                f.close()
        
    def Summarize_Season(self, team, gs, teamCol):
        """
        Iterate over each game that each team has played this season to summarize player stats.
        
        Parameters
        ----------
        team : str
            The full team name that stats are being summaryzied for.
        
        gs : Gamestats.Gamestats
            The Gamestats class that has been fully executed and has the necessary attributes.
        
        teamCol : str
            The color hex code that should be used as the table fill color for a team.

        Returns
        -------
        None.
        
        """
        self.team = team
        teamAbbrv = gs.HomeAbrv if gs.Home == team else gs.AwayAbrv
        allGames      = gs.Games
        self.allGames = allGames
        
        # Collect the teams color that is not used as the primary fill color.
        # Will be used in `StatsTable.TeamSummary` as the hyperlink text color
        tLUrl = 'https://raw.githubusercontent.com/AmeriFinn/LiveNHLstats/master/teamList.csv'
        tL = pd.read_csv(tLUrl, index_col=0)
        
        # Use the alternate color for a team as the text color
        TeamCols = tL[tL.team_abbrv == teamAbbrv][['home_c', 'away_c']]
        if teamCol == TeamCols['home_c'].values[0]:
            teamCol_text = TeamCols['away_c'].values[0]
        else:
            teamCol_text = TeamCols['home_c'].values[0]
        
        self.teamCol_text = teamCol_text
        
        # Refine `allGames` to only include games that the desired team played in
        allGames = allGames[
            ((allGames.home_team == team) | (allGames.away_team == team)) &
            (allGames.game_state == 'Final')
        ]
        
        # Iterate over all the games to collect player stats for each game played in the season
        team_dfs = []
        for game_id in allGames.game_id.unique():
            # Create a temp reference to GameStats
            temp = GameStats(game_id)
            temp.All()
            
            # Create a summary table of player stats for each game
            TS = TeamStats()
            TS.Summarize_Game(game_id, temp, False)
            
            # Collect the player stats for the relevant team from the game and store
            df = TS.Team1[1] if TS.Team1[0] == teamAbbrv else TS.Team2[1]
            team_dfs.append(df)
            
        self.team_dfs = team_dfs
        
        # Concat the team dfs and group the player stats
        full_df = pd.concat(team_dfs, axis = 0)
        full_df = full_df.groupby(['Player', 'ID']).sum()
        full_df.reset_index(inplace = True, drop = False)
        full_df.sort_values(
            by=['P', 'G', 'PPG', 'SHG', '1A', '2A', 'H'],
            inplace = True,
            ascending = False
        )
        full_df.reset_index(inplace=True, drop=True)
        
        # Calculate the games played for each player
        for i in full_df.index:
            player = full_df.loc[i, 'Player']
            GP = 0
            for df in team_dfs:
                if player in df.Player.unique():
                    GP += 1
                    
            full_df.loc[i, 'GP'] = int(GP)
        full_df['GP'] = full_df.GP.astype('int')
        
        # Reorder columns so GP is after the player info columns
        start_cols = ['Player', 'ID', '#', 'Pos.', 'GP']
        full_df = full_df[start_cols + [c for c in full_df.columns if c not in start_cols]]
        
        # Calculate average TOI per game and format the TOI column
        full_df['TOI'] = full_df['TOI'] / full_df['GP']
        full_df['TOI'] = full_df['TOI'].apply(
            lambda x: datetime.utcfromtimestamp(x).strftime('%H:%M:%S')
        )
        
        # Collect each players jersey number and position
        NHL_url = 'https://www.nhl.com/player/'
        for i in full_df.index:
            
            # Determine the appropriate NHL url to ping
            player = full_df.loc[i, 'Player']
            player = player.replace(' ', '-').lower()
            ID     = full_df.loc[i, 'ID']
            player_url = NHL_url + player + '-' + str(ID)
            
            # Collect the relevant info for the player
            page = requests.get(player_url).text
            page = page.replace('\n', '..')
            
            # Determine the players jersey number
            search_me = r'<h3 class="player-jumbotron-vitals__name-num">.*?</h3>'
            info = re.search(search_me, page).group(0)
            
            info = re.sub('<.*?>| {1,}|\.{1,}|#', ' ', info)
            try:
                jersey = info.split('|')[1].strip()
            except IndexError:
                jersey = ''
            full_df.loc[i, '#'] = jersey
            
            # Determine the players position
            search_me = r'<div class="player-jumbotron-vitals__attributes">.*?</div>'
            info = re.search(search_me, page).group(0)
            
            info = re.sub('<.*?>| {1,}|\.{1,}', ' ', info)
            position = info.split('|')[0].strip()
            full_df.loc[i, 'Pos.'] = position
            
        self.full_df = full_df

game_id = 2021020221
# game_id = 2021020030
# game_id = 2021021052

gs = GameStats(game_id)
gs.All()

TS = TeamStats()

TS.Summarize_Game(game_id, gs)
# TS.Team1
# TS.Team2

team = gs.Away
allGames = gs.Games
teamCol = '#236192'
TS.Summarize_Season(team, gs, teamCol)
