# -*- coding: utf-8 -*-
"""
Created on Sun Aug  8 13:21:23 2021.

@author: grega

`GameStats` will be used to collect, clean, and summarize all stats for an individual NHL game.
As of right now, my focus is only on ensuring this module will work for the individual games,
but from my experience building out the PreGame/Playoffs/TeamStats classes in the original
`myNHLstats.py`, this should also support being called iteratively to summarize multiple
games to create summaries by player, team, or league-wide stats.

This script houses the two main classes from the original `myNHLstats.py`; `GameStats` & `GameMap`.
However, `GameMap` will now be integrated into `GameStats` to eliminate the need to call both
classes separately when creating game recaps.

☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼
☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼ This should be good to go ☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼
☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼☼
"""
# Import necessary modules
import os
import pickle
import pandas as pd
from math import floor
from datetime import *
import datetime as dt
from dateutil import tz
import numpy as np

# import nhlstats
from nhlstats import list_plays, list_shots, list_games, list_shifts

def InHouse(x, y):
    
    # Define a useful function for determining if an event falls within the triangular
    # portions of the house
    def point_on_line(x):
        return 22 - ((x - 69) * (18 / 20))
    
    # Standardize the x input
    x = 0 if x is None else x
    y = 0 if y is None else y
    x = abs(x)
    
    # Check if the event occured in the large rectanglular portion of the house
    # 1st Rectangle | Domain: [54, 69],    Range: [-22, 22]
    if 54 <= x <= 69:
        if -22 <= y <= 22:
            return True
        
    # Check if the event occured in the small rectanglular portion of the house,
    # or the two triangular areas
    # 2nd Rectangle | Domain: (69, 89],    Range: [-4, 4]
    # 1st Triangele | Domain: (69, 89],    Range: [4, 22]
    # 2nd Triangele | Domain: (69, 89],    Range: [-22, -4]
    if 69 < x <= 89:
        if -4 <= y <= 4:
            return True
        
        elif 4 < abs(y) <= 22:
            y = abs(y)
            if y <= point_on_line(x):
                return True
    
    return False

