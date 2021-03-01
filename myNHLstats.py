# -*- coding: utf-8 -*-
"""
Created on Sat Jan 30 20:18:23 2021

This is essentionally version 2 of myNHLstats.

I will start by translating the matplotlib plots
into a single plotly figure. This will require the
GameStats and GameMap classes to be either combined,
or called by a seperate class procedure dedicated
to creating the plotly figure. The latter option
is the one I will start my draft with.

Later, I'll revist the other class methods, procedures, and attributes
to remove erroneous lines

@author: grega
"""

# Import necessary modules
import pandas as pd
import numpy as np
import math
#import os
from datetime import *
import datetime as dt
from datetime import time, date
import time

import nhlstats
from nhlstats import list_plays, list_shots, list_shifts, list_games
from nhlstats.formatters import csv

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

class GameStats:
    """
    Collect time series data.

    Returns
    -------
    None.

    """

    def __init__(self, game_id):

        # Store game id as a class attribute
        self.game_id = game_id

        # Collect the plays, shots, and shift JSON files
        # provided by the nhlstats module. Simultaneously,
        # convert JSON files into a pandas data frame
        self.plays = pd.DataFrame(list_plays(game_id))
        self.shots = pd.DataFrame(list_shots(game_id))
        self.shift = pd.DataFrame(list_shifts(game_id))

        self.gameDay = pd.to_datetime(self.plays['datetime']).iloc[0].date()
        self.Teams   = pd.DataFrame(list_games(str(self.gameDay + dt.timedelta(days=-1)),
                                               str(self.gameDay)))
        self.Teams   = self.Teams[self.Teams.game_id == game_id]

        self.Home = self.Teams.home_team.iloc[0]
        self.Away = self.Teams.away_team.iloc[0]

        # Collect team info provided in teamList.csv file in my github repos.
        tLUrl = 'https://raw.githubusercontent.com/AmeriFinn/LiveNHLstats/master/teamList.csv'
        tL = pd.read_csv(tLUrl)

        # Collect team abbreviations recognized by the NHL
        self.HomeAbrv = tL[tL.team_name == self.Home].team_abbrv.max()
        self.AwayAbrv = tL[tL.team_name == self.Away].team_abbrv.max()

        # Collect the two primary colors (in Hex code format) listed in
        # team logo copyright
        self.Home_Color1 = tL[tL.team_abbrv == self.HomeAbrv].home_c.max()
        self.Home_Color2 = tL[tL.team_abbrv == self.HomeAbrv].away_c.max()

        self.Away_Color1 = tL[tL.team_abbrv == self.AwayAbrv].away_c.max()
        self.Away_Color2 = tL[tL.team_abbrv == self.AwayAbrv].home_c.max()

    def ModifyDFs(self):
        """
        .

        Returns
        -------
        None.

        """
        # Add columns to plays DF for time elapsed.
        # Relevant for adding line markers for goals in plots.
        self.plays['Time']   = pd.to_datetime(self.plays.period_time, format="%M:%S")
        self.plays['Hour']   = self.plays['Time'].dt.hour
        self.plays['Minute'] = self.plays['Time'].dt.minute
        self.plays['Second'] = self.plays['Time'].dt.second

        # Change Time column from the time of the period to the game time elapsed
        for i in range(2, self.plays.period.unique().max() + 1):
            self.plays.loc[self.plays.period == i, 'Time'] = \
                self.plays[self.plays.period == i].Time + dt.timedelta(minutes=20 * (i - 1))

            self.plays.loc[self.plays.period == i, 'Minute'] = \
                self.plays[self.plays.period == i].Minute + (20 * (i - 1))
                
            if i >= 4:
                self.plays.loc[self.plays.period == i, 'Hour'] = \
                    self.plays[self.plays.period == i].Hour + (1 * math.floor((i - 3) / 3))

        # Create a time index that spans every 5 seconds of every minute for the entire game
        secns = [int(s) for s in range(0, 60, 5)] * 60
        mints = [math.floor(len(secns[:s]) / 12) for s in range(len(secns))]
        hours = [int(0) for m in mints]

        # Determine if the index needs to be adjusted for OT
        ## Additional adjustments will need to be made for playoff OT
        if 4 in self.plays.period.unique():
            OTsec = [int(s) for s in range(0, 60, 5)] * 5
            secns = secns + OTsec
            mints = mints + [math.floor(len(OTsec[:s]) / 12) for s in range(len(OTsec))]
            hours = hours + [int(1) for s in OTsec]

        index = [dt.time(h, m, s) for h, m, s in list(zip(hours, mints, secns))]
        s     = pd.Series(index, name='Time')

        # Clean Time column format
        self.plays.Time = pd.Series([dt.time(d.hour, d.minute, d.second) for d in self.plays.Time])

        # Add in player_4 column in case the JSON file does not contain one
        if 'player_4' not in self.plays.columns:
            self.plays.loc[:, 'player_4'] = ''

        # Merge the new index with the plays, shots, and shifts df's
        self.plays = pd.concat([self.plays, pd.DataFrame(s)],
                               ignore_index=True, join='outer', keys='Time')
        self.plays.sort_values(by='Time', inplace=True, ascending=True)

        #self.plays.set_index('Time', inplace=True, drop=True)
        self.plays['datetime'] = pd.to_datetime(self.plays['datetime'])

        # Modify the gameDay attribute by converting date to a standard string format
        gameDay      = self.plays.datetime.iloc[0]
        self.gameDay = dt.datetime(year=gameDay.year, month=gameDay.month, day=gameDay.day)
        self.gameDay = dt.datetime.strftime(self.gameDay, '%d-%b-%Y')

    def AggregateData(self):
        """
        Calculate rolling totals for desired stats.

        Returns
        -------
        None.

        """
        Away  = self.AwayAbrv
        Home  = self.HomeAbrv
        plays = self.plays

        # Add empty columns for shots and goals
        newC = [Away + " Goals", Home + " Goals",
                Away + " Shots", Home + " Shots",
                Away + " Hits", Home + " Hits",
                Away + " Shot Attempts", Home + " Shot Attempts",
                Away + " Blocked Shots", Home + " Blocked Shots",
                Away + " Missed Shots", Home + " Missed Shots"]
        # Create empty columns in plays DF for game stats
        for S in newC:
            plays[S] = 0

        # Loop through each row of the plays DF to aggregate event types
        plays.reset_index(inplace=True, drop=True)
        for i in plays.index:

            event = self.plays.loc[i, 'event_type']
            team = self.plays.loc[i, "team_for"]

            ###################### Goals
            if event == 'GOAL':
                plays.loc[i, team + ' Goals'] = 1
            ###################### Shots on Net
            if event in ['SHOT', 'GOAL']:
                plays.loc[i, team + ' Shots'] = 1
            ###################### Shot Attempts
            if event in ['MISSED_SHOT', 'SHOT', 'GOAL']:
                plays.loc[i, team + ' Shot Attempts'] = 1
            ###################### Blocked Shots
            # Record the blocked shot for the blocking team,
            # and the shot attempt for the shooting team
            if event == 'BLOCKED_SHOT':
                if team == Away:
                    # Record block for away team
                    plays.loc[i, newC[8]] = 1
                    # Record shot attempt for home team
                    plays.loc[i, newC[7]] = 1
                elif team == Home:
                    # Record block for home team
                    plays.loc[i, newC[9]] = 1
                    # Record shot attempt for away team
                    plays.loc[i, newC[6]] = 1
            ###################### Missed Shots
            if event == 'MISSED_SHOT':
                plays.loc[i, team + ' Missed Shots'] = 1
            ###################### Hits
            if event == 'HIT':
                plays.loc[i, team + ' Hits'] = 1

        # Calculate rolling sum by iterating over each row from last to first
        for i in range(plays.shape[0] - 1, -1, -1):
            plays.loc[i, newC] = plays.loc[:i, newC].sum(axis=0)

        # Calculate a Shot Differential
        plays['Shot Differential'] = abs(self.plays[newC[3]] - self.plays[newC[2]])

        self.plays = plays

    def prior_5(plays, Home, Away, col='Shots'):
        """
        .

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
        secns = [int(s) for s in range(0, 60, 5)] * 60
        mints = [math.floor(len(secns[:s]) / 12) for s in range(len(secns))]
        hours = [int(0) for m in mints]

        if 4 in plays.period.unique():

            OTsec = [int(s) for s in range(0, 60, 5)] * 5
            secns = secns + OTsec
            mints = mints + [math.floor(len(OTsec[:s]) / 12) for s in range(len(OTsec) + 1)]
            hours = hours + [int(1) for s in OTsec]

            prior_5 = [dt.time(h, m, s) for h, m, s in list(zip(hours, mints, secns))]
        else:
            prior_5 = [dt.time(h, m, s) for h, m, s in list(zip(hours, mints, secns))]
            prior_5.append(dt.time(1, 0, 0))

        prior_5 = plays[(plays.Time.isin(prior_5))][[f'{Home} {col}', f'{Away} {col}', 'Time']]

        prior_5[Home + f" {col} - Prior 1 min"] = 0
        prior_5[Home + f" {col} - Prior 5 min"] = 0
        prior_5[Away + f" {col} - Prior 1 min"] = 0
        prior_5[Away + f" {col} - Prior 5 min"] = 0

        # `prior_5_{col}` column order:
        #    Home {col}        (0)
        #    Away {col}        (1)
        #    Time              (2)
        #    Home Prior 1 min  (3)
        #    Home Prior 5 min  (4)
        #    Away Prior 1 min  (5)
        #    Away Prior 5 min  (6)

        # Loop through `plays` to populate prior_5_{col} shots columns
        # Start with a loop through the minutes
        for i in range(prior_5.shape[0]):
            # Still within first minute of play
            if i <= 12:
                # Count instances in first minute of gameplay for Home, then Away
                # In the first minute, prior shots are just the current total shots
                for m, n in zip([3, 4, 5, 6], [0, 0, 1, 1]):
                    # Prior 5 & Prior 1 min data will be the same w/in first minute of play
                    prior_5.iloc[i, m] = prior_5.iloc[i, n]

            # Still within first 5 minutes of play
            elif i <= 60:
                for m, n in zip([3, 5], [0, 1]):
                    # Calculate prior 1 min stats
                    prior_5.iloc[i, m]     = prior_5.iloc[i, n] - prior_5.iloc[i - 12, n]
                    # Calculate prior 5 min stats
                    prior_5.iloc[i, m + 1] = prior_5.iloc[i, n]
                
            # Outside of first 5 minutes of play. Can calculate stats as usual
            else:
                for m, n in zip([3, 5], [0, 1]):
                    # Calculate prior 1 min stats
                    prior_5.iloc[i, m]     = prior_5.iloc[i, n] - prior_5.iloc[i - 12, n]
                    # Calculate prior 5 min stats
                    prior_5.iloc[i, m + 1] = prior_5.iloc[i, n] - prior_5.iloc[i - 60, n]

        # Trim DF
        prior_5 = prior_5[[Away + f" {col}", Away + f" {col} - Prior 5 min",
                           Home + f" {col}", Home + f" {col} - Prior 5 min", "Time"]]

        return prior_5

    def Prior5Stats(self):
        """
        Create dataframe for shots over prior 5 minutes.

        Returns
        -------
        None.

        """
        # Collect attributes needed for Prior_5 function
        Away, Home, plays = self.AwayAbrv, self.HomeAbrv, self.plays

        # Collect the prior 5 minute data needed to calculate a teams momentum
        shots    = GameStats.prior_5(plays, Home, Away, 'Shots')
        hits     = GameStats.prior_5(plays, Home, Away, 'Hits')
        goals    = GameStats.prior_5(plays, Home, Away, 'Goals')
        attempts = GameStats.prior_5(plays, Home, Away, 'Shot Attempts')

        # Return the prior 5 minute df's for the selected stats to their own attributes
        self.prior_5_shots = shots
        self.prior_5_hits  = hits
        self.prior_5_goals = goals
        self.prior_5_atmpt = attempts
        self.prior5        = pd.concat([shots, hits, goals, attempts], axis=1)

        # Merge the selected stats into one dataframe
        momentum = pd.concat([goals, shots, attempts, hits], axis = 1, levels = 'Time')
        momentum = momentum[[col for col in momentum.columns if ' - ' in col] + ['Time']]
        momentum = momentum.loc[~momentum.Time.duplicated(), ~momentum.columns.duplicated()]
        momentum.set_index('Time', inplace = True, drop = True)

        # Define function to calculate momentum over prior 5 minutes
        def TeamMomentum(P5_goals, P5_shots, P5_atts, P5_hits):
            w_goal   = 5
            w_shot   = 4
            w_hit    = 3
            w_attmpt = 1
            
            return (P5_goals * w_goal) + (P5_shots * w_shot) + \
                    (P5_hits * w_hit) + (P5_atts * w_attmpt)
        
        # Calculate momentum for each team
        HMcols = [col for col in momentum.columns if Home in col]
        AMcols = [col for col in momentum.columns if Away in col]
        
        momentum.loc[:, f'{Home} - Momentum'] = momentum.apply(lambda x: \
                                                               TeamMomentum(x[HMcols[0]],
                                                                            x[HMcols[1]],
                                                                            x[HMcols[2]],
                                                                            x[HMcols[3]],),
                                                               axis=1)
        momentum.loc[:, f'{Away} - Momentum'] = momentum.apply(lambda x: \
                                                               TeamMomentum(x[AMcols[0]],
                                                                            x[AMcols[1]],
                                                                            x[AMcols[2]],
                                                                            x[AMcols[3]]),
                                                               axis=1)
        # Calculate the Net Momentum (Home Team Mom. - Away Team Mom.)
        momentum.loc[:, 'Net_Momentum'] = momentum[f'{Home} - Momentum'] - \
            momentum[f'{Away} - Momentum']

        # Create seperate df's for the time periods where the home teams momentum is
        # dominant and when the away teams momentum is dominant. This is necessary for
        # the momentum plots to appropiately shade the area under the curves in plotly.
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

            # minors is currently unused. Instead of checking that a penalty is in this list,
            # we will assume that the penalty is an item in this list and use conditional
            # statemnts to check that assumption.
            minors = ['Boarding', 'Charging', 'Clipping', 'Elbowing', 'Hooking',
                      'Illegal check to the head', 'Kneeing', 'Roughing', 'Throwing equipment',
                      'Holding', 'Hooking', 'Interference', 'Tripping', 'Cross checking',
                      'Hi-sticking', 'Slashing', 'Delaying Game - Puck over glass',
                      'Delay of game', 'Delaying the game', 'Embellishment',
                      'Closing hand on puck', 'Interference - Goalkeeper',
                      'Too many men on the ice', 'Unsportsmanlike conduct']
            double = ['Hi stick - double minor', 'Cross check - double minor', 'Spearing']

            pim = 4 if PenType in double else 2

            majors = ['Fighting', 'Kicking', 'Slew-footing', 'Butt-ending']
            pim = 5 if PenType in majors else pim

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
            
            # Create minute and second references
            tempTime = plays.Time.iloc[i]
            # Create temporary end time (assumes all penalties are 2 minutes.
            # Will need to create a comprehension for majors & double minors)
            if tempTime.minute + pim > 59:
                tempH, tempM = 1, (tempTime.minute + pim) - 60
            else:
                tempH, tempM = 0, tempTime.minute + pim
            start, end = tempTime, dt.time(tempH, tempM, tempTime.second)

            x = i + 1  # temp row reference
            # Initiate while loop to handle MOI, PPG, SHG
            while (plays.Time.iloc[x] <= end):
                # Record one man down for PK in each row of plays df
                plays.loc[x, shTeam + " Men On Ice"] -= 1

                # Short handed goal scored
                if (plays.event_type.iloc[x] == 'GOAL') & \
                   (plays.team_for.iloc[x] == shTeam) & \
                   (plays.loc[x, shTeam + ' is_shg'] is False):

                    # Penalized team scores, record SHG
                    plays.loc[x:, shTeam + " SHG"]    += 1
                    plays.loc[x:, shTeam + ' is_shg']  = True

                # PP team scores. Record PPG & end penalty comprehension
                elif (plays.event_type.iloc[x] == 'GOAL') & \
                     (plays.team_for.iloc[x] == ppTeam) & \
                     (plays.loc[x, ppTeam + ' is_ppg'] is False):

                    # Team on PP scores, record PPG, end comprehension
                    end = dt.time(plays.Time.iloc[x].hour,
                                  int(plays.Minute.iloc[x]),
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

            # append penalty data for relevant team
            # Adjust start and end time to round seconds to nearest 5 second interval
            start = dt.time(start.hour, start.minute, min(5 * round(start.second / 5), 55))
            end   = dt.time(end.hour, end.minute, min(5 * round(end.second / 5), 55))
            pen_Home.append((start, end)) if team == Home else pen_Away.append((start, end))

            # return updated plays df and penalty lists
            return plays, pen_Home, pen_Away

        # Create shorter, temporary, references
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

        # Loop through each record of plays df to aggregate PP/PK data
        for i in range(0, plays.shape[0]):
            if (plays.event_type.iloc[i] == 'PENALTY') & \
               (plays.event_secondary_type.iloc[i] != 'Fighting'):
                plays, pen_Home, pen_Away = PenaltyComp(plays.team_for.iloc[i], i,
                                                        Home, Away, plays, pen_Home, pen_Away)

        # Convert list of tuples into nested list with start/end times of penalties.
        HomePens, AwayPens = [[i[0], i[1]] for i in pen_Home], [[x[0], x[1]] for x in pen_Away]

        # Update plays df and add penalty list attributes
        self.plays, self.HomePens, self.AwayPens = plays, HomePens, AwayPens

    def GoalsDF(self):
        """
        Create dataframe of goals data.

        Returns
        -------
        df : TYPE
            DESCRIPTION.
        max_Goal : TYPE
            DESCRIPTION.

        """
        plays, Home, Away = self.plays, self.HomeAbrv, self.AwayAbrv

        def CreateGoalsDF(plays, team):
            """
            Create a time series of just goals with minute
            and secod references. Used in top plot for
            vertical goal bars

            Parameters
            ----------
            plays : TYPE
                DESCRIPTION.
            team : TYPE
                DESCRIPTION.
            """
            # Create a copy of the plays df to modify
            df = plays.copy()

            # Set the index and seperate out goals as they were scored
            df.set_index("Time", inplace=True, drop=True)

            # Duplicates following the first instance of a goal marker will be dropped
            if 'player_4' not in df.columns:
                df.loc[:, 'player_4'] = ''
            cols = [team + " Goals", 'period'] + \
                   [col for col in ['player_1', 'player_2',
                                    'player_3', 'player_4'] if col in df.columns]
                    
            # Set up error handling in the event a team scored no goals
            if df[(df.event_type == 'GOAL') & (df.team_for == team)].empty is True:
                return pd.DataFrame(columns=cols), 0

            df = df[(df.event_type == 'GOAL') & (df.team_for == team)][cols]
            df.reset_index(inplace=True, drop=False)

            # Convert time objects to strings
            for i in range(0, df.shape[0]):
                df.loc[i, 'strTime'] = str(df.loc[i, 'Time'])

            # Seperate out the Hour, Minute, and Second that each goal is scored
            df['Hour'] = pd.to_numeric(df.strTime.str.slice(start=0, stop=2), downcast='integer')
            df['Minute'] = pd.to_numeric(df.strTime.str.slice(start=3, stop=5), downcast='integer')
            df['Seconds'] = pd.to_numeric(df.strTime.str.slice(start=6, stop=8), downcast='integer')

            # Reset the index and determine total goals scored by the team
            df.set_index('strTime', inplace=True)
            max_Goal = df[team + " Goals"].max()

            return df, max_Goal

        # Home & Away Team Goals / total goals scored
        home_goals, max_hGoal = CreateGoalsDF(plays, Home)
        away_goals, max_aGoal = CreateGoalsDF(plays, Away)

        max_Goal = max([max_aGoal, max_hGoal])
        self.Goals = [home_goals, away_goals, max_hGoal, max_aGoal, max_Goal]

    def SumDF(self):
        """
        Create summary stats dataframe.

        Returns
        -------
        TYPE
            DESCRIPTION.

        """
        plays = self.plays
        Home, Away = self.HomeAbrv, self.AwayAbrv

        # Determine if game went to OT
        self.OT = True if 4 in plays.period.unique() else False

        if self.OT is False:
            periods = 4  # Add 1 to inlcude room for a summary column
        else:
            periods = int(plays.period.max()) + 1
            
        # Define sum stats we want to collect
        myStats = ["Goals", "Shots", "Shot %", "Shot Attempts", "S/SA %",
                   "Blocked Shots", "Missed Shots", "Hits",
                   "Power Plays", "PPG", "SHG", "PIM"]
        dic = {}

        # Initiate loop through the `plays` df to collect summary stats by period
        for p in range(1, periods, 1):
            tempHlst = []  # Reset temp lists for each loop of `p`
            tempAlst = []

            for i in myStats:

                if i == "Shot %":
                    tempH = "{:.0%}".format(tempHlst[0] / tempHlst[1])
                    tempA = "{:.0%}".format(tempAlst[0] / tempAlst[1])

                    tempHlst.append(tempH)
                    tempAlst.append(tempA)
                    continue

                if i == "S/SA %":
                    tempH = "{:.0%}".format(tempHlst[1] / tempHlst[-1])
                    tempA = "{:.0%}".format(tempAlst[1] / tempAlst[-1])

                    tempHlst.append(tempH)
                    tempAlst.append(tempA)
                    continue

                tempH = plays[(plays.event_type == 'PERIOD_END') & \
                              (plays.period == p)][f"{Home} {i}"].min()
                tempA = plays[(plays.event_type == 'PERIOD_END') & \
                              (plays.period == p)][f"{Away} {i}"].min()

                tempHlst.append(tempH)
                tempAlst.append(tempA)
            
            p = p if p < 4 else 'OT'
            dic.update({(p, Home): tempHlst})
            dic.update({(p, Away): tempAlst})

        # Create DF of selected summary stats (sum stats are presented as rolling totals here)
        SumStats = pd.DataFrame.from_dict(dic, orient='columns')

        # Transpose and rename columns for a better looking layout
        SumStats = SumStats.transpose(copy=True)
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
        FS.index = pd.MultiIndex.from_tuples([('Game Total', Home), ('Game Total', Away)],
                                             names=['Period', 'Team'])

        # Define list of column names used to calculate sum stats by period
        SCols = ["Goals", "Shots", "Shot Attempts", "Blocked Shots", "Missed Shots",
                 "Hits", "Power Plays", "PPG", "SHG", "PIM"]

        # Seperate out home & away team sum stats for 2nd & 3rd periods
        for team in [Home, Away]:
            # Seperate out 2nd period stats
            SumStats.loc[idx[2, team], SCols] = SumStats.loc[idx[2, team], SCols] - \
                                                SumStats.loc[idx[1, team], SCols]
            # Seperate out 3rd period stats
            SumStats.loc[idx[3, team], SCols] = SumStats.loc[idx[3, team], SCols] - \
                                                SumStats.loc[idx[2, team], SCols] - \
                                                SumStats.loc[idx[1, team], SCols]

            if self.OT is True:
                SumStats.loc[idx['OT', team], SCols] = SumStats.loc[idx['OT', team], SCols] - \
                    SumStats.loc[idx[3, team], SCols] - \
                    SumStats.loc[idx[2, team], SCols] - \
                    SumStats.loc[idx[1, team], SCols]

        SS = pd.concat([FS, SumStats])

        SS['Shot %'] = (SS["Goals"] / SS['Shots'].replace(0, 1)) * 100
        SS['Shot %'] = pd.Series(["{0:.0f}%".format(val) for val in SS['Shot %']], index = SS.index)

        SS['S/SA %'] = (SS['Shots'] / SS['Shot Attempts'].replace(0, 1)) * 100
        SS['S/SA %'] = pd.Series(["{0:.0f}%".format(val) for val in SS['S/SA %']], index = SS.index)

        SS = SS.transpose(copy=False)

        self.SumStats = SS  # Standard pandas data frame of summary stats

    def All(gameid):
        
        gp = GameStats(gameid)
        
        GameStats.ModifyDFs(gp)
        GameStats.AggregateData(gp)
        GameStats.Prior5Stats(gp)
        GameStats.MenOnIce(gp)
        GameStats.GoalsDF(gp)
        GameStats.SumDF(gp)
        
        return gp

class GameMap():
    def __init__(self, game_id):

        pd.set_option('mode.chained_assignment', None)

        self.game_id = game_id

        self.plays = pd.DataFrame(list_plays(game_id))
        self.shots = pd.DataFrame(list_shots(game_id))
        self.shift = pd.DataFrame(list_shifts(game_id))

        # Add columns to shots and plays DF's for time elapsed.
        # Relevant for adding line markers for goals in plots.
        self.shots['Time']   = pd.to_datetime(self.shots.period_time, format="%M:%S")
        self.shots['Minute'] = self.shots['Time'].dt.minute
        self.shots['Second'] = self.shots['Time'].dt.second

        self.plays['Time']   = pd.to_datetime(self.plays.period_time, format="%M:%S")
        self.plays['Minute'] = self.plays['Time'].dt.minute
        self.plays['Second'] = self.plays['Time'].dt.second

        # Change Time column from the time of the period to the game time elapsed
        for i in range(2, self.plays.period.unique().max() + 1):
            self.shots.loc[self.shots.period == i, 'Time'] = \
                self.shots[self.shots.period == i]. Time + dt.timedelta(minutes=20 * (i - 1))

            self.plays.loc[self.plays.period == i, 'Time'] = \
                self.plays[self.plays.period == i].Time + dt.timedelta(minutes=20 * (i - 1))

            self.shots.loc[self.shots.period == i, 'Minute'] = \
                self.shots[self.shots.period == i].Minute + (20 * (i - 1))

            self.plays.loc[self.plays.period == i, 'Minute'] = \
                self.plays[self.plays.period == i].Minute + (20 * (i - 1))

        self.gameDay = pd.to_datetime(self.plays['datetime']).iloc[0].date()
        self.Teams = pd.DataFrame(list_games(str(self.gameDay + dt.timedelta(days=-1)),
                                             str(self.gameDay)))
        self.Teams = self.Teams[self.Teams.game_id == game_id]

        self.Home = self.Teams.home_team.iloc[0]
        self.Away = self.Teams.away_team.iloc[0]

        # Define team name references
        tL = pd.read_csv('teamList.csv')  # store as csv file in GH?

        self.HomeAbrv = tL[tL.team_name == self.Home].team_abbrv.max()
        self.AwayAbrv = tL[tL.team_name == self.Away].team_abbrv.max()

        self.Home_Color1 = tL[tL.team_abbrv == self.HomeAbrv].home_c.max()
        self.Home_Color2 = tL[tL.team_abbrv == self.HomeAbrv].away_c.max()

        self.Away_Color1 = tL[tL.team_abbrv == self.AwayAbrv].away_c.max()
        self.Away_Color2 = tL[tL.team_abbrv == self.AwayAbrv].home_c.max()

    def XY_SnG(self):
        """
        Collect Goals, Shots, & Shot Attempts data.

        Returns
        -------
        str
            DESCRIPTION.

        """
        shots = self.shots
        Home = self.HomeAbrv
        Away = self.AwayAbrv

        def IndexToMarker(index):
            return f"${index}$"

        # Refine `shots` DF columns
        cols = ['event_type', 'team_for', 'x', 'y', 'period',
                'player_1', 'player_2', 'player_3', 'player_4', 'period_time']
        cols = [col for col in cols if col in shots.columns]
        XY = shots[cols]

        # Odd logic problem where adjustments for direction of attack is not
        # consistent across all home teams. Need to test with more games to
        # determine a formula to automate process of making x,y adjustments.
        # Will probably just include an extra column in the teamsList.csv file...

        # Standardize direction of play/attack for each team
        XY.loc[(XY.team_for == Home), 'x'] = -1 * abs(XY['x'])
        XY.loc[(XY.team_for == Away), 'x'] = abs(XY['x'])

        #XY.loc[(XY.team_for == Away) & ((XY.period == 1) | (XY.period == 3)), 'y'] = -1 * XY['y']
        XY.loc[((XY.period == 2)), 'y'] = -1 * XY['y']

        # Seperate out each team's shots and goals
        XYhome = XY[(XY.team_for == Home)]
        XYhomeS = XYhome[XYhome.event_type == 'SHOT']
        XYhomeSA = XY[((XY.team_for == Home) & (XY.event_type == 'MISSED_SHOT')) | \
                      ((XY.team_for == Away) & (XY.event_type == 'BLOCKED_SHOT'))]
        XYhomeSA.loc[:, 'x'] = -1 * abs(XYhomeSA['x'])
        XYhomeG = XYhome[XYhome.event_type == 'GOAL']

        XYaway = XY[(XY.team_for == Away)]
        XYawayS = XYaway[XYaway.event_type == 'SHOT']
        XYawaySA = XY[((XY.team_for == Away) & (XY.event_type == 'MISSED_SHOT')) | \
                      ((XY.team_for == Home) & (XY.event_type == 'BLOCKED_SHOT'))]
        XYawaySA.loc[:, 'x'] = abs(XYawaySA['x'])
        XYawayG = XYaway[XYaway.event_type == 'GOAL']
        XYhomeSA.loc[:, 'x'] = -1 * abs(XYhomeSA['x'])

        # Reset index of goals df's to match goal # within this game
        XYhomeS.index = np.arange(1, len(XYhomeS) + 1)
        XYhomeSA.index = np.arange(1, len(XYhomeSA) + 1)
        XYhomeG.index = np.arange(1, len(XYhomeG) + 1)

        XYhomeS['MarkerStyle'] = 'circle'
        XYhomeSA['MarkerStyle'] = 'x'
        XYhomeG['MarkerStyle'] = XYhomeG.index.copy(dtype='str')

        XYawayS.index = np.arange(1, len(XYawayS) + 1)
        XYawaySA.index = np.arange(1, len(XYawaySA) + 1)
        XYawayG.index = np.arange(1, len(XYawayG) + 1)

        XYawayS['MarkerStyle'] = 'circle'
        XYawaySA['MarkerStyle'] = 'x'
        XYawayG['MarkerStyle'] = XYawayG.index.copy(dtype='str')

        self.HomeG, self.HomeS, self.HomeSA = XYhomeG, XYhomeS, XYhomeSA
        self.AwayG, self.AwayS, self.AwaySA = XYawayG, XYawayS, XYawaySA

    def XY_Plays(self):
        """
        Collect Hits, Takeaways, and giveaways

        Returns
        -------
        None.

        """
        plays = self.plays
        Home = self.HomeAbrv
        Away = self.AwayAbrv

        cols = ['event_type', 'team_for', 'x', 'y', 'period',
                'player_1', 'player_2', 'player_3', 'player_4', 'period_time']
        cols = [col for col in cols if col in plays.columns]

        hits = plays[plays.event_type == 'HIT'][cols]
        take = plays[plays.event_type == 'TAKEAWAY'][cols]
        give = plays[plays.event_type == 'GIVEAWAY'][cols]
        face = plays[plays.event_type == 'FACEOFF'][cols]

        XYhomeH = hits[hits.team_for == Home]   # x,y data for home team hits
        XYawayH = hits[hits.team_for == Away]   # x,y data for away team hits

        XYhomeT = take[take.team_for == Home]   # x,y data for home team takeaways
        XYawayT = take[take.team_for == Away]   # x,y data for away team takeaways

        XYhomeGA = give[give.team_for == Home]  # x,y data for home team giveaways
        XYawayGA = give[give.team_for == Away]  # x,y data for away team giveaways

        # Possibly useful for looking at draws likely to win/lose
        XYhomeF = face[face.team_for == Home]   # Faceoff win xy data
        XYawayF = face[face.team_for == Away]   # Faceoff win xy data -

        XYhomeH.index = np.arange(1, len(XYhomeH) + 1)
        XYhomeT.index = np.arange(1, len(XYhomeT) + 1)
        XYhomeGA.index = np.arange(1, len(XYhomeGA) + 1)

        XYawayH.index = np.arange(1, len(XYawayH) + 1)
        XYawayT.index = np.arange(1, len(XYawayT) + 1)
        XYawayGA.index = np.arange(1, len(XYawayGA) + 1)

        self.HomeH = XYhomeH
        self.HomeT = XYhomeT
        self.HomeGA = XYhomeGA
        self.HomeFO = XYhomeF

        self.AwayH = XYawayH
        self.AwayT = XYawayT
        self.AwayGA = XYawayGA
        self.AwayFO = XYawayF

class PlotGameStats:
    def __init__(self, gameid, HomeColor=False, AwayColor=False, gameDay=None):
        # Use GameStats to collect time series data
        #gp = GameStats(gameid)

        # GameStats.ModifyDFs(gp)
        # GameStats.AggregateData(gp)
        # GameStats.Prior5Stats(gp)
        # GameStats.MenOnIce(gp)
        # GameStats.GoalsDF(gp)
        # GameStats.SumDF(gp)
        gp = GameStats.All(gameid)

        # Collect Home/Away abbreviations and color codes
        self.Home = gp.HomeAbrv
        self.HCol = [gp.Home_Color1, gp.Home_Color2][min(1, max(0, HomeColor))]
        self.Away = gp.AwayAbrv
        self.ACol = [gp.Away_Color1, gp.Away_Color2][min(1, max(0, AwayColor))]

        self.plays = gp.plays
        self.Goals = gp.Goals

        self.prior_5_shots, self.prior_5_hits = gp.prior_5_shots, gp.prior_5_hits
        self.prior_5_goals, self.prior_5_atmpt = gp.prior_5_goals, gp.prior_5_atmpt
        self.HomeMomentum, self.AwayMomentum = gp.HomeMomentum, gp.AwayMomentum
        self.HomePens, self.AwayPens = gp.HomePens, gp.AwayPens

        self.gameDay = gameDay if gameDay is not None else gp.gameDay

        # Use GameMap to collect x/y data
        gm = GameMap(gameid)

        GameMap.XY_SnG(gm)
        GameMap.XY_Plays(gm)

        self.shots = gm.shots

        self.HomeS  = gm.HomeS
        self.AwayS  = gm.AwayS
        self.HomeSA = gm.HomeSA
        self.AwaySA = gm.AwaySA
        self.HomeG  = gm.HomeG
        self.AwayG  = gm.AwayG

        self.HomeH  = gm.HomeH
        self.AwayH  = gm.AwayH
        self.HomeT  = gm.HomeT
        self.AwayT  = gm.AwayT
        self.HomeGA = gm.HomeGA
        self.AwayGA = gm.AwayGA

        self.SumStats = gp.SumStats

    def go(self, template='plotly_white'):
        """
        Return the Plotly figure visuals.

        Returns
        -------
        None.

        """
        # Define function used to add vertical bars every 20 minutes
        # ------------------------------------
        def PeriodLines(fig, df, Home, Away, row, col, stat, secondary_y=False):
            
            if stat == 'Net_Momentum':
                height = max(df[0][stat].max(), df[1][stat].max()) + 5
                base   = min(df[0][stat].min(), df[1][stat].min()) - 5
            else:
                height = max(df[0].shape[0], df[1].shape[0]) + 1 if stat == 'Goals' else \
                    max(df[f'{Home} {stat}'].max(), df[f'{Away} {stat}'].max()) + 1
                base = 0
                
            for i in ["00:20:00", "00:40:00", "01:00:00"]:
                bar = go.Scatter(x          = [i, i],
                                 y          = [base, height],
                                 mode       = 'lines',
                                 showlegend = False,
                                 hoverinfo  = 'skip',
                                 name       = "",
                                 line       = dict(color = self.txtColor,
                                                   dash  = 'dot',
                                                   width = 3))
                fig.add_trace(bar, secondary_y=secondary_y, row = row, col = col)

            return fig
        # ------------------------------------

        # Define function to shade subplots 2 & 3 to mark power plays
        # ------------------------------------
        def ShadePenalties(fig, Pens, Colors, height, row, col):

            for pen, color in zip(Pens, Colors):
                for r in pen:
                    bar = go.Scatter(x = [str(r[0]), str(r[1]), str(r[1]),
                                          str(r[0]), str(r[0])],
                                     y          = [0, 0, height, height, 0],
                                     mode       = 'lines',
                                     showlegend = False,
                                     hoverinfo  = 'skip',
                                     name       = '',
                                     line       = dict(color = color),
                                     fill       = 'toself',
                                     fillcolor  = color,
                                     opacity    = 0.25)
                    fig.add_trace(bar, secondary_y=False, row=row, col=col)

            return fig
        # ------------------------------------

        # Define function to format the Ice Map scatter plots
        # ------------------------------------
        def FormatMap(fig, Home, HCol, Away, ACol, row, col):

            # LEFT & RIGHT y-axis
            for LoR, HoA in zip([False, True], [Home, Away]):
                fig.update_yaxes(title_text     = f"{HoA} Attacks",
                                 showgrid       = False,
                                 range          = (-42.5, 42.5),
                                 secondary_y    = LoR,
                                 zeroline       = False,
                                 row            = row,
                                 col            = col,
                                 title          = dict(standoff=0),
                                 showticklabels = False)
            # X-axis
            fig.update_xaxes(title_text = "",
                             showgrid   = False,
                             range      = (-100, 100),
                             zeroline   = False,
                             row        = row,
                             col        = col,
                             showticklabels = False)

            # Add goal lines, blue lines, and center ice line
            for x, y, color in zip([-89, -25, 0, 25, 89], [41, 42.5, 42.5, 42.5, 41],
                                   ['red', '#0000ff', 'red', 'blue', 'red']):
                fig.add_shape(type      = "line",
                              xref      = "x",
                              yref      = "y",
                              x0        = x,
                              x1        = x,
                              y0        = -y,
                              y1        = y,
                              line      = dict(color=color, width=3),
                              fillcolor = color,
                              row       = row,
                              col       = col,
                              opacity   = 0.35)
            # Add F-O circles
            for x, y in zip([-69, -69, 0, 69, 69], [22, -22, 0, 22, -22]):
                fig.add_shape(type = "circle",
                              xref = "x",
                              yref = "y",
                              x0   = x - 9, y0 = y - 7.5,
                              x1   = x + 9, y1 = y + 7.5,
                              line_color       = "red",
                              row  = row, col  = col,
                              opacity          = 0.35)

            # Add shaded areas for each teams attacking zone
            xs = [i / 100 for i in range(7375, 10010, 5)]
            xs = pd.Series(xs)

            ys = [((x - 73.75)**5 / (26.25**4)) - 42.5 for x in xs]
            ys = pd.Series(ys)

            for x, y, color in zip([xs, xs, -xs, -xs],
                                   [ys, -ys, ys, -ys],
                                   [ACol, ACol, HCol, HCol]):

                Shade = go.Scatter(x          = x,
                                   y          = y,
                                   line       = dict(color=color,
                                                     width=6),
                                   mode       = 'lines',
                                   fill       = "none",
                                   fillcolor  = color,
                                   hoverinfo  = 'skip',
                                   showlegend = False,
                                   opacity    = .9)
                fig.add_trace(Shade,
                              secondary_y = False,
                              row = row, col = col)

            # Add perimeter borders
            for x0, x1, y0, y1, color in zip([-100,  -100,  -100,   100,     0,    0],
                                             [   0,     0,  -100,   100,   100,  100],
                                             [-42.5, 42.5, -42.5, -42.5, -42.5, 42.5],
                                             [-42.5, 42.5,  42.5,  42.5, -42.5, 42.5],
                                             [ HCol, HCol,  HCol,  ACol,  ACol, ACol]):

                fig.add_shape(type = "line",
                              xref = "x",
                              yref = "y",
                              x0=x0, x1=x1,
                              y0=y0, y1=y1,
                              line = dict(color=color, width=6,),
                              fillcolor = color, row = row, col = col, opacity = 0.9)

            # Add LHS/RHS House
            LHouse = go.Scatter(x          = [-89, -69, -54, -54, -69, -89, -89],
                                y          = [-4, -22, -22, 22, 22, 4, -4],
                                mode       = 'lines',
                                name       = '',
                                fill       = 'none',
                                hoverinfo  = 'skip',
                                showlegend = False,
                                line       = dict(color=self.txtColor,
                                                  dash='dot',
                                                  width=1))
            fig.add_trace(LHouse, secondary_y=False, row=row, col=col)

            RHouse = go.Scatter(x          = [89, 69, 54, 54, 69, 89, 89],
                                y          = [-4, -22, -22, 22, 22, 4, -4],
                                mode       = 'lines',
                                name       = '',
                                fill       = 'none',
                                hoverinfo  = 'skip',
                                showlegend = False,
                                line       = dict(color=self.txtColor,
                                                  dash='dot',
                                                  width=1))
            fig.add_trace(RHouse, secondary_y=False, row=row, col=col)

            # Add LHS/RHS Goal Creases
            for x, y in zip([[-89, -85], [89, 85]],
                            [[-4, 4], [-4, 4]]):
                fig.add_shape(type="rect",
                              x0=x[0], x1=x[1],
                              y0=y[0], y1=y[1],
                              row=row, col=col,
                              fillcolor='blue', opacity=0.5)

            return fig
        # ------------------------------------

        # Define function to create Sunburst plots for the desired stat
        def StatSunburst(self, fig, row, col, stat, Home, HCol, Away, ACol):
            def strPeriod(p):
                if p == 1:
                    return "1st"
                elif p == 2:
                    return "2nd"
                elif p == 3:
                    return "3rd"
                else:
                    return "OT"

            def strPlayer(p):
                return p.replace(' ', '<br>')
            # Copy the plays dataframe to manipulate and trim it
            plays = self.plays.copy()

            if stat.upper() == 'SHOT ATTEMPT':
                ## Special procedure if SHOT ATTEMPT is entered for the stat parameter
                # Refine the plays df to the columns (cols) and rows (.isin()) needed
                cols  = ['team_for', 'period', 'player_1', 'event_type']
                shots = plays.loc[plays.event_type.isin(['BLOCKED_SHOT',
                                                         'MISSED_SHOT',
                                                         'SHOT',
                                                         'GOAL']),
                                  cols + ['player_2']]

                # NHL API records blocked shots as the team that blocked the shot.
                # For this plot, we want to record it as a blocked shot attempt
                # for the team that shot the puck. Collect the same columns as in `shots`
                # but clean the data from the NHL API.
                #atts  = plays.loc[plays.event_type == 'BLOCKED_SHOT', cols]
                shots.loc[shots.event_type == 'BLOCKED_SHOT', 'team_for'] = \
                   shots.loc[shots.event_type == 'BLOCKED_SHOT', 'team_for'].apply(lambda x: \
                                                                    Home if x == Away else Away)
                shots.loc[shots.event_type == 'BLOCKED_SHOT', 'player_1'] = \
                    shots.loc[shots.event_type == 'BLOCKED_SHOT', 'player_2']

                shots.event_type = shots.event_type.apply(lambda x: x.replace('_', '<br>') + "S")

                # Return the shot attempt stats data to be used in the sunburst
                stats = shots[cols]

                # Define variables need to group data and for the sunburst path
                newCols = ['Team', 'Period', 'Player', "Type", stat + "S"]
                path1   = ['Team', 'Player', "Type", 'Period']
                path2   = ['Team', "Type", 'Period', 'Player']
                val     = stat + "S"

            elif stat.upper() == 'HTG':
                cols = ['team_for', 'period', 'player_1', 'event_type']
                HTG  = plays.loc[plays.event_type.isin(['HIT', 'TAKEAWAY', 'GIVEAWAY']), cols]

                stats = HTG

                newCols = ['Team', 'Period', 'Player', "Type", stat + "S"]
                path1   = ['Team', 'Player', "Type", 'Period']
                path2   = ['Team', "Type", 'Period', 'Player']
                val     = stat + "S"

            else:
                # For all other stats, only a simple transformation is needed
                cols  = ['team_for', 'period', 'player_1']
                stats = plays.loc[plays.event_type == stat.upper(), cols]

                # Define variables need to group data and for the sunburst path
                newCols = ['Team', 'Period', 'Player', stat + "S"]
                path1   = ['Team', 'Player', 'Period']
                path2   = ['Team', 'Period', 'Player']
                val     = stat + "S"

            stat += "S"

            # Group the stats data by period and then by player
            if stats.shape[0] > 0:
                group = cols
                stats = stats.groupby(group).size().reset_index()
                stats.columns = newCols
    
                # Format the Period and Player column values
                stats.Period = stats.Period.astype('int')
                stats.Period = stats.Period.apply(lambda x: strPeriod(x))
                stats.Player = stats.Player.apply(lambda x: strPlayer(x))
    
                for path, col_, depth in zip([path1, path2], [0, 1], [3, 3]):
                    ## Create the left-hand side sunburst plot - 'Team', 'Player', 'Period'
                    sun = px.sunburst(stats,
                                      path       = path,
                                      values     = val,
                                      hover_data = path,
                                      color      = 'Team',
                                      color_discrete_map = {Home: HCol, Away: ACol, '(?)': 'lightgrey'})
    
                    # Define the hovertemplate to be used in the sunburst  plot
                    if stat.upper() == 'SHOT ATTEMPT':
                        # Special template for         shot attempts
                        hTemplate = '<b>Team: %{customdata[0]}</b><br>' + \
                                    f'{path[1]}: ' + '%{customdata[1]}<br>' + \
                                    f'{path[2]}: ' + '%{customdata[2]}<br>' + \
                                    f'{path[3]}: ' + '%{customdata[3]}<br>' + \
                                    f'{stat}' + ': %{value:,.0f}'
    
                    else:
                        # Regular template for all other stats
                        hTemplate = '<b>Team: %{customdata[0]}</b><br>' + \
                                    f'{path[1]}: ' + '%{customdata[1]}<br>' + \
                                    f'{path[2]}: ' + '%{customdata[2]}<br>' + \
                                    f'{stat}' + ': %{value:,.0f}'
    
                    # , mode='hide' (include in dict() to hide scrunched up text labels)
                    sun.update_layout(uniformtext=dict(minsize=10))
                    sun.update_traces(hovertemplate = hTemplate)
    
                    # "Steal" the necessary attributes from the px sunburst
                    # to use in the go sunburst.
                    parents       = sun['data'][0]['parents']
                    labels        = sun['data'][0]['labels']
                    ids           = sun['data'][0]['ids']
                    values        = sun['data'][0]['values']
                    customdata    = sun['data'][0]['customdata']
                    hovertemplate = sun['data'][0]['hovertemplate']
                    marker        = sun['data'][0]['marker']
    
                    # Add the sunburst chart for by player data
                    fig.add_trace(go.Sunburst(labels        = labels,
                                              parents       = parents,
                                              ids           = ids,
                                              name          = '',
                                              values        = values,
                                              marker        = marker,
                                              customdata    = customdata,
                                              hovertemplate = hovertemplate,
                                              branchvalues  = 'total',
                                              textfont      = dict(size=14),
                                              maxdepth      = depth,
                                              ),
                                  row = row,
                                  col = col + col_)
                    fig.update_yaxes(row = row, col = col + col_, automargin = True)
                
            return fig
        # ------------------------------------

        # Collect necessary references
        # ------------------------------------
        Home, HCol = self.Home, self.HCol  # Home abbreviation, color
        Away, ACol = self.Away, self.ACol  # Away abbreviation, color

        plays, Goals = self.plays, self.Goals  # Plays dataframe, Shots dataframe

        # Prior 5 minutes of shots, Prior 5 minutes of hits
        prior_5_shots, prior_5_hits = self.prior_5_shots, self.prior_5_hits
        
        # Home team penalties, Away team penalties
        HomePens, AwayPens = self.HomePens, self.AwayPens
        # Home team shots, shot attempts, goals
        HomeS, HomeSA, HomeG  = self.HomeS, self.HomeSA, self.HomeG
        # Away team shots, shot attempts, goals
        AwayS, AwaySA, AwayG  = self.AwayS, self.AwaySA, self.AwayG
        # Home team hits, takeaways, giveaways
        HomeH, HomeT, HomeGA  = self.HomeH, self.HomeT, self.HomeGA
        # Away team hits, takeaways, giveaways
        AwayH, AwayT, AwayGA = self.AwayH, self.AwayT, self.AwayGA

        SumStats = self.SumStats  # Summary game stats
        gameDay  = self.gameDay  # Date of game in string format
        
        HMom = self.HomeMomentum
        AMom = self.AwayMomentum

        self.txtColor = 'white' if template == 'plotly_dark' else 'black'
        # ------------------------------------

        # Create the frame for an SIX row, THREE column plot
        # ------------------------------------
        GPdict  = {"secondary_y": True, 'colspan': 1, 'rowspan': 2}   # GameStats specs
        MMdict  = {"secondary_y": False, 'colspan': 1, 'rowspan': 1}  # Momentum & P5 plot specs
        MPdict  = {"secondary_y": True, 'colspan': 2, 'rowspan': 1}   # GameMap specs
        SBdict  = {"type": "sunburst", 'colspan': 1, 'rowspan': 1}    # Sunburst plot specs
        TBdict  = {"type": "table", 'colspan': 1, 'rowspan': 1}       # Table specs
        
        fig = make_subplots(rows  = 6,
                            cols  = 3,
                            specs = [[GPdict, MPdict, None],
                                     [None, SBdict, SBdict],
                                     [MMdict, MPdict, None],
                                     [MMdict, SBdict, SBdict],
                                     [MMdict, SBdict, SBdict],
                                     [TBdict, SBdict, SBdict]],
                            column_widths  = [2, 1, 1],
                            row_heights    = [1.5, 1.5, 1.5, 1.5, 1, 1],
                            subplot_titles = ("Goals, Shots, & Shot Attempts Time Series",
                                              "Goals, Shots, & Shot Attempts Map",
                                              "GSA | By PLAYER", "GSA | By PERIOD",
                                              "Net Momentum Plot",
                                              "Hits, Takeaways, & Giveaways Map",
                                              "Shots Over Prior 5 Minutes",
                                              "HTG | By PLAYER", "HTG | By PERIOD",
                                              "Hits Over Prior 5 Minutes",
                                              "Goals | By PLAYER", "Goals | By PERIOD",
                                              "Summary Stats",
                                              "Shots | By PLAYER", "Shots | By PERIOD",
                                              ),
                            vertical_spacing   = 0.06,
                            horizontal_spacing = 0.05)
        # ------------------------------------

        # Adjust figure formats
        # ------------------------------------
        # Adjust subplot title font sizes
        for i in fig['layout']['annotations']:
            i['font']['size'] = 24

        # Adjust figure fonts and font sizes,
        # add figure title, adjust size and bg color
        height = 2250
        width  = 1600
        
        fig.update_layout(font          = dict(family = "Arial",
                                               size   = 24,
                                               color  = self.txtColor),
                          title_text    = f"{Away} @ {Home} | {gameDay}",
                          autosize      = True,
                          #width         = width,
                          height        = height,  # width * 5.5,
                          margin        = dict(l=15, r=15,
                                               b=15, t=65,
                                               pad=0),
                          template      = template,
                          hovermode     = "x",
                          hoverlabel    = dict(namelength = -1),
                          legend        = dict(x=0, y=1,
                                               traceorder='normal',
                                               font=dict(size=12)))
        # Align subplot titles to the left side
        # for i, x in zip(range(6), [0.28, 0.1, 0.17, 0.17, 0.235]):
        #     fig.layout.annotations[i].update(x=x)
        # ------------------------------------
        
        # Add GameStats to figure (1:1, (2x1))
        # ------------------------------------------------------------------------
        # ------------------------------------
        myRow = 1
        myCol = 1
        
        zipped = zip([f'{Home} Shots', f'{Away} Shots',
                      f'{Home} Shot Attempts', f'{Away} Shot Attempts'],
                     ([HCol, ACol] * 2), ['solid', 'solid', 'dash', 'dash'])

        for trace, color, line in zipped:
            plot = go.Scatter(x    = plays.Time,
                              y    = plays[trace],
                              mode = 'lines',
                              name = trace,
                              line = dict(color=color,
                                          dash=line))

            fig.add_trace(plot, secondary_y=False, row=myRow, col=myCol)
        # ------------------------------------

        # On second y-axis of the top subplot,
        # add vertical bars denoting goals for each team
        # ------------------------------------
        for team, color, index in zip([Home, Away], [HCol, ACol], [0, 1]):
            # Add goal bars
            for i in range(Goals[index].shape[0]):
                # The nth goal provided in the Goals df
                goal_n  = Goals[index][f"{team} Goals"].iloc[i]
                # The time the nth goal was scored
                g_time = Goals[index].index[i]

                # Collect player references for the goal
                cols = ['player_1', 'player_2', 'player_3', 'player_4']
                # Drop player_3 and/or player_4 columns if no goal was scored
                # with an assist or secondary assit.
                cols = [c for c in cols if c in Goals[index].columns]
                if len(cols) == 2:
                    player1, player2 = Goals[index].loc[g_time, cols]
                    player3, player4 = None, None
                elif len(cols) == 3:
                    player1, player2, player3 = Goals[index].loc[g_time, cols]
                    player4 = None
                else:
                    player1, player2, player3, player4 = Goals[index].loc[g_time, cols]

                # If goal was un-assited, player2 is the goalie & should be swapped with player4
                #player2, player4 = player4, player2 if player3 == player4 else player2, player4
                if (player3 == player4) & (player4 in ['', None]):
                    player2, player4 = player4, player2
                # If goal only had one assit, player3 needs to be swapped with player 4
                #, player4 = player4, player3 if player4 is None else player3, player4
                elif (player4 in ['', None]) & (player3 not in ['', None]):
                    player3, player4 = player4, player3

                bar = go.Scatter(x          = [g_time, g_time],
                                 y          = [0, goal_n],
                                 hovertemplate = f'<b>Goal #: {goal_n}<b><br>' +
                                 f'Scored By: {player1}<br>' +
                                 f'Assit*: {player2}<br>' +
                                 f'Assit**: {player3}<br>' +
                                 f'Goalie: {player4}<br>'
                                 '<extra></extra>',
                                 mode       = 'lines',
                                 showlegend = False,
                                 name       = f"{team} Goal",
                                 line       = dict(color=color,
                                                   dash='solid',
                                                   width=5))
                fig.add_trace(bar, secondary_y=True, row=myRow, col=myCol)
        # ------------------------------------

        # Add period seperating lines to 1st subplot
        # ------------------------------------
        fig = PeriodLines(fig, Goals, Home, Away, myRow, myCol, 'Goals', secondary_y=True)
        # ------------------------------------

        # Update top subplot formats
        # ------------------------------------
        # Set x-axis title
        fig.update_xaxes(title_text = "Game Time Elapsed",
                         titlefont  = dict(size=18),
                         tickfont   = dict(size=18),
                         showgrid   = False,
                         row        = myRow,
                         col        = myCol,
                         #range      = ["00:00:00", "00:01:00"],
                         tickvals   = ["00:00:00"] +
                         [f"00:{m}:00" for m in range(10, 65, 10)] +
                         ["01:00:00"])

        # Set y-axes titles
        ## Left side
        fig.update_yaxes(title_text  = "Shots (Attempts)",
                         secondary_y = False,
                         zeroline    = False,
                         row         = myRow,
                         col         = myCol,
                         showgrid    = False)
        ## Right side
        height = Goals[4] + 1
        ntick = height if height < 10 else int(height / 2)

        fig.update_yaxes(title_text    = "Goals",
                         secondary_y   = True,
                         row           = myRow,
                         col           = myCol,
                         showgrid      = False,
                         zeroline      = False,
                         nticks        = ntick,
                         range         = (0, height))
        # ------------------------------------
        # ------------------------------------------------------------------------

        # Add Momentum plot to figure (3:1, 1x1)
        # ------------------------------------------------------------------------
        # ------------------------------------
        myRow = 3
        myCol = 1
        
        zipped = zip([HMom, AMom], [HCol, ACol], [Home, Away])
        
        for trace, color, team in zipped:
            plot = go.Scatter(x          = trace.index,
                              y          = trace.Net_Momentum,
                              name       = f'{team} Momentum',
                              fill       = 'tozeroy',
                              fillcolor  = color,
                              opacity    = 0.5,
                              line       = dict(color=color),
                              showlegend = False)
            fig.add_trace(plot, secondary_y = False, row = myRow, col = myCol)
        # ------------------------------------
        
        # Add period seperating lines to 2nd subplot
        # ------------------------------------
        fig = PeriodLines(fig, [HMom, AMom], Home, Away, myRow, myCol, 'Net_Momentum')
        # ------------------------------------

        # Format the 2nd subplot
        # ------------------------------------
        height = HMom.Net_Momentum.max() + 5
        ntick  = int(height / 3) if height < 30 else int(height / 5)
        base   = AMom.Net_Momentum.min() - 5

        fig.update_yaxes(title_text    = "Shots",
                         secondary_y   = False,
                         showgrid      = False,
                         row           = myRow,
                         col           = myCol,
                         titlefont     = dict(size=22),
                         nticks        = ntick,
                         range         = (base, height),
                         zeroline      = False)

        # Set x-axis title
        fig.update_xaxes(title_text = "Game Time Elapsed",
                         titlefont  = dict(size=18),
                         tickfont   = dict(size=18),
                         showgrid   = False,
                         row        = myRow,
                         col        = myCol,
                         #range      = ["00:00:00", "00:01:00"],
                         tickvals   = ["00:00:00"] +
                         [f"00:{m}:00" for m in range(10, 65, 10)] +
                         ["01:00:00"])

        # fig.update_xaxes(titlefont = dict(size=18),
        #                  tickfont  = dict(size=18),
        #                  showgrid  = False,
        #                  row       = myRow,
        #                  col       = myCol)
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Add Prior 5 Minute Shots plots to the figure (4:1, 1x1)
        # ------------------------------------------------------------------------
        # ------------------------------------
        myRow = 4
        myCol = 1
        
        zipped = zip([f'{Home} Shots - Prior 5 min',
                      f'{Away} Shots - Prior 5 min'],
                     ([HCol, ACol]),
                     ['dot', 'dot'])

        for trace, color, line in zipped:
            plot = go.Scatter(x          = prior_5_shots.Time,
                              y          = prior_5_shots[trace],
                              mode       = 'lines',
                              showlegend = False,
                              name       = trace,
                              line       = dict(color=color,
                                                dash=line))
            fig.add_trace(plot, secondary_y=False, row = myRow, col = myCol)
        # ------------------------------------

        # Add period seperating lines to 3rd subplot
        # ------------------------------------
        fig = PeriodLines(fig, prior_5_shots, Home, Away, myRow, myCol, 'Shots - Prior 5 min')
        # ------------------------------------

        # Shade areas for Home/Away team power plays
        # Note: Need to figure out a way to neatly
        #       make users aware of this via annotations
        # ------------------------------------
        Pens = [HomePens, AwayPens]
        height = max(prior_5_shots[f'{Home} Shots - Prior 5 min'].max(),
                     prior_5_shots[f'{Away} Shots - Prior 5 min'].max()) + 1

        fig = ShadePenalties(fig, Pens, [ACol, HCol], height, myRow, myCol)
        # ------------------------------------

        # Format the 3rd subplot
        # ------------------------------------
        ntick = height if height < 10 else int(height / 2)

        fig.update_yaxes(title_text    = "Shots",
                         secondary_y   = False,
                         showgrid      = False,
                         row           = myRow,
                         col           = myCol,
                         titlefont     = dict(size=22),
                         nticks        = ntick,
                         range         = (0, height),
                         zeroline      = False)

        # Set x-axis title
        fig.update_xaxes(title_text = "Game Time Elapsed",
                         titlefont  = dict(size=18),
                         tickfont   = dict(size=18),
                         showgrid   = False,
                         row        = myRow,
                         col        = myCol,
                         #range      = ["00:00:00", "00:01:00"],
                         tickvals   = ["00:00:00"] +
                         [f"00:{m}:00" for m in range(10, 65, 10)] +
                         ["01:00:00"])
        # ------------------------------------
        # ------------------------------------------------------------------------

        # Add Prior 5 Minute Hits plots to the figure (5:1, 1x1)
        # ------------------------------------------------------------------------
        # ------------------------------------
        myRow = 5
        myCol = 1
        
        zipped = zip([f'{Home} Hits - Prior 5 min', f'{Away} Hits - Prior 5 min'],
                     ([HCol, ACol]),
                     ['dot', 'dot'])

        for trace, color, line in zipped:
            plot = go.Scatter(x          = prior_5_hits.Time,
                              y          = prior_5_hits[trace],
                              mode       = 'lines',
                              showlegend = False,
                              name       = trace,
                              line       = dict(color=color,
                                                dash=line))
            fig.add_trace(plot, secondary_y=False, row = myRow, col = myCol)
        # ------------------------------------

        # Add period seperating lines to 4th subplot
        # ------------------------------------
        fig = PeriodLines(fig, prior_5_hits, Home, Away, myRow, myCol, 'Hits - Prior 5 min')
        # ------------------------------------

        # Shade areas for Home/Away team power plays
        # Note: Need to figure out a way to neatly
        #       make users aware of this via annotations
        # ------------------------------------
        Pens = [HomePens, AwayPens]
        height = max(prior_5_hits[f'{Home} Hits - Prior 5 min'].max(),
                     prior_5_hits[f'{Away} Hits - Prior 5 min'].max()) + 2

        fig = ShadePenalties(fig, Pens, [ACol, HCol], height, myRow, myCol)
        # ------------------------------------

        # Format the 4th subplot
        # ------------------------------------
        ntick = height if height < 10 else int(height / 2)

        fig.update_yaxes(title_text    = "Hits",
                         secondary_y   = False,
                         showgrid      = False,
                         row           = myRow,
                         col           = myCol,
                         titlefont     = dict(size=22),
                         nticks        = ntick,
                         range         = (0, height - 1),
                         zeroline      = False)

        # Set x-axis title
        fig.update_xaxes(title_text = "Game Time Elapsed",
                         titlefont  = dict(size=18),
                         tickfont   = dict(size=18),
                         showgrid   = False,
                         row        = myRow,
                         col        = myCol,
                         #range      = ["00:00:00", "00:01:00"],
                         tickvals   = ["00:00:00"] +
                         [f"00:{m}:00" for m in range(10, 65, 10)] +
                         ["01:00:00"])
        # ------------------------------------
        # ------------------------------------------------------------------------

        # Create references to the X/Y data frames for shots, attempts, and goals
        # Add GSA map to the figure (1:2, 1x2)
        # ------------------------------------------------------------------------
        # ------------------------------------
        myRow = 1
        myCol = 2
        
        ShotsDfs   = [HomeS, AwayS]
        ShotAttDfs = [HomeSA, AwaySA]
        GoalsDfs   = [HomeG, AwayG]
        Colors     = [HCol, ACol]
        # ------------------------------------

        # Add goal, shots, then attempts scatter points to 5th subplot
        # ------------------------------------
        # Add the `goal` markers to the 5th row scatter plot
        Legend = [Home + ' Goals', Away + ' Goals']
        SecndY = [False, True]
        zipped = zip(GoalsDfs, Colors, Legend, SecndY)

        for Df, color, name, second_y in zipped:
            # Skip team df's if the team scored no goals
            if Df.shape[0] > 0:

                # Create reference to customdata that should be displayed.
                # If no goals were scored with two assists, then there will be
                # no column for player_4. A list of empty strings will be created
                # to mimic a player_4 column.
                if 'player_4' in Df.columns:
                    # Create the customdata to be included in the hovertemplate.
                    # If 'player_4' is a column in `Df` (as is the case with most
                    # games), the customdata follows the "standard" template
                    customdata = np.stack(([str(i or '') for i in Df['player_1']],
                                           [str(i or '') for i in Df['player_2']],
                                           [str(i or '') for i in Df['player_3']],
                                           [str(i or '') for i in Df['player_4']],
                                           [str(i or '') for i in Df['period']],
                                           [str(i or '') for i in Df['period_time']],
                                           ),
                                          axis=-1)
                elif 'player_3' in Df.columns:
                    # If 'player_4' is NOT in `Df`, then no goals were scored with
                    # a secondary assist for the selected team. Fill the player_4
                    # row in `customdata` with the empty string.
                    customdata = np.stack(([str(i or '') for i in Df['player_1']],
                                           [str(i or '') for i in Df['player_2']],
                                           [str(i or '') for i in Df['player_3']],
                                           [str('') for i in Df['player_3']],
                                           [str(i or '') for i in Df['period']],
                                           [str(i or '') for i in Df['period_time']],
                                           ),
                                          axis=-1)
                elif 'player_2' in Df.columns:
                    # If 'player_4' & 'player_3' is NOT in `Df`, then no goals were
                    # scored with any assists for the selected team.
                    # Fill the 'player_4' & 'player_3' rows in `customdata` with
                    # the empty string.
                    customdata = np.stack(([str(i or '') for i in Df['player_1']],
                                           [str(i or '') for i in Df['player_2']],
                                           [str('') for i in Df['player_2']],
                                           [str('') for i in Df['player_2']],
                                           [str(i or '') for i in Df['period']],
                                           [str(i or '') for i in Df['period_time']],
                                           ),
                                          axis=-1)
                # Rearrange player order to make sure the Goalie is correctly annotated
                for i in customdata:
                    # If player_4 is empty, determine which player needs to be re-ordered
                    if i[3] == '':
                        # If player_3 position is empty, the goal was unassisted
                        if str(i[2] or '') == '':
                            i[3], i[1] = i[1], i[3]
                        # Otherwise just player_4 is empty
                        else:
                            i[3], i[2] = i[2], i[3]

                Df.MarkerStyle = 218
                plot = go.Scatter(x             = Df.x,
                                  y             = Df.y,
                                  customdata    = customdata,
                                  hovertemplate = f'<b>{name}</b><br><br>' +
                                    'Goal #: %{text}<br>' +
                                    'Period: %{customdata[4]}<br>' +
                                    'Time: %{customdata[5]}<br><br>'
                                    'Scored By: %{customdata[0]}<br>' +
                                    'Assit*: %{customdata[1]}<br>' +
                                    'Assit**: %{customdata[2]}<br>' +
                                    'Goalie: %{customdata[3]}<br>'
                                    '<extra></extra>',
                                  text          = Df.index,
                                  textfont      = dict(family="Arial",
                                                       size=32,
                                                       color=color),
                                  mode          = "markers+text",
                                  showlegend    = False,
                                  marker_symbol = Df.MarkerStyle,
                                  name          = name,
                                  marker        = dict(color=color,
                                                       size=1),
                                  line          = dict(color=color,
                                                       width=5))
                fig.add_trace(plot, secondary_y=second_y, row = myRow, col = myCol)
        # Add the `Shots` markers to the 5th row scatter plot
        Legend = [Home + ' Shots', Away + ' Shots']
        zipped = zip(ShotsDfs, Colors, Legend)

        for Df, color, name in zipped:
            customdata    = np.stack((Df['player_1'],
                                      Df['player_2'],
                                      Df.index,
                                     [str(i or '') for i in Df['period']],
                                     [str(i or '') for i in Df['period_time']]),
                                     axis=-1)

            plot = go.Scatter(x             = Df.x,
                              y             = Df.y,
                              customdata    = customdata,
                              hovertemplate = f'<b>{name}</b><br><br>' +
                                'Shot #: %{customdata[2]}<br>' +
                                'Period: %{customdata[3]}<br>' +
                                'Time: %{customdata[4]}<br><br>' +
                                'Shot By: %{customdata[0]}<br>' +
                                'Saved By: %{customdata[1]}<br>' +
                                '<extra></extra>',
                              text          = Df['player_1'],
                              mode          = "markers",
                              showlegend    = False,
                              marker_symbol = Df.MarkerStyle,
                              name          = name,
                              marker        = dict(color=color, size=8),
                              line          = dict(color=color, width=10))
            fig.add_trace(plot, secondary_y=False, row = myRow, col = myCol)

        # Add the `Shot Attempts` markers to the 5th row scatter plot
        Legend = [Home + ' Shot Attempts', Away + ' Shot Attempts']
        zipped = zip(ShotAttDfs, Colors, Legend)

        for Df, color, name in zipped:
            customdata    = np.stack((Df['player_1'],
                                      Df['player_2'],
                                      Df.index,
                                     [str(i or '') for i in Df['period']],
                                     [str(i or '') for i in Df['period_time']]),
                                     axis=-1)
            for i in customdata:
                if str(i[1] or '') == '':
                    i[1], i[0] = i[0], 'No One'

            plot = go.Scatter(x             = Df.x,
                              y             = Df.y,
                              customdata    = customdata,
                              hovertemplate = f'<b>{name}</b><br><br>' +
                                'Attempt #: %{customdata[2]}<br>' +
                                'Period: %{customdata[3]}<br>' +
                                'Time: %{customdata[4]}<br><br>' +
                                'Blocked By: %{customdata[0]}<br>' +
                                'Shot By: %{customdata[1]}<br>' +
                                '<extra></extra>',
                              text          = Df['MarkerStyle'],
                              mode          = "markers",
                              showlegend    = False,
                              marker_symbol = Df.MarkerStyle,
                              name          = name,
                              marker        = dict(color=color,
                                                   size=7),
                              line          = dict(color=color,
                                                   width=10))
            fig.add_trace(plot, secondary_y=False, row = myRow, col = myCol)
        # ------------------------------------

        # Format the 5th subplot to look more like an ice rink
        # ------------------------------------
        fig = FormatMap(fig, Home, HCol, Away, ACol, myRow, myCol)
        # ------------------------------------
        # ------------------------------------------------------------------------

        # Add sunburst plots for shot attempts below the SGA map
        # Add GSA sunburst to the figure (2:2, 1x2)
        # ------------------------------------------------------------------------
        # ------------------------------------
        myRow = 2
        myCol = 2
        
        fig = StatSunburst(self, fig, myRow, myCol, 'SHOT ATTEMPT', Home, HCol, Away, ACol)
        # ------------------------------------
        # ------------------------------------------------------------------------

        # Add Hits, Takeaways, then Giveaways to 7th subplot
        # Add HTG Map to the figure (3:2, 1x2)
        # ------------------------------------------------------------------------
        # ------------------------------------
        myRow = 3
        myCol = 2

        # Create references to the X/Y data frames for Hits, Takeaways, and Giveaways
        HitsDfs  = [HomeH, AwayH]
        TkawDfs  = [HomeT, AwayT]
        GvawDfs  = [HomeGA, AwayGA]
        Colors   = [HCol, ACol]
        
        # Add the `Hit` markers to the 7th row scatter plot
        Legend = [Home + ' Hits', Away + ' Hits']
        SecndY = [False, True]
        zipped = zip(HitsDfs, Colors, Legend, SecndY)

        for Df, color, name, second_y in zipped:
            Df.MarkerStyle = 218
            plot = go.Scatter(x             = Df.x,
                              y             = Df.y,
                              customdata    = np.stack((Df['player_1'],
                                                        Df['player_2'],
                                                        Df.index,
                                                        [str(i) for i in Df['period']],
                                                        [str(i) for i in Df['period_time']]),
                                                       axis=-1),
                              hovertemplate = f'<b>{name}</b><br><br>' +
                                               'Hit #: %{customdata[2]}<br>' +
                                               'Period: %{customdata[3]}<br>' +
                                               'Time: %{customdata[4]}<br><br>' +
                                               'Hitter: %{customdata[0]}<br>' +
                                               'Victim: %{customdata[1]}<br>' +
                                               '<extra></extra>',
                              text          = Df['player_1'],
                              mode          = "markers",
                              showlegend    = False,
                              marker_symbol = Df.MarkerStyle,
                              name          = name,
                              marker        = dict(color=color, size=10),
                              line          = dict(color=color, width=50))
            fig.add_trace(plot, secondary_y=second_y, row = myRow, col = myCol)

        # Add the `Takeaways` markers to the 7th row scatter plot
        Legend = [Home + ' Takeaways', Away + ' Takeaways']
        zipped = zip(TkawDfs, Colors, Legend)

        for Df, color, name in zipped:
            Df.MarkerStyle = 26
            plot = go.Scatter(x = Df.x,
                              y = Df.y,
                              customdata    = np.stack((Df['player_1'],
                                                       Df['player_2'],
                                                       Df.index,
                                                       [str(i) for i in Df['period']],
                                                       [str(i) for i in Df['period_time']]),
                                                       axis=-1),
                              hovertemplate = f'<b>{name}</b><br><br>' +
                                'Takeaway#: %{customdata[2]}<br>' +
                                'Period: %{customdata[3]}<br>' +
                                'Time: %{customdata[4]}<br><br>' +
                                'Thief: %{customdata[0]}<br>' +
                                '<extra></extra>',
                              text          = Df['player_1'],
                              mode          = "markers",
                              showlegend    = False,
                              marker_symbol = Df.MarkerStyle,
                              name          = name,
                              marker        = dict(color=color,
                                                   size=10),
                              line          = dict(color=color,
                                                   width=10))
            fig.add_trace(plot, secondary_y=False, row = myRow, col = myCol)

        # Add the `Giveaways` markers to the 7th row scatter plot
        Legend = [Home + ' Giveaways', Away + ' Giveaways']
        zipped = zip(GvawDfs, Colors, Legend)

        for Df, color, name in zipped:
            Df.MarkerStyle = 32
            plot = go.Scatter(x             = Df.x,
                              y             = Df.y,
                              customdata    = np.stack((Df['player_1'],
                                                        Df['player_2'],
                                                        Df.index,
                                                        [str(i) for i in Df['period']],
                                                        [str(i) for i in Df['period_time']]),
                                                       axis=-1),
                              hovertemplate = f'<b>{name}</b><br><br>' +
                                'Giveaway #: %{customdata[2]}<br>' +
                                'Period: %{customdata[3]}<br>' +
                                'Time: %{customdata[4]}<br><br>' +
                                'Giver: %{customdata[0]}<br>' +
                                '<extra></extra>',
                              text          = Df['player_1'],
                              mode          = "markers",
                              showlegend    = False,
                              marker        = dict(color=color,
                                                   size=10),
                              marker_symbol = Df.MarkerStyle,
                              name          = name,
                              line          = dict(color=color,
                                                   width=10))
            fig.add_trace(plot, secondary_y=False, row = myRow, col = myCol)
        # ------------------------------------

        # Format the 7th subplot to look more like an ice rink
        # ------------------------------------
        fig = FormatMap(fig, Home, HCol, Away, ACol, myRow, myCol)
        # ------------------------------------
        # ------------------------------------------------------------------------

        # Add HTG sunburst to the figure (4:2, 1x2)
        # ------------------------------------------------------------------------
        # ------------------------------------
        myRow = 4
        myCol = 2
        
        fig = StatSunburst(self, fig, myRow, myCol, 'HTG', Home, HCol, Away, ACol)
        # ------------------------------------
        # ------------------------------------------------------------------------

        # Add summary stats table to 9th row of figure
        # ------------------------------------------------------------------------
        # ------------------------------------
        # Adjust SumStats multi-index dataframe to be compatible with plotly
        myRow = 6
        myCol = 1
        
        SumStats.columns = [(c[0], c[1]) for c in SumStats.columns]
        SumStats.reset_index(inplace=True, drop=False)
        SumStats.rename(columns={'index': ('Period', 'Team')}, inplace=True)

        # Create a list of fill colors for the table cells
        cell_fill_color = []
        head_fill_color = []
        n = SumStats.shape[1]
        for i in range(n + 1):
            if i == 0:
                cell_fill_color.append(['lightblue'] * n)
                head_fill_color.append(['lightblue'] * 2)

            elif i <= 2:
                cell_fill_color.append(['white'] * n)
                head_fill_color.append(['slategray', [ACol, HCol][(i % 2)]])

            elif i <= 4:
                cell_fill_color.append(['#C8C8C8'] * n)
                head_fill_color.append(['slategray', [ACol, HCol][(i % 2)]])

            elif i <= 6:
                cell_fill_color.append(['#AFAFAF'] * n)
                head_fill_color.append(['slategray', [ACol, HCol][(i % 2)]])

            elif i <= 8:
                cell_fill_color.append(['#969696'] * n)
                head_fill_color.append(['slategray', [ACol, HCol][(i % 2)]])

            elif i <= 10:
                cell_fill_color.append(['beige'] * n)
                head_fill_color.append(['slategray', [ACol, HCol][(i % 2)]])

        # Create the table object to be added to the figure
        table = go.Table(header = dict(values     = list(SumStats.columns),
                                       font       = dict(size=20, color='black'),
                                       line_color = 'darkslategray',
                                       fill_color = head_fill_color,
                                       align      = 'center'),
                         cells  = dict(values     = [SumStats[col] for col in SumStats.columns],
                                       font       = dict(size=16, color='black'),
                                       line_color = 'darkslategray',
                                       fill_color = cell_fill_color,
                                       align      = 'center')
                         )
        fig.add_trace(table, row = myRow, col = myCol)
        # ------------------------------------
        # ------------------------------------------------------------------------

        # Add sunburst plots for the goals scored by player and by period
        # ------------------------------------------------------------------------
        # ------------------------------------
        myRow = 5
        myCol = 2
        
        fig = StatSunburst(self, fig, myRow, myCol, 'GOAL', Home, HCol, Away, ACol)
        # ------------------------------------
        # ------------------------------------------------------------------------

        # Add sunburst plots for the shots on net by player and by period
        # ------------------------------------------------------------------------
        # ------------------------------------
        myRow = 6
        myCol = 2
        
        fig = StatSunburst(self, fig, myRow, myCol, 'SHOT', Home, HCol, Away, ACol)
        # ------------------------------------
        # ------------------------------------------------------------------------

        # Return the resulting figure
        # ------------------------------------
        self.fig = fig
        # ------------------------------------

class PreGame:

    def __init__(self, team, season):
        self.team = team
        self.season = int(season)
        
    def GamesIndex(self):
        team = self.team
        season = self.season
        
        # Due to COVID...
        if season == 2021:
            # Define the special date range for games
            start = dt.date(2021, 1, 1)
            end   = dt.date(2021, 7, 1)
        else:
            # Define the standard date range for games
            start = dt.date(season - 1, 8, 1)
            end   = dt.date(season, 7, 1)
            
        Games = pd.DataFrame(list_games(start, end))
        Games = Games.loc[(Games.home_team == team) | (Games.away_team == team)].reset_index(drop = True)
        Games = Games.loc[Games.game_state == 'Final']
        
        self.Games = Games
        
    def RecentGames(self, n=5):
        
        # Collect the list of recent games
        df = self.Games
        # If n = 0, game stats for the entire season will be collected
        n = n if n != 0 else df.shape[0]
        # df must be the index table of a teams game during a desired season
        
        lst = []
        for i in range(n, 0, -1):
            gameid = df.game_id.iloc[-i]
            
            gp = GameStats.All(gameid)
            lst.append([gameid, gp])
            
        self.RecentGames = lst
    
    def AggGameStats(self):
        
        GPs = self.RecentGames
        teamFull = self.team
        
        # Define list of stats to collect
        stats = ['GOAL', 'SHOT', 'BLOCKED_SHOT', 'MISSED_SHOT', 'HIT', 'TAKEAWAY', 'GIVEAWAY']
        # cols  = ['gameid', 'datetime', 'team_for', 'period', 'event_type', 'player_1', 'player_2']
        
        # Collect the plays df from each of the GameStats classes attached to the MNS objects in GPs
        lst = []
        for i in range(len(GPs)):
            # Collect the plays df stored as an attribute in the gp object
            Home = GPs[i][1].HomeAbrv
            Away = GPs[i][1].AwayAbrv
            team = Home if GPs[i][1].Home == teamFull else Away
            gDay = GPs[i][1].gameDay
            
            plays = GPs[i][1].plays
            plays.loc[:, 'gameid'] = f"{Away}@{Home}<br>{gDay}"  # GPs[i][0]
            
            # Refine df to desired stats and columns
            plays.loc[plays.event_type == 'BLOCKED_SHOT', 'team_for'] = \
                plays.loc[plays.event_type == 'BLOCKED_SHOT', 'team_for'].apply(lambda x: \
                                                                        Home if x == Away else Away)
            plays.loc[plays.event_type == 'BLOCKED_SHOT', 'player_1'] = \
                plays.loc[plays.event_type == 'BLOCKED_SHOT', 'player_2']
            
            kCols = ['gameid', 'team_for', 'period', 'event_type', 'player_1']
            plays = plays.loc[plays.event_type.isin(stats), kCols]
            plays.loc[plays.team_for != team, 'team_for'] = 'OPP'
            plays.reset_index(inplace=True, drop=True)
            
            lst.append(plays)
            
        plays = pd.concat(lst, axis=0)
        plays.columns = ['Game', 'Team', 'Period', 'Event', 'Player']
        
        group = ['Team', 'Event', 'Game', 'Player']
        plays = plays.groupby(group).size().reset_index()
        plays.columns = group + ['Count']
        
        self.plays = plays
        
    def All(self, n=5):
        
        gp = PreGame(self.team, self.season)
        
        PreGame.GamesIndex(gp)
        print("Collected Game Index")
        PreGame.RecentGames(gp, n=n)
        print("Collected Recent Game Stats")
        PreGame.AggGameStats(gp)
        print("Aggregated Game Stats")
        
        return gp

    def Plot(self):
        
        MPdict  = {"secondary_y": True, 'colspan': 2, 'rowspan': 1}   # GameMap specs
        SBdict  = {"type": "sunburst", 'colspan': 1, 'rowspan': 1}    # Sunburst plot specs
        TBdict  = {"type": "table", 'colspan': 1, 'rowspan': 1}       # Table specs
        
        fig = make_subplots(rows  = 6,
                            cols  = 2,
                            specs = [[SBdict, SBdict],
                                     [SBdict, SBdict],
                                     [SBdict, SBdict],
                                     [SBdict, SBdict],
                                     [SBdict, SBdict],
                                     [SBdict, SBdict]],
                            column_widths  = [1, 1],
                            row_heights    = [1, 1, 1, 1, 1, 1],
                            subplot_titles = ("Goals | By PERIOD", "Goals | By PLAYER",
                                              "Shots | By PERIOD", "Shots | By PLAYER",
                                              "Attempts | By PERIOD", "Attempts | By PLAYER",
                                              "Hits | By PERIOD", "Hits | By PLAYER",
                                              "Takeaways | By PERIOD", "Takeaways | By PLAYER",
                                              "Giveaways | By PERIOD", "Giveaways | By PLAYER",
                                              ),
                            vertical_spacing   = 0.06,
                            horizontal_spacing = 0.05)
        
        