class GameStats:
    """
    Collect, clean, and summarize all stats for an individual NHL game.
    
    Returns
    -------
    None.
    
    """
    
    def __init__(self, game_id, gr=None):
        # Store game id as a class attribute
        self.game_id   = game_id
        self.gr        = gr
        season         = str(game_id)[:4]
        self.season    = season
        game_type      = str(game_id)[4:6]
        self.game_type = game_type
        
        # Check if the directory exists for plays, shots, and shifts
        data_dir = os.path.join(os.getcwd(), 'Data', season, str(game_id))
        data_svd = os.path.isdir(data_dir)
        self.data_svd = data_svd
        self.data_dir = data_dir
        if data_svd:
            
            # If it does exist, read the raw data in and assign relative class attributes
            print('Data already saved locally')
            
        else:
            os.mkdir(data_dir)
        
        # Collect the plays/shots/shift JSON files provided by the nhlstats
        # module. Simultaneously convert JSON's into a pandas dataframe.
        self.plays = pd.DataFrame(list_plays(game_id))
        self.shots = pd.DataFrame(list_shots(game_id))
        self.shift = pd.DataFrame(list_shifts(game_id))
        
        # Create copies of the above dataframes that will be manipulated and used
        # for the X/Y positional data used in the RinkScatter plots.
        self.plays_xy = self.plays.copy()
        self.shots_xy = self.shots.copy()
        self.shift_xy = self.shift.copy()
        
        if gr is None:
            # If GameStats was called outside of GameRecap, define the necessary attributes
            # Collect the gameday info, which forever reason is usually wrong...
            gameDay  = pd.to_datetime(self.plays['datetime']).iloc[0].date()
            allGames = pd.DataFrame(
                list_games(
                    str(dt.date(gameDay.year - 1, 10, 12)),
                    str(gameDay)
                )
            )
            
            # Subset out the desired type of game (i.e. preseason, regular, playoffs)
            allGames = allGames[allGames.game_id.astype('str').str.slice(4, 6) == game_type]
            
            # Assign the gameDay attribute as a modified v of the gameDay variable,
            # adjusted for the timezone issue (which is why I think the info is usually wrong)
            self.gameDay = (
                pd.to_datetime(
                    self.plays['datetime']
                ).iloc[0] + dt.timedelta(hours=-4)
            ).date()
            
            self.Games = allGames
            self.Teams = allGames[allGames.game_id == game_id]
            self.Home  = self.Teams.home_team.iloc[0]
            self.Away  = self.Teams.away_team.iloc[0]
            
            # Collect team info provided in teamList.csv file in my github repo.
            tLUrl = 'https://raw.githubusercontent.com/AmeriFinn/LiveNHLstats/master/teamList.csv'
            tL = pd.read_csv(tLUrl)
            
            # Collect team abbreviations recognized by the NHL
            self.HomeAbrv = tL[tL.team_name == self.Home].team_abbrv.max()
            self.AwayAbrv = tL[tL.team_name == self.Away].team_abbrv.max()
            
            # Determine if this teams arena records x/y stat data the "normal"
            # way, or backwards. Note: Some arenas are less consistent about x/y
            # stat data. Both within games (where goals/shots/hits/etc. aren't
            # recorded properly by period) or between games (where the home team
            # will have 1st period stats recorded on opposite ends of the rink).
            # This is the best solution I have currently.
            self.direct_of_attack = \
                tL[tL.team_abbrv == self.HomeAbrv].normal_direct_of_play.max()
        else:
            # If GameStats was called from GameRecap, inherit the necessary attributes
            self.GameDay          = gr.GameDay
            self.Home             = gr.Home
            self.HomeAbrv         = gr.HomeAbrv
            self.Away             = gr.Away
            self.AwayAbrv         = gr.AwayAbrv
            self.direct_of_attack = gr.direct_of_attack
    
    def ModifyDFs(self):
        """
        Clean and make necessary modifications to stats df's collected from the NHL JSON files.
        
        Returns
        -------
        None.
        
        """
        # Add columns to plays DF for time elapsed.
        # Relevant for adding line markers for goals in plots.
        self.plays['Time']   = pd.to_datetime(
            self.plays.period_time, format="%M:%S"
        )
        # Then separate out the Hour, Minute, and Second for each play
        self.plays['Hour']   = self.plays['Time'].dt.hour
        self.plays['Minute'] = self.plays['Time'].dt.minute
        self.plays['Second'] = self.plays['Time'].dt.second
        
        # Change Time column to the game time elapsed
        for i in range(2, self.plays.period.unique().max() + 1):
            self.plays.loc[self.plays.period == i, 'Time'] = \
                self.plays[self.plays.period == i].Time + \
                dt.timedelta(minutes= 20 * (i - 1))
            
            self.plays.loc[self.plays.period == i, 'Minute'] = \
                self.plays[self.plays.period == i].Minute + (20 * (i - 1))
            
            if i >= 4:
                self.plays.loc[self.plays.period == i, 'Hour'] = \
                    self.plays[self.plays.period == i].Hour + (floor((i - 3) / 3))
        
        # Create a time index that with intervals of 5 seconds for entire game
        secns = [int(s) for s in range(0, 60, 5)] * 60
        mints = [floor(len(secns[:s]) / 12) for s in range(len(secns))]
        hours = [int(0) for m in mints]
        
        # Determine if the index needs to be adjusted for OT
        ## Additional adjustments will need to be made for playoff OT
        if 4 in self.plays.period.unique():
            OTsec = [int(s) for s in range(0, 60, 5)] * 5
            secns += OTsec
            mints += [floor(len(OTsec[:s]) / 12) for s in range(len(OTsec))]
            hours += [int(1) for s in OTsec]
        
        index = [dt.time(h, m, s) for h, m, s in zip(hours, mints, secns)]
        s     = pd.Series(index, name='Time')
        
        # Clean Time column format
        self.plays.Time = pd.Series(
            [dt.time(d.hour, d.minute, d.second) for d in self.plays.Time]
        )
        
        # Add in player_4 column in case the JSON file does not contain one
        if 'player_4' not in self.plays.columns:
            self.plays.loc[:, 'player_4'] = ''
            
        # Merge the new index with the plays, shots, and shifts df's
        # (This expands the dataframe to allow for prettier P5 charts)
        self.plays = pd.concat(
            [self.plays, pd.DataFrame(s)],
            ignore_index=True, join='outer', keys='Time'
        )
        self.plays.sort_values(by='Time', inplace=True, ascending=True)
        self.plays['datetime'] = pd.to_datetime(self.plays['datetime'])
        
    def AggregateData(self):
        """
        Calculate rolling totals for desired stats.
        
        Returns
        -------
        None.
        
        """
        def oppo_ident(team: str, Both: list) -> int:
            """
            Determines the index of the opposing team name in the list of both team acronyms.
            i.e. if team == 'COL' and Both == ['LAK', 'COL'], this returns 0. If team == 'LAK',
            then the function returns 1.
            This function ONLY works as intended when `Both` is exactly of length 2.
            
            Parameters
            ----------
            team : str
                The team that an event was recorded for.
            Both : list
                The 2-item list containing the Home and Away team abbreviations.
                
            Returns
            -------
            int
                The list index of the opposition team (always 0 or 1).
                
            """
            if len(Both) != 2:
                print(f"{Both} is not a list of length 2!")
                return 0
            
            for i, item in enumerate(Both):
                if item != team:
                    return i
            
            return 0
        
        Away, Home, plays = self.AwayAbrv, self.HomeAbrv, self.plays
        Both = [Away, Home]
        
        # Define new columns for goals, shots, hits, attempts, etc.
        ## Away: Even index numbs, Home: Odd index numbs
        newC = [
            Away + " Goals", Home + " Goals",
            Away + " Shots", Home + " Shots",
            Away + " Hits", Home + " Hits",
            Away + " Shot Attempts", Home + " Shot Attempts",
            Away + " Blocked Shots", Home + " Blocked Shots",
            Away + " Missed Shots", Home + " Missed Shots",
            Away + " Takeaways", Home + " Takeaways",
            Away + " Giveaways", Home + " Giveaways",
            Away + " Faceoff Wins", Home + " Faceoff Wins",
            Away + " House Shots", Home + " House Shots",
            Away + " House Attempts", Home + " House Attempts"
        ]
        
        # Create empty columns in plays DF for game stats
        for S in newC:
            plays[S] = 0
        
        # Loop through each row of the plays DF to aggregate event types
        plays.reset_index(inplace=True, drop=True)
        for i in plays.index:
            
            # Collect relevant items for each iteration
            event = self.plays.loc[i, 'event_type']
            team  = self.plays.loc[i, "team_for"]
            x, y = plays.loc[i, ['x', 'y']]
            
            # Record event types for the appropiate team.
            # There may be multiple event types in each row.
            ###################### Goals
            if event == 'GOAL':
                plays.loc[i, team + ' Goals'] = 1
                if InHouse(x, y):
                    plays.loc[i, [team + ' House Shots']] = 1
            
            ###################### Shots on Net
            if event in ['SHOT', 'GOAL']:
                plays.loc[i, team + ' Shots'] = 1
                if InHouse(x, y):
                    plays.loc[i, [team + ' House Shots']] = 1
            
            ###################### Shot Attempts
            if event in ['MISSED_SHOT', 'SHOT', 'GOAL']:
                plays.loc[i, team + ' Shot Attempts'] = 1
                if InHouse(x, y):
                    plays.loc[i, [team + ' House Attempts']] = 1
            
            ###################### Blocked Shots
            # Record the blocked shot for the blocking team,
            # and the shot attempt for the shooting team
            if event == 'BLOCKED_SHOT':
                oppo = Both[oppo_ident(team, Both)]
                
                # Record block for team that blocked the shot (is `team`)
                plays.loc[i, team + ' Blocked Shots'] = 1
                # Record shot attempt for team that had the shot blocked (is `oppo`)
                plays.loc[i, oppo + ' Shot Attempts'] = 1
                if InHouse(x, y):
                    plays.loc[i, [oppo + ' House Attempts']] = 1
                
                
            ###################### Missed Shots
            if event == 'MISSED_SHOT':
                plays.loc[i, team + ' Missed Shots'] = 1
            
            ###################### Hits
            if event == 'HIT':
                plays.loc[i, team + ' Hits'] = 1
            
            ###################### Takeaways
            if event == 'TAKEAWAY':
                plays.loc[i, team + ' Takeaways'] = 1
            
            ###################### Giveaways
            if event == 'GIVEAWAY':
                plays.loc[i, team + ' Giveaways'] = 1
                
            ###################### Faceoff Wins
            if event == 'FACEOFF':
                plays.loc[i, team + ' Faceoff Wins'] = 1
            
        # Calculate the cummulative sum over the course of the game for each
        # of the new stat columns.
        plays[newC] = plays[newC].cumsum(axis = 0)
        
        # Calculate the Shot Differential
        plays['Shot Differential'] = \
            abs(self.plays[Home + " Shots"] - self.plays[Away + " Shots"])
        
        self.plays = plays
        
    def prior_5(plays, Home, Away, col='Shots'):
        """
        Calculate rolling stats over a 5 minute window for the entire game.
        
        Parameters
        ----------
        plays : TYPE
            DESCRIPTION.
        Home : TYPE
            DESCRIPTION.
        Away : TYPE
            DESCRIPTION.
        col : TYPE, optional
            DESCRIPTION. The default is 'Shots'.
        
        Returns
        -------
        None.
        
        """
        # Create the 5-second interval index for each stat
        secns = [int(s) for s in range(0, 60, 5)] * 60
        mints = [floor(len(secns[:s]) / 12) for s in range(len(secns))]
        hours = [int(0) for m in mints]
        
        # Make adjustments for OT if needed
        if 4 in plays.period.unique():
            
            OTsec = [int(s) for s in range(0, 60, 5)] * 5
            secns += OTsec
            mints += [floor(len(OTsec[:s]) / 12) for s in range(len(OTsec) + 1)]
            hours += [int(1) for s in OTsec]
            
            # Create the full list
            prior_5 = [dt.time(h, m, s) for h, m, s in zip(hours, mints, secns)]
        else:
            prior_5 = [dt.time(h, m, s) for h, m, s in zip(hours, mints, secns)]
            prior_5.append(dt.time(1, 0, 0))
        
        prior_5 = plays[(plays.Time.isin(prior_5))][
            [f'{Home} {col}', f'{Away} {col}', 'Time']
        ]
        
        # Create empty columns for the stat over the past 1, 2, 3, 4, and 5 minutes
        for i in range(1, 6):
            prior_5.loc[:, f"{Home} {col} - Prior {i} min"] = 0
            prior_5.loc[:, f"{Away} {col} - Prior {i} min"] = 0
        
        # Loop through plays to to populate prior_{n}_minutes
        for i in range(prior_5.shape[0]):
            # for m, n in zip([3, 5], [0, 1]):
            for j in range(5):
                
                # Calculate prior j min stats - Home
                prior_5.iloc[i, 3 + (2 * j)] = \
                    (prior_5.iloc[max(0, i - (12 * j)), 0] - \
                     prior_5.iloc[max(0, i - (12 * (j + 1))), 0]) * ((5 - j) / 5)
                
                # Calculate prior j min stats - Home
                prior_5.iloc[i, 4 + (2 * j)] = \
                    (prior_5.iloc[max(0, i - (12 * j)), 1] - \
                     prior_5.iloc[max(0, i - (12 * (j + 1))), 1]) * ((5 - j) / 5)
                
        # Sum the weighted events across prior 1, 2, ... , 5 minutes
        prior_5.loc[:, f"{Home} {col} - Time Sum Weighted"] = \
            prior_5.loc[:, [f"{Home} {col} - Prior {i} min" for i in range(1, 6)]].sum(axis = 1)
        
        prior_5.loc[:, f"{Away} {col} - Time Sum Weighted"] = \
            prior_5.loc[:, [f"{Away} {col} - Prior {i} min" for i in range(1, 6)]].sum(axis = 1)
        
        # Sum the stats over the prior 1, 2, ... , 5 minutes to use in the P5 plots
        prior_5.reset_index(inplace = True, drop = True)
        for i in prior_5.index:
            for team in [Home, Away]:
                
                # Still within first 5 minutes of play
                if i <= 60:
                    prior_5.loc[i, f'{team} {col} - Prior 5 min'] = prior_5.loc[i, f'{team} {col}']
                    
                # Outside of first 5 minutes of play. Can calculate stats as usual
                else:
                    prior_5.loc[i, f'{team} {col} - Prior 5 min'] = \
                        prior_5.loc[i, f'{team} {col}'] - prior_5.loc[i - 60, f'{team} {col}']
                    
        # for team in [Home, Away]:
        #     prior_5.loc[:, f"{team} {col} - Prior 5 min"] = \
        #         prior_5.loc[:, f"{team} {col} - Prior 5 min"] + \
        #         (prior_5.loc[:, f"{team} {col} - Prior 4 min"] / 0.8) + \
        #         (prior_5.loc[:, f"{team} {col} - Prior 3 min"] / 0.6) + \
        #         (prior_5.loc[:, f"{team} {col} - Prior 2 min"] / 0.4) + \
        #         (prior_5.loc[:, f"{team} {col} - Prior 1 min"] / 0.2)
        
        # prior_5.loc[:, f"{Away} {col} - Prior 5 min"] = \
        #     prior_5.loc[:, [f"{Away} {col} - Prior {j} min" for j in range(1, 6)]].sum(axis = 1)
        
        # Drop unnecessary columns
        prior_5.drop([c for c in prior_5.columns if ('min' in c) and ('5' not in c)], axis = 1, inplace = True)
        
        return prior_5
        
    def Prior5Stats(self):
        """
        Create dataframe for prior 5 minute stat data for all stats.
        
        Returns
        -------
        None.
        
        """
        # Collect attributes needed for Prior_5 function
        Away, Home, plays = self.AwayAbrv, self.HomeAbrv, self.plays
        
        # Collect the prior 5 minute data needed to calculate a teams momentum
        shots     = GameStats.prior_5(plays, Home, Away, 'Shots')
        hits      = GameStats.prior_5(plays, Home, Away, 'Hits')
        goals     = GameStats.prior_5(plays, Home, Away, 'Goals')
        attempts  = GameStats.prior_5(plays, Home, Away, 'Shot Attempts')
        giveaways = GameStats.prior_5(plays, Home, Away, 'Giveaways')
        takeaways = GameStats.prior_5(plays, Home, Away, 'Takeaways')
        
        # Append the prior 5 minute df's for the selected stats
        # to their own attributes
        self.prior_5_shots = shots
        self.prior_5_hits  = hits
        self.prior_5_goals = goals
        self.prior_5_atmpt = attempts
        self.prior_5_tkwys = takeaways
        self.prior_5_gvwys = giveaways
        
        # Append a fully concatted df of all prior5 stats
        self.prior5        = pd.concat(
            [shots, hits, goals, attempts, giveaways, takeaways],
            axis=1
        )
        
        # Parse selected stats into one dataframe for calculating momentum
        momentum = pd.concat(
            [goals, shots, attempts, hits],
            axis = 1,
            levels = 'Time'
        )
        # Drop any columns that don't follow the naming conventions
        # for prior 5 stats (mostly just drops the rolling total columns)
        momentum = momentum[
            [col for col in momentum.columns if ' - ' in col] + ['Time']
        ]
        # Drop any duplicate rows/columns and set the index to the time column
        momentum = momentum.loc[
            ~momentum.Time.duplicated(),
            ~momentum.columns.duplicated()
        ]
        momentum.set_index('Time', inplace = True, drop = True)
        
        # Define a quick function to calculate weighted momentum based on event type
        def TeamMomentum(P5_goals, P5_shots, P5_atts, P5_hits):
            w_goal   = 5  # 1      # 6
            w_shot   = 3  # 2 / 3  # 4
            w_hit    = 2  # 1 / 2  # 3
            w_attmpt = 1  # 1 / 3  # 1
            
            return (P5_goals * w_goal) + (P5_shots * w_shot) + \
                    (P5_hits * w_hit) + (P5_atts * w_attmpt)
        
        # Calculate momentum for each team
        HMcols = [col for col in momentum.columns if Home in col]
        AMcols = [col for col in momentum.columns if Away in col]
        
        momentum.loc[:, f'{Home} - Momentum'] = momentum.apply(
            lambda x: TeamMomentum(
                x[HMcols[1]], x[HMcols[3]], x[HMcols[5]], x[HMcols[7]]
            ),
            axis=1
        )
        momentum.loc[:, f'{Away} - Momentum'] = momentum.apply(
            lambda x: TeamMomentum(
                x[AMcols[1]], x[AMcols[3]], x[AMcols[5]], x[AMcols[7]]
            ),
            axis=1
        )
        
        # Calculate the moving average of momentum for each team
        momentum[f'{Home} 5Min MA'] = momentum[f'{Home} - Momentum'].rolling(12).mean().round(1)
        momentum[f'{Away} 5Min MA'] = momentum[f'{Away} - Momentum'].rolling(12).mean().round(1)
        momentum[f'{Home} 1Min MA'] = momentum[f'{Home} - Momentum'].rolling(3).mean().round(1)
        momentum[f'{Away} 1Min MA'] = momentum[f'{Away} - Momentum'].rolling(3).mean().round(1)
            
        # Calculate the Net Momentum (Home Team Mom. - Away Team Mom.)
        # momentum.loc[:, 'Net_Momentum'] = \
        #     momentum[f'{Home} - Momentum'] - momentum[f'{Away} - Momentum']
        momentum.loc[:, 'Net_Momentum'] = \
            momentum[f'{Home} 5Min MA'] - momentum[f'{Away} 5Min MA']
        
        # Transpose the away team momentum
        momentum[f'{Away} 5Min MA'] *= -1
        momentum[f'{Away} 1Min MA'] *= -1
        
        # Create separate df's for the time periods where the home teams
        # momentum is dominant and when the away teams momentum is dominant.
        # This is necessary for the momentum plots to appropiately shade the
        # area under the curves in plotly.
        # "Dominant" momentum for the HOME team is when net momentum is POSITIVE.
        # "Dominnat" momentum for the AWAY team is when net momentum is NEGATIVE.
        HMom = momentum.copy()
        HMom.loc[HMom.Net_Momentum < 0, 'Net_Momentum'] = 0
        
        AMom = momentum.copy()
        AMom.loc[AMom.Net_Momentum >= 0, 'Net_Momentum'] = 0
        
        # Assign the momentum attibutes
        self.Momentum = momentum
        self.HomeMomentum, self.AwayMomentum = HMom, AMom
        
    def MenOnIce(self):
        """
        Collect penalty data.
        
        Returns
        -------
        plays : pd.DataFrame
            A modified plays df with penalty data included.
        pen_Home : list
            A list of start and end times for the home teams power plays.
        pen_Away : list
            A list of start and end times for the away teams power plays.
        
        """
        # Define function w/in MenOnIce to determine PP/PK stats
        def PenaltyComp(team, i, Home, Away, plays, pen_Home, pen_Away):
            # Input team as the team that took the penalty
            # Define refernces for short-handed team and power play team
            if team == Home:
                shTeam, ppTeam = Home, Away
            else:
                shTeam, ppTeam = Away, Home
            
            PenType = plays.loc[i, 'event_secondary_type']
            pim = 0
            
            # minors is currently unused.
            # Instead of checking that a penalty is in this list,
            # I will assume the penalty is a minor and use conditional
            # statemnts to check that assumption.
            minors = ['Boarding', 'Charging', 'Clipping', 'Elbowing', 'Hooking',
                      'Illegal check to the head', 'Kneeing', 'Roughing',
                      'Throwing equipment', 'Holding', 'Hooking', 'Interference',
                      'Tripping', 'Cross checking', 'Hi-sticking', 'Slashing',
                      'Delaying Game - Puck over glass', 'Delay of game',
                      'Delaying the game', 'Embellishment',
                      'Closing hand on puck', 'Interference - Goalkeeper',
                      'Too many men on the ice', 'Unsportsmanlike conduct']
            double = ['Hi stick - double minor', 'Cross check - double minor',
                      'Spearing']
            # Check if the penalty qualifies as a dobule minor
            pim = 4 if PenType in double else 2
            
            # Check if the penalty qualifies as a major
            majors = ['Fighting', 'Kicking', 'Slew-footing',
                      'Butt-ending', 'Match penalty']
            pim = 5 if PenType in majors else pim
            
            # Check if the penalty is actually a game misconduct
            miscon = ['Instigator - Misconduct', 'Misconduct', 'Game misconduct']
            if PenType in miscon:
                # Misconducts count towards the teams PIM, but don't reduce MOI
                pim = 10
                plays.loc[i:, shTeam + " PIM"] += pim
                return plays, pen_Home, pen_Away
            
            if (plays.loc[i, 'player_1'] == plays.loc[i + 1, 'player_1']) & \
               (plays.loc[i + 1, 'event_secondary_type'] in miscon) & (pim != 5):
                pim = 5
            
            # Take one man away from "Men on Ice" columns for shTeam
            # Record one power play for the pp team
            plays.loc[i, shTeam + " Men On Ice"]   -= 1
            plays.loc[i:, ppTeam + " Power Plays"] += 1
            
            # Record PIM in plays df
            plays.loc[i:, shTeam + " PIM"] += pim
            
            # Create references for start time of penalty and the period
            tempTime = plays.Time.iloc[i]
            tempPeri = plays.period.iloc[i]
            
            # Handle instances where a penalty occurs in last few minutes of
            # regulation and/or the game goes into OT
            if tempTime.minute + pim > 59:
                # Redefine the end time of the penalty to account
                # for rolling of the hour hand
                tempH, tempM = 1, (tempTime.minute + pim) - 60
            else:
                # The penalty does not relate to this special case
                tempH, tempM = 0, tempTime.minute + pim
            
            # Handle instances where a penalty is called in OT
            # The game managers (or ref's) NEVER call penalties in OT though...
            # ... Unless its so blatantly obvious that the receiving team would
            # literally call for blood...
            if tempPeri > 3:
                tempTime = dt.time(1, tempTime.minute, tempTime.second)
                tempH, tempM = 1, (tempTime.minute + pim)
            
            # Define the starting and ending game time for the penalty
            start, end = tempTime, dt.time(tempH, tempM, tempTime.second)
            
            x = i + 1  # temp row reference
            # Initiate while loop to handle MOI, PPG, SHG
            while (plays.Time.iloc[x] <= end):
                # Record one man down for PK in each row of plays df
                plays.loc[x, shTeam + " Men On Ice"] -= 1
                
                # Short handed goal scored
                if (plays.event_type.iloc[x] == 'GOAL') & \
                   (plays.team_for.iloc[x] == shTeam) & \
                   (plays.loc[x, shTeam + ' is_shg'] == False):
                    
                    # Penalized team scores, record SHG
                    plays.loc[x:, shTeam + " SHG"]    += 1
                    plays.loc[x, shTeam + ' is_shg']  = True
                
                # PP team scores. Record PPG & end penalty comprehension
                elif (plays.event_type.iloc[x] == 'GOAL') & \
                     (plays.team_for.iloc[x] == ppTeam) & \
                     (plays.loc[x, ppTeam + ' is_ppg'] == False):
                    
                    # Team on PP scores, record PPG, end the while loop
                    if plays.period.iloc[x] <= 3:
                        # In regulation, the penalty simply ends
                        end = dt.time(plays.Time.iloc[x].hour,
                                      int(plays.Minute.iloc[x]),
                                      int(plays.Second.iloc[x]))
                        plays.loc[x:, ppTeam + " PPG"]  += 1
                        plays.loc[x, ppTeam + ' is_ppg'] = True
                        break
                    
                    else:
                        # In OT, the penalty and game end
                        end = dt.time(plays.Time.iloc[x].hour,
                                      int(plays.Minute.iloc[x] - 60),
                                      int(plays.Second.iloc[x]))
                        plays.loc[x:, ppTeam + " PPG"]  += 1
                        plays.loc[x, ppTeam + ' is_ppg'] = True
                        break
                        
                else:
                    # continue with next iteration
                    x += 1
                
                # End while loop if end of plays df has been reached.
                # Happens when penalty is currently happening, or game
                # ends with time left on penalty.
                if x >= plays.shape[0]:
                    end = dt.time(plays.Time.iloc[x - 1].hour,
                                  min(int(plays.Minute.iloc[x - 1]), 59),
                                  min(int(plays.Second.iloc[x - 1]), 59))
                    break
            
            # Append penalty data for relevant team
            # Adjust start/end time to round seconds to nearest 5 second interval
            # This is necessary so plotly doesn't get confused :/...
            # Not the ideal solution, but one that works.
            start = dt.time(
                start.hour, start.minute, min(5 * round(start.second / 5), 55)
            )
            end   = dt.time(
                end.hour, end.minute, min(5 * round(end.second / 5), 55)
            )
            pen_Home.append((start, end)) if team == Home else \
                pen_Away.append((start, end))
            
            # return updated plays df and penalty lists
            return plays, pen_Home, pen_Away
        
        # Collect the necessary attributes
        Away = self.AwayAbrv
        Home = self.HomeAbrv
        plays = self.plays
        
        # Each team starts with 5 men on ice, 0 PPG, 0 SHG, & 0 Penalties.
        # Also create boolean reference columns and PIM counter
        plays[Home + " Men On Ice"], plays[Away + " Men On Ice"] = 5, 5
        
        plays[Home + " PPG"], plays[Away + " PPG"] = 0, 0
        plays[Home + " SHG"], plays[Away + " SHG"] = 0, 0
        
        plays[Home + " is_ppg"], plays[Away + " is_ppg"] = False, False
        plays[Home + " is_shg"], plays[Away + " is_shg"] = False, False
        
        plays[Home + " Power Plays"] = 0
        plays[Away + " Power Plays"] = 0
        
        plays[Home + " PIM"] = 0
        plays[Away + " PIM"] = 0
        
        pen_Home = []
        pen_Away = []
        
        # Forward fill any missing data for the Hour, Minute, Second column
        plays[['Minute', 'Second']] = plays[['Minute', 'Second']].fillna(method = 'ffill')
        
        # Loop through each record of plays df to aggregate PP/PK data
        for i in range(0, plays.shape[0]):
            # if (plays.event_type.iloc[i] == 'PENALTY') & \
            #    (plays.event_secondary_type.iloc[i] != 'Fighting'):
            if plays.event_type.iloc[i] == 'PENALTY':
                
                plays, pen_Home, pen_Away = PenaltyComp(
                    plays.team_for.iloc[i], i, Home, Away,
                    plays, pen_Home, pen_Away
                )
        
        # Convert list of tuples into nested lists with
        # start/end times of penalties.
        HomePens, AwayPens = \
            [[i[0], i[1]] for i in pen_Home], [[x[0], x[1]] for x in pen_Away]
        
        # Update plays df and add penalty list attributes
        self.plays, self.HomePens, self.AwayPens = plays, HomePens, AwayPens
        
    def GoalsDF(self):
        """
        Create dataframe of goals data to be used in `GameScatter`.
        
        Returns
        -------
        df : TYPE
            DESCRIPTION.
        max_Goal : TYPE
            DESCRIPTION.
            
        """
        plays, Home, Away = self.plays, self.HomeAbrv, self.AwayAbrv
        
        def Create(plays, team):
            """
            Create a time series of goals with minute and secod references.
            
            Used in top plot for vertical goal bars
            
            Parameters
            ----------
            plays : TYPE
                DESCRIPTION.
            team : TYPE
                DESCRIPTION.
            """
            # Create a copy of the plays df to modify
            df = plays.copy()
            
            # Set the index and separate out goals as they were scored
            df.set_index("Time", inplace=True, drop=True)
            
            # Ensure there is a column for player_4 data.
            # There may be instances where a player_3 column needs
            # needs to be added, but this has not been necessary yet...
            if 'player_4' not in df.columns:
                df.loc[:, 'player_4'] = ''
            
            # Duplicates following the first instance of a goal must be dropped
            cols = [team + " Goals", 'period', 'period_time'] + \
                   [col for col in ['player_1', 'player_2', 'player_3', 'player_4'] \
                    if col in df.columns]
            
            # Set up error handling in the event a team scored no goals
            if df[(df.event_type == 'GOAL') & (df.team_for == team)].empty:
                return pd.DataFrame(columns=cols), 0
            
            df = df[(df.event_type == 'GOAL') & (df.team_for == team)][cols]
            df.reset_index(inplace=True, drop=False)
            
            # Convert Time column from objects to datetimes
            df.Time = pd.to_datetime(df.Time, format='%H:%M:%S').dt.time
            # Create a string references
            df['strTime'] = df.Time.apply(lambda x: x.strftime('%H:%M:%S'))
            
            # Parse out the Hour, Minute, and Second that each goal is scored
            df['Hour'] = pd.to_datetime(df.Time, format='%H:%M:%S').dt.hour
            df['Minute'] = pd.to_datetime(df.Time, format='%H:%M:%S').dt.minute
            df['Second'] = pd.to_datetime(df.Time, format='%H:%M:%S').dt.second
            
            # Reset the index and determine total goals scored by the team
            df.set_index('strTime', inplace=True)
            max_Goal = df[team + " Goals"].max()
            
            return df, max_Goal
        
        # Home & Away Team goals data
        home_goals, max_hGoal = Create(plays, Home)
        away_goals, max_aGoal = Create(plays, Away)
        
        ### TODO
        # Collect the max number of goals scored to use as a height limit
        # in the `GameScatter` plot. This was necessary to do when I was
        # using mpl to create the plots, but might not be necessary w/ Plotly
        max_Goal = max([max_aGoal, max_hGoal])
        
        # Assign results as a list attribute. Mostly out of laziness,
        # but it works for now...
        self.Goals = [home_goals, away_goals, max_hGoal, max_aGoal, max_Goal]
        
    def SumDF(self):
        """
        Create summary stats dataframe of all stats for each team.
        
        Returns
        -------
        TYPE
            DESCRIPTION.
        
        """
        plays, Home, Away = self.plays, self.HomeAbrv, self.AwayAbrv
        
        # Determine if game went to OT and make necessary adjustments if so
        self.OT = True if 4 in plays.period.unique() else False
        self.SO = True if (5 in plays.period.unique() and self.game_type != '03') else False
        
        if self.OT:
            # Game went to OT. Regular season OT means 4 period, Playoff OT means at least 4.
            periods = int(plays.period.max()) + 1
        else:
            periods = 3 + 1  # Add 1 to inlcude room for a summary column
            
        # Define the summary stats we want to collect
        myStats = ["Goals", "Shots", "Shot %", "House Shots", "Shot Attempts",
                   "S/SA %", "Blocked Shots", "Missed Shots", "House Attempts",
                   "Faceoff Wins", "Hits", "Power Plays", "PPG", "SHG", "PIM",
                   "Takeaways", "Giveaways"]
        dic = {}
        
        # Initiate loop through the `plays` df to collect summary stats by period
        for p in range(1, periods, 1):
            tempHlst = []  # Reset temp lists for each loop of `p`
            tempAlst = []
            
            for i in myStats:
                
                # Calculate each teams shot percentage (goals / shots on net)
                if i == "Shot %":
                    tempH = "{:.1%}".format(tempHlst[0] / max(tempHlst[1], 1))
                    tempA = "{:.1%}".format(tempAlst[0] / max(tempAlst[1], 1))
                    
                    tempHlst.append(tempH)
                    tempAlst.append(tempA)
                    continue
                
                # Calculate each teams shot attempt percentage (shots on net / shot attempts)
                if i == "S/SA %":
                    tempH = "{:.1%}".format(tempHlst[1] / max(tempHlst[-1], 1))
                    tempA = "{:.1%}".format(tempAlst[1] / max(tempAlst[-1], 1))
                    
                    tempHlst.append(tempH)
                    tempAlst.append(tempA)
                    continue
                
                ## TODO: Figure out how to handle instances where the
                ##       current period has not ended
                tempH = plays[(plays.event_type == 'PERIOD_OFFICIAL') & \
                              (plays.period == p)][f"{Home} {i}"].max()
                tempA = plays[(plays.event_type == 'PERIOD_OFFICIAL') & \
                              (plays.period == p)][f"{Away} {i}"].max()
                
                if (plays[(plays.event_type == 'PERIOD_OFFICIAL') & (plays.period == p)].shape[0] == 0) & (p in plays.period.unique()):
                    tempH = plays[(plays.period == p)][f"{Home} {i}"].max()
                    tempA = plays[(plays.period == p)][f"{Away} {i}"].max()
                
                tempHlst.append(tempH)
                tempAlst.append(tempA)
            
            p = p if p < 4 else 'OT'
            dic[(p, Home)] = tempHlst
            dic[(p, Away)] = tempAlst
            
        # Create DF of selected summary stats
        # (Sum stats are presented as rolling totals here)
        SumStats = pd.DataFrame.from_dict(dic, orient='columns')
        
        # Transpose and rename columns for a better looking layout
        SumStats = SumStats.T
        SumStats.columns = myStats
        
        # Create a pandas index slice reference
        idx = pd.IndexSlice
        
        # Determine if an extra column is needed for OT stats
        # Adjustments need to be made for post-season OT (@ CBJ-TBL 2020 RD1 G1)
        if self.OT is False:
            finalPeriod = plays.period.max()
        else:
            finalPeriod = 'OT'
        
        # Collect the total game stats
        FS = SumStats.loc[idx[finalPeriod, :], :]
        FS.index = pd.MultiIndex.from_tuples(
            [('Game Total', Home), ('Game Total', Away)],
            names=['Period', 'Team']
        )
        
        # Define list of column names used to calculate sum stats by period
        SCols = [
            "Goals", "Shots", "House Shots", "Shot Attempts", "House Attempts",
            "Blocked Shots", "Missed Shots", "Faceoff Wins", "Hits", "PPG", "Power Plays",
            "SHG", "PIM", "Takeaways", "Giveaways"
        ]
        
        # Separate out home & away team sum stats for 2nd & 3rd periods
        for team in [Home, Away]:
            # Separate out 2nd period stats
            SumStats.loc[idx[2, team], SCols] = \
                SumStats.loc[idx[2, team], SCols] - \
                SumStats.loc[idx[1, team], SCols]
            
            # Separate out 3rd period stats
            SumStats.loc[idx[3, team], SCols] = \
                SumStats.loc[idx[3, team], SCols] - \
                SumStats.loc[idx[2, team], SCols] - \
                SumStats.loc[idx[1, team], SCols]
            
            # If needed, separate out the OT stats
            # Note: This currently groups all OT stats together.
            #       So, when there is a game that goes to 2OT+ in playoffs,
            #       all of that data will be grouped. Otherwise the table
            #       becomes unreadable... Could come back to this if desired
            if self.OT:
                SumStats.loc[idx['OT', team], SCols] = \
                    SumStats.loc[idx['OT', team], SCols] - \
                    SumStats.loc[idx[3, team], SCols] - \
                    SumStats.loc[idx[2, team], SCols] - \
                    SumStats.loc[idx[1, team], SCols]
        
        # Concat the total game stats with the per-period stats
        SS = pd.concat([FS, SumStats])
        
        # Calculate a few percentage stats
        SS['Shot %'] = (SS["Goals"] / SS['Shots'].replace(0, 1)) * 100
        SS['Shot %'] = pd.Series(
            ["{0:.1f}%".format(val) for val in SS['Shot %']],
            index = SS.index
        )
        
        SS['S/SA %'] = (SS['Shots'] / SS['Shot Attempts'].replace(0, 1)) * 100
        SS['S/SA %'] = pd.Series(
            ["{0:.1f}%".format(val) for val in SS['S/SA %']],
            index = SS.index
        )
        
        # Transpose the table for a better look in the final visual
        SS = SS.T
        
        # Calculate the Faceoff win percentages
        # Collect the index value of the `Faceoff Wins` row
        row = 9  # Need to figure out a way to dynamically define this variable
        for i in range(0, len(SS.columns) - 1, 2):
            HFO = SS.iloc[row, i]
            AFO = SS.iloc[row, i + 1]
            TFO = HFO + AFO
            # Handle instances where the period had technically started,
            # but the puck has not been dropped
            TFO = TFO if TFO != 0 else 1
            
            SS.iloc[row, i] = f'{str(round(100 * HFO / TFO, 1))}%<br>({str(HFO)})'
            SS.iloc[row, i + 1] = f'{str(round(100 * AFO / TFO, 1))}%<br>({str(AFO)})'
        
        self.SumStats = SS
        
    def XY_GSA_HTG(self):
        """
        Subset out the home team and away team goals/shots/attempts, as well as hits/TA's/GA's.
        
        Returns
        -------
        None.
        
        """
        # =============================================================================
        #                                   GSA Data                                  =
        # =============================================================================
        shots = self.shots_xy
        Home = self.HomeAbrv
        Away = self.AwayAbrv
        
        # Define the list of columns to collect
        cols = ['event_type', 'team_for', 'x', 'y', 'period',
                'player_1', 'player_2', 'player_3', 'player_4', 'period_time']
        # Drop any of the above columns from the list if they do not appear in the JSON file
        cols = [c for c in cols if c in shots.columns]
        
        # Subset the `shots` df to the desired columns
        XY_Shots = shots[cols].copy()
        
        # Odd logic problem where adjustments for direction of attack is not
        # consistent across all arenas. Introduced the direct_of_attack variable
        # in the __init__ method to solve this issue.
        
        # Flip the game stat locations for even-numbered periods (P2, OT1, OT3, etc.)
        XY_Shots.loc[XY_Shots.period % 2 == 0, 'x'] *= -1
        XY_Shots.loc[XY_Shots.period % 2 == 0, 'y'] *= -1
        
        # The above transformations should put away stats on the left (negative x values),
        # and home stats on the right (positive x values).
        # Depending on what arena the game is being played in, we may need the opposite of that.
        if self.direct_of_attack:
            XY_Shots.loc[:, 'x'] *= -1
            XY_Shots.loc[:, 'y'] *= -1
        
        ## Subset out each team's goals, shots, and shot attempts
        # Home team stats
        XYhome = XY_Shots[(XY_Shots.team_for == Home)].copy()
        # Home team goals
        XYhomeG = XYhome[XYhome.event_type == 'GOAL'].copy()
        # Home team shots
        XYhomeS = XYhome[XYhome.event_type == 'SHOT'].copy()
        # Home team shot attempts (missed + blocked shots)
        XYhomeSA = XY_Shots[
            ((XY_Shots.team_for == Home) & (XY_Shots.event_type == 'MISSED_SHOT')) | \
            ((XY_Shots.team_for == Home) & (XY_Shots.event_type == 'BLOCKED_SHOT'))
        ].copy()
        # Flip coordinates for Shot Attempts
        # XYhomeSA['x'] *= -1
        # XYhomeSA['y'] *= -1
        
        # TODO - Make necessary adjustments to the comments below
        # Transpoe the blocked shot data by 180 degrees since the data provided by the NHL
        # records the blocked shot data for the team that had the puck hit their player.
        # Therefore, we also need to reassign the `team_for` labels
        XYhomeSA.loc[XYhomeSA.event_type == 'BLOCKED_SHOT', 'x'] *= -1
        XYhomeSA.loc[XYhomeSA.event_type == 'BLOCKED_SHOT', 'y'] *= -1
        XYhomeSA.loc[:, 'team_for'] = Home
        
        # Away team stats
        XYaway = XY_Shots[(XY_Shots.team_for == Away)].copy()
        # Away team goals
        XYawayG = XYaway[XYaway.event_type == 'GOAL'].copy()
        # Away team shots
        XYawayS = XYaway[XYaway.event_type == 'SHOT'].copy()
        # Away team shot attempts (missed + blocked shots)
        XYawaySA = XY_Shots[
            ((XY_Shots.team_for == Away) & (XY_Shots.event_type == 'MISSED_SHOT')) | \
            ((XY_Shots.team_for == Away) & (XY_Shots.event_type == 'BLOCKED_SHOT'))
        ].copy()
        # Flip coordinates for Shot Attempts
        # XYawaySA['x'] *= -1
        # XYawaySA['y'] *= -1
        
        # TODO - Make necessary adjustments to the comments below
        # Transpoe the blocked shot data by 180 degrees since the data provided by the NHL
        # records the blocked shot data for the team that had the puck hit their player.
        # Therefore, we also need to reassign the `team_for` labels
        XYawaySA.loc[XYawaySA.event_type == 'BLOCKED_SHOT', 'x'] *= -1
        XYawaySA.loc[XYawaySA.event_type == 'BLOCKED_SHOT', 'y'] *= -1
        XYawaySA.loc[:,'team_for'] = Away
        
        # Reset index of each stats df for the home team to start at 1
        ## TODO - determine if this is relevant for the Shots & Shot Atempts dfs
        XYhomeS.index  = np.arange(1, len(XYhomeS) + 1)
        XYhomeSA.index = np.arange(1, len(XYhomeSA) + 1)
        XYhomeG.index  = np.arange(1, len(XYhomeG) + 1)
        
        # Assign relevant market styles to use in the Rink Scatters
        XYhomeS['MarkerStyle']  = 'circle'
        XYhomeSA['MarkerStyle'] = 'x'
        XYhomeG['MarkerStyle']  = XYhomeG.index.copy(dtype='str')
        
        # Reset index of each stats df for the home team to start at 1
        ## TODO - determine if this is relevant for the Shots & Shot Atempts dfs
        XYawayS.index  = np.arange(1, len(XYawayS) + 1)
        XYawaySA.index = np.arange(1, len(XYawaySA) + 1)
        XYawayG.index  = np.arange(1, len(XYawayG) + 1)
        
        # Assign relevant market styles to use in the Rink Scatters
        XYawayS['MarkerStyle']  = 'circle'
        XYawaySA['MarkerStyle'] = 'x'
        XYawayG['MarkerStyle']  = XYawayG.index.copy(dtype='str')
        
        # Assign home and away team stats as individual class attributes
        self.HomeG, self.HomeS, self.HomeSA = XYhomeG, XYhomeS, XYhomeSA
        self.AwayG, self.AwayS, self.AwaySA = XYawayG, XYawayS, XYawaySA
        
        # =============================================================================
        #                                   HTG Data                                  =
        # =============================================================================
        plays = self.plays_xy
        
        cols = ['event_type', 'team_for', 'x', 'y', 'period',
                'player_1', 'player_2', 'player_3', 'player_4', 'period_time']
        cols = [col for col in cols if col in plays.columns]
        
        ## Standardize direction of play/attack for each team
        # Flip the game stat locations for even-numbered periods
        plays.loc[plays.period % 2 == 0, 'x'] *= -1
        plays.loc[plays.period % 2 == 0, 'y'] *= -1
        
        # Above transformations put away stats on the left, and home stats on the right.
        # Depending on the rink the game is being played at and from what angle / side of the rink
        # the stats team views the game, we may need to transform the data again.
        if self.direct_of_attack:
            plays.loc[:, 'x'] *= -1
            plays.loc[:, 'y'] *= -1
        
        # Subset out the desired stats
        hits = plays[plays.event_type == 'HIT'][cols]
        take = plays[plays.event_type == 'TAKEAWAY'][cols]
        give = plays[plays.event_type == 'GIVEAWAY'][cols]
        face = plays[plays.event_type == 'FACEOFF'][cols]
        
        # Further subset out the desired stats for each team
        XYhomeH = hits[hits.team_for == Home]   # x,y data for home team hits
        XYawayH = hits[hits.team_for == Away]   # x,y data for away team hits
        
        XYhomeT = take[take.team_for == Home]   # x,y data for home team takeaways
        XYawayT = take[take.team_for == Away]   # x,y data for away team takeaways
        
        XYhomeGA = give[give.team_for == Home]  # x,y data for home team giveaways
        XYawayGA = give[give.team_for == Away]  # x,y data for away team giveaways
        
        # Possibly useful for looking at draws likely to win/lose
        XYhomeF = face[face.team_for == Home]   # Home team faceoff wins xy data
        XYawayF = face[face.team_for == Away]   # Away team faceoff wins xy data
        
        # Reset the indexes to start at 1
        XYhomeH.index  = np.arange(1, len(XYhomeH) + 1)
        XYhomeT.index  = np.arange(1, len(XYhomeT) + 1)
        XYhomeGA.index = np.arange(1, len(XYhomeGA) + 1)
        
        XYawayH.index  = np.arange(1, len(XYawayH) + 1)
        XYawayT.index  = np.arange(1, len(XYawayT) + 1)
        XYawayGA.index = np.arange(1, len(XYawayGA) + 1)
        
        # Assign home and away team stats as individual class attributes
        self.HomeH, self.HomeT, self.HomeGA, self.HomeFO = XYhomeH, XYhomeT, XYhomeGA, XYhomeF
        self.AwayH, self.AwayT, self.AwayGA, self.AwayFO = XYawayH, XYawayT, XYawayGA, XYawayF
        
    def All(self):
        
        # if self.data_svd is False:
        self.ModifyDFs()
        self.AggregateData()
        self.Prior5Stats()
        self.MenOnIce()
        self.GoalsDF()
        self.SumDF()
        self.XY_GSA_HTG()
        
        # Save a summary dictionary of key stats
        # Start with basic info for each team
        GameDay  = self.gameDay
        HomeAbrv = self.HomeAbrv
        AwayAbrv = self.AwayAbrv
        WentToOT = self.OT
        WentToSO = self.SO
        
        # Start looking at actual stats - Goals
        plays = self.plays.copy()
        HomeGoals = plays[f'{HomeAbrv} Goals'].max()
        AwayGoals = plays[f'{AwayAbrv} Goals'].max()
        
        # Determine who won
        Winner = HomeAbrv if HomeGoals > AwayGoals else AwayAbrv
        
        # Determine the type of game
        GameType = self.game_type
        if GameType == '01':
            GameType = 'Pre-Season'
        elif GameType == '02':
            GameType = 'Regular Season'
        else:
            GameType = 'Post-Season'
        
        # Collect the other summary stats
        HomeShots   = plays[f'{HomeAbrv} Shots'].max()
        HomeAtpmts  = plays[f'{HomeAbrv} Shot Attempts'].max()
        HomeHouseS  = plays[f'{HomeAbrv} House Shots'].max()
        HomeHouseSA = plays[f'{HomeAbrv} House Attempts'].max()
        HomeHits    = plays[f'{HomeAbrv} Hits'].max()
        HomePPs     = plays[f'{HomeAbrv} Power Plays'].max()
        HomePPG     = plays[f'{HomeAbrv} PPG'].max()
        HomePIM     = plays[f'{HomeAbrv} PIM'].max()
        HomeFOW     = plays[f'{HomeAbrv} Faceoff Wins'].max()
        AwayShots   = plays[f'{AwayAbrv} Shots'].max()
        AwayAtpmts  = plays[f'{AwayAbrv} Shot Attempts'].max()
        AwayHouseS  = plays[f'{AwayAbrv} House Shots'].max()
        AwayHouseSA = plays[f'{AwayAbrv} House Attempts'].max()
        AwayHits    = plays[f'{AwayAbrv} Hits'].max()
        AwayPPs     = plays[f'{AwayAbrv} Power Plays'].max()
        AwayPPG     = plays[f'{AwayAbrv} PPG'].max()
        AwayPIM     = plays[f'{AwayAbrv} PIM'].max()
        AwayFOW     = plays[f'{AwayAbrv} Faceoff Wins'].max()
        
        DataDict = dict(
            GameDay     = GameDay,
            HomeAbrv    = HomeAbrv,
            AwayAbrv    = AwayAbrv,
            WentToOT    = WentToOT,
            WentToSO    = WentToSO,
            Winner      = Winner,
            GameType    = GameType,
            HomeGoals   = HomeGoals,
            HomeShots   = HomeShots,
            HomeAtpmts  = HomeAtpmts,
            HomeHouseS  = HomeHouseS,
            HomeHouseSA = HomeHouseSA,
            HomeHits    = HomeHits,
            HomePPs     = HomePPs,
            HomePPG     = HomePPG,
            HomePIM     = HomePIM,
            HomeFOW     = HomeFOW,
            AwayGoals   = AwayGoals,
            AwayShots   = AwayShots,
            AwayAtpmts  = AwayAtpmts,
            AwayHouseS  = AwayHouseS,
            AwayHouseSA = AwayHouseSA,
            AwayHits    = AwayHits,
            AwayPPs     = AwayPPs,
            AwayPPG     = AwayPPG,
            AwayPIM     = AwayPIM,
            AwayFOW     = AwayFOW
        )
        
        self.DataDict = DataDict
        
        # Save the summary dictionary
        with open(os.path.join(self.data_dir, 'summary_data.bin'), 'wb') as f:
            pickle.dump(DataDict, f)
            f.close()
        
        ## Test the load feature
        # with open(os.path.join(self.data_dir, 'summary_data.bin'), 'rb') as f:
        #     test = pickle.load(f)
        #     f.close()
            
        # Save the entire class object with summarized and cleaned data
        with open(os.path.join(self.data_dir, 'cleaned_data.bin'), 'wb') as f:
            pickle.dump(self, f)
            f.close()
        
        # # Test the load feature
        # with open(os.path.join(self.data_dir, 'cleaned_data.bin'), 'rb') as f:
        #     test = pickle.load(f)
        #     f.close()

game_id = 2021030111
gs = GameStats(game_id)
gs.All()
