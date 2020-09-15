# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 2020

@author: grega
"""
## Import necessary modules
import pandas as pd
import numpy as np
import os
from datetime import *
import datetime as dt
from datetime import time
import time

from nhlstats import *
from nhlstats.formatters import csv

import matplotlib as mpl
from matplotlib import pyplot as plt
from matplotlib import style, dates
import matplotlib.gridspec as gridspec

import matplotlib.image as image
from matplotlib.ticker import MaxNLocator
import matplotlib.collections as collections
import matplotlib.patches as patches
import matplotlib.markers as mmarkers

class GamePlot:
    
    def __init__(self, game_id):
        
        self.game_id = game_id
        
        self.plays = pd.DataFrame(list_plays(game_id))
        self.shots = pd.DataFrame(list_shots(game_id))
        self.shift = pd.DataFrame(list_shifts(game_id))
                
        self.gameDay = pd.to_datetime(self.plays['datetime']).iloc[0].date() 
        self.Teams = pd.DataFrame(list_games(str(self.gameDay + dt.timedelta(days=-1)), str(self.gameDay)))
        self.Teams = self.Teams[self.Teams.game_id == game_id]
        
        self.Home = self.Teams.home_team.iloc[0]
        self.Away = self.Teams.away_team.iloc[0]
        
        # Define team name references
        tL = pd.read_csv('teamList.csv') # store as csv file in GH?

        self.HomeAbrv = tL[tL.team_name == self.Home].team_abbrv.max()    
        self.AwayAbrv = tL[tL.team_name == self.Away].team_abbrv.max()
    
        self.Home_Color1 = tL[tL.team_abbrv == self.HomeAbrv].home_c.max()
        self.Home_Color2 = tL[tL.team_abbrv == self.HomeAbrv].away_c.max()
    
        self.Away_Color1 = tL[tL.team_abbrv == self.AwayAbrv].away_c.max()    
        self.Away_Color2 = tL[tL.team_abbrv == self.AwayAbrv].home_c.max() 
            
    def ModifyDFs(self):
    
        # Add column to shots and plays DF's for time elapsed
        self.shots['Time'] = pd.to_datetime(self.shots.period_time, format="%M:%S")
        self.shots['Minute'] = self.shots['Time'].dt.minute
        self.shots['Second'] = self.shots['Time'].dt.second
    
        self.plays['Time'] = pd.to_datetime(self.plays.period_time, format="%M:%S")
        self.plays['Minute'] = self.plays['Time'].dt.minute
        self.plays['Second'] = self.plays['Time'].dt.second
    
        # Parse out plays for each period of regulation and adjust time elapsed
        plays_1 = self.plays[self.plays.period == 1].reset_index()
    
        plays_2 = self.plays[self.plays.period == 2].reset_index()
        plays_2.Time += dt.timedelta(minutes=20)
        plays_2.Minute += 20
    
        plays_3 = self.plays[self.plays.period == 3].reset_index()
        plays_3.Time += dt.timedelta(minutes=40)
        plays_3.Minute += 40
    
        # Parse out OT and Shootouts
        plays_4 = self.plays[self.plays.period == 4].reset_index()
        plays_4.Time += dt.timedelta(minutes=60)
        plays_4.Minute += 60
    
        plays_5 = self.plays[self.plays.period == 5].reset_index()
        plays_5.Time += dt.timedelta(minutes=65)
        plays_5.Minute += 65
    
        self.plays = pd.concat([plays_1,plays_2,plays_3,plays_4,plays_5],axis=0)
        self.plays.Time = [d.time() for d in self.plays.Time]
    
        self.plays.set_index('Time',inplace=True, drop=True)
        self.plays = self.plays.drop(columns=['index'])
        
        #Define variable for date of game
        self.plays['datetime'] = pd.to_datetime(self.plays['datetime'])
    
        #Identify date of game now before modifications are made to `plays`
        temp = self.plays.datetime.iloc[0]
        self.gameDay = dt.datetime(year=temp.year,month=temp.month,day=temp.day)
        self.gameDay = dt.datetime.strftime(self.gameDay,'%d-%b-%Y')
            
    def AggregateData(self):
        Away = self.AwayAbrv
        Home = self.HomeAbrv
        plays = self.plays

        # Add empty columns for shots and goals
        newS = [Away + " Goals",
                Home + " Goals",
                Away + " Shots",
                Home + " Shots",
                Away + " Hits",
                Home + " Hits",
                Away + " Shot Attempts",
                Home + " Shot Attempts",
                Away + " Blocked Shots",
                Home + " Blocked Shots",
                Away + " Missed Shots",
                Home + " Missed Shots"]    
        
        # Create empty columns in plays DF for game stats
        for S in newS:
            plays[S] = 0
        
        # Loop through each row of the plays DF to sort through each event 
        self.plays.reset_index(inplace=True,drop=False)
        for i in range(0,plays.shape[0]):
                
            event = self.plays.loc[i,'event_type']
            team = self.plays.loc[i,"team_for"]
            
            ########################################### REDO
            ########################################### Goals
            if event == 'GOAL':
                plays.loc[i,team + ' Goals'] = 1
            ########################################### Shots on Net
            if event in ['SHOT', 'GOAL']:
                plays.loc[i,team + ' Shots'] = 1
            ########################################### Shot Attempts
            if event in ['MISSED_SHOT','SHOT', 'GOAL']:
                plays.loc[i,team + ' Shot Attempts'] = 1
            ########################################### Blocked Shots
            # Record the blocked shot for the blocking team,
            # and the shot attempt for the shooting team
            if event == 'BLOCKED_SHOT':
                if team == Away:
                    # Record block for away team
                    plays.loc[i,newS[8]] = 1
                    # Record shot attempt for home team
                    plays.loc[i,newS[7]] = 1
                elif team == Home:
                    # Record block for home team
                    plays.loc[i,newS[9]] = 1
                    # Record shot attempt for away team
                    plays.loc[i,newS[6]] = 1
            ########################################### Missed Shots
            if event == 'MISSED_SHOT':
                plays.loc[i,team + ' Missed Shots'] = 1
            ########################################### Hits
            if event == 'HIT':
                plays.loc[i,team + ' Hits'] = 1
                
        for i in range(plays.shape[0]-1,-1,-1):
            plays.loc[i,newS] = plays.loc[:i-1,newS].sum(axis=0)

        plays['Shot Differential'] = abs(self.plays[newS[3]] - self.plays[newS[2]])
        
    def Prior5Shots(self):
        Away = self.AwayAbrv
        Home = self.HomeAbrv
        plays = self.plays
        
        x = 61
    
        #Create DF to calculate each team's shots for prior 5 minutes
        prior_5_shots = [dt.time(0,i,0) for i in range(0,x-1)]
        prior_5_shots.append(dt.time(1,0,0))
    
        #If the game goes into OT, extend the Df
        if 4 in plays.period.unique():
            x = 66
            for i in range(1,6):
                prior_5_shots.append(dt.time(1,i,0))
    
        prior_5_shots = {'Time' : prior_5_shots}
        prior_5_shots = pd.DataFrame(prior_5_shots)
        prior_5_shots.set_index('Time',inplace=True)
    
        #Add necessary columns
        prior_5_shots[Away + " Shots"] = ''
        prior_5_shots[Away + " Shots - Prior 1 min"] = ''
        prior_5_shots[Away + " Shots - Prior 5 min"] = ''
        prior_5_shots[Home + " Shots"] = ''
        prior_5_shots[Home + " Shots - Prior 1 min"] = ''
        prior_5_shots[Home + " Shots - Prior 5 min"] = ''
    
        # Loop through `plays` to populate prior_5_shots shots columns
        for i in range(0,x):
            #Find starting shot total for each minute of gameplay
            prior_5_shots.iloc[i,0] = plays[plays.Minute == i][Away + " Shots"].min()
            prior_5_shots.iloc[i,3] = plays[plays.Minute == i][Home + " Shots"].min()
    
            # If no plays/actions were recorded for a certain minute, plug shots columns with shots for prior minute
            if ((type(plays[plays.Minute == i][Away + " Shots"].min()) == float) | \
               (type(plays[plays.Minute == i][Home + " Shots"].min()) == float)):
                prior_5_shots.iloc[i,0] = prior_5_shots.iloc[i-1,0]  # Away shots
                prior_5_shots.iloc[i,3] = prior_5_shots.iloc[i-1,3]  # Home shots
    
        # Calculate the difference of shots per minute, then the sum of these differences for each five minute interval
        for i in range(0,x):
                if i > 0:
                    # Prior minute
                    prior_5_shots.iloc[i,1] = prior_5_shots.iloc[i,0] - prior_5_shots.iloc[i-1,0]
                    prior_5_shots.iloc[i,4] = prior_5_shots.iloc[i,3] - prior_5_shots.iloc[i-1,3]
    
                if i >= 5:
                    # Prior 5 minutes
                    sumA = 0
                    sumH = 0
                    for x in range(0,5):
                        sumA += prior_5_shots.iloc[i-x,1]
                        sumH += prior_5_shots.iloc[i-x,4]
    
                    prior_5_shots.iloc[i,2] = sumA
                    prior_5_shots.iloc[i,5] = sumH
    
        # Trim DF
        prior_5_shots = prior_5_shots[[Away + " Shots", Away + " Shots - Prior 5 min",\
                                       Home + " Shots", Home + " Shots - Prior 5 min"]]
    
        for i in range(0,6):
            prior_5_shots.iloc[i,1] = prior_5_shots.iloc[i,0]
            prior_5_shots.iloc[i,3] = prior_5_shots.iloc[i,2]
        
        self.prior_5_shots = prior_5_shots

    def Prior5Hits(self):
        Away = self.AwayAbrv
        Home = self.HomeAbrv
        plays = self.plays
            
        x = 61
        
        #Create DF to calculate each team's shots for prior 5 minutes
        prior_5_hits = [dt.time(0,i,0) for i in range(0,x-1)]
        prior_5_hits.append(dt.time(1,0,0))
        
        #If the game goes into OT, extend the Df
        if 4 in plays.period.unique():
            x = 66
            for i in range(1,6):
                prior_5_hits.append(dt.time(1,i,0))
        
        prior_5_hits = {'Time' : prior_5_hits}
        prior_5_hits = pd.DataFrame(prior_5_hits)
        prior_5_hits.set_index('Time',inplace=True)
        
        #Add necessary columns
        prior_5_hits[Away + " Hits"] = ''
        prior_5_hits[Away + " Hits - Prior 1 min"] = ''
        prior_5_hits[Away + " Hits - Prior 5 min"] = ''
        prior_5_hits[Home + " Hits"] = ''
        prior_5_hits[Home + " Hits - Prior 1 min"] = ''
        prior_5_hits[Home + " Hits - Prior 5 min"] = ''
    
        #Loop through `plays` to populate prior_5_hits hits columns
        for i in range(0,x):
            #Find highest hit total for each minute of gameplay
            prior_5_hits.iloc[i,0] = plays[plays.Minute == i][Away + " Hits"].min()
            prior_5_hits.iloc[i,3] = plays[plays.Minute == i][Home + " Hits"].min()
        
            #If no plays/actions were recorded for a certain minute, plug hits columns with total hits for the prior minute
            if ((type(plays[plays.Minute == i][Away + " Hits"].min()) == float) | \
                (type(plays[plays.Minute == i][Home + " Hits"].min()) == float)):
                prior_5_hits.iloc[i,0] = prior_5_hits.iloc[i-1,0]
                prior_5_hits.iloc[i,3] = prior_5_hits.iloc[i-1,3]
        
        #Calculate the difference of hits per minute, then the sum of these differences for each five minute interval        
        for i in range(0,x):
            #Prior minute
            if i > 0:
                prior_5_hits.iloc[i,1] = prior_5_hits.iloc[i,0] - prior_5_hits.iloc[i-1,0]
                prior_5_hits.iloc[i,4] = prior_5_hits.iloc[i,3] - prior_5_hits.iloc[i-1,3]
    
                #Prior 5 minutes
                if i >= 5:
                    sumA = 0
                    sumH = 0
                    for x in range(0,5):
                        sumA += prior_5_hits.iloc[i-x,1]
                        sumH += prior_5_hits.iloc[i-x,4]
    
                    prior_5_hits.iloc[i,2] = sumA
                    prior_5_hits.iloc[i,5] = sumH
    
        #Trim DF
        prior_5_hits = prior_5_hits[[Away + " Hits", Away + " Hits - Prior 5 min",\
                                     Home + " Hits", Home + " Hits - Prior 5 min"]]
    
        #Add values for prior 5-minutes of hits to first 5 rows
        for i in range(0,6):
            prior_5_hits.iloc[i,1] = prior_5_hits.iloc[i,0]
            prior_5_hits.iloc[i,3] = prior_5_hits.iloc[i,2]
            
        self.prior_5_hits = prior_5_hits
           
    def MenOnIce(self):
        # Define function w/in MenOnIce to determine PP/PK stats
        def PenaltyComp(team, i, Home, Away, plays, pen_Home, pen_Away):
            # Input team as the team that took the penalty
            # Define refernces for short-handed team and power play team
            if team == Home:
                shTeam = Home
                ppTeam = Away
                
            else:
                shTeam = Away
                ppTeam = Home
            
            PenType = plays.loc[i, 'event_secondary_type']
            pim = 2
            
            minors = ['Boarding', 'Charging', 'Clipping', 'Elbowing', 'Hooking', 'Illegal check to the head',
                      'Kneeing', 'Roughing', 'Throwing equipment', 'Holding', 'Hooking', 'Interference', 'Tripping',
                      'Cross checking', 'Hi-sticking', 'Slashing', 'Delaying Game - Puck over glass', 'Delay of game',
                      'Delaying the game', 'Embellishment', 'Closing hand on puck', 'Interference - Goalkeeper',
                      'Too many men on the ice', 'Unsportsmanlike conduct']
            double = ['Hi stick - double minor', 'Cross check - double minor', 'Spearing']
            if PenType in double:
                pim = 4
                
            majors = ['Fighting', 'Kicking', 'Slew-footing', 'Butt-ending']
            if PenType in majors:
                pim = 5
            miscon = ['Instigator - Misconduct', 'Misconduct', 'Game misconduct']
            if PenType in miscon:
                pim = 10
                plays.loc[i:, shTeam + " PIM"] += pim
                return plays, pen_Home, pen_Away
            
            if (plays.loc[i, 'player_1'] == plays.loc[i+1, 'player_1']) & \
            (plays.loc[i+1, 'event_secondary_type'] in miscon) & \
            (pim != 5):
                pim = 5
            
            # Take one man away from "Men on Ice" columns for shTeam
            # Record one power play for the pp team
            plays.loc[i, shTeam + " Men On Ice"] -= 1
            plays.loc[i:, ppTeam + " Power Plays"] += 1
            
            # Record PIM in plays df                
            plays.loc[i:, shTeam + " PIM"] += pim            
            # Create minute and second references
            minute, second = plays.Minute.iloc[i], plays.Second.iloc[i]
            # Create temporary end time (assumes all penalties are 2 minutes. Will need to create a comprehension for majors & double minors)
            start, end = (minute, second), (minute + pim, second)
            
            x = i + 1 # temp row reference
            # Initiate while loop to handle MOI, PPG, SHG
            while (((plays.Minute.iloc[x] == minute + pim) & (plays.Second.iloc[x] <= second)) | \
                   (plays.Minute.iloc[x]  < minute + pim)): 
                
                plays.loc[x, shTeam + " Men On Ice"] -= 1 # Record one man down for PK in each row of plays df
        
                # Short handed goal scored
                if (plays.loc[x, 'event_type'] == 'GOAL') & \
                   (plays.loc[x, 'team_for'] == shTeam) & \
                   (plays.loc[x, shTeam + ' is_shg'] == False):
                    
                    # Penalized team scores, record SHG
                    plays.loc[x:, shTeam + " SHG"] += 1
                    plays.loc[x:, shTeam + ' is_shg'] = True
                    #print(f"{plays.Minute.iloc[x]}:{plays.Second.iloc[x]} {plays.team_for.iloc[x]}: {plays.event_description.iloc[x]}")
                
                # PP team scores. Record PPG & end penalty comprehension
                elif (plays.loc[x, 'event_type'] == 'GOAL') & \
                     (plays.loc[x, 'team_for'] == ppTeam) & \
                     (plays.loc[x, ppTeam + ' is_ppg'] == False):
        
                    # Team on PP scores, record PPG, end comprehension
                    end = (plays.Minute.iloc[x], plays.Second.iloc[x])             
                    plays.loc[x:, ppTeam + " PPG"] += 1 # Team on PP scores, record PPG
                    plays.loc[x, ppTeam + ' is_ppg'] = True
                    #print(f"{plays.Minute.iloc[x]}:{plays.Second.iloc[x]} {plays.team_for.iloc[x]}: {plays.event_description.iloc[x]}")
                    break
                    
                else:
                    # continue with next iteration
                    x += 1
                
                # End while loop if end of plays df has been reached. 
                # Happens when penalty is currently happening, or game ends with time left on penalty
                if x >= plays.shape[0]:
                    break
            # append penalty data for relevant team
            if team == Home:
                pen_Home.append((start,end))
            else:
                pen_Away.append((start,end))            
            # return updated plays df and penalty lists
            return plays, pen_Home, pen_Away
        
        # Create shorter, temporary, references
        Away = self.AwayAbrv
        Home = self.HomeAbrv
        plays = self.plays
        
        # Each team starts with 5 men on ice, 0 PPG, 0 SHG, & 0 Penalties.
        # Also create boolean reference columns and PIM counter
        plays[Home + " Men On Ice"] = 5
        plays[Away + " Men On Ice"] = 5
        
        plays[Home + " PPG"] = 0
        plays[Away + " PPG"] = 0
        plays[Home + " SHG"] = 0
        plays[Away + " SHG"] = 0
        
        plays[Home + " is_ppg"] = False
        plays[Away + " is_ppg"] = False
        plays[Home + " is_shg"] = False
        plays[Away + " is_shg"] = False
        
        plays[Home + " Power Plays"] = 0
        plays[Away + " Power Plays"] = 0
        
        plays[Home + " PIM"] = 0
        plays[Away + " PIM"] = 0
        
        pen_Home = []
        pen_Away = []    
        
        # Loop through each record of plays df to aggregate PP/PK data
        for i in range(0,plays.shape[0]):
            if (plays.event_type.iloc[i] == 'PENALTY') & \
            (plays.event_secondary_type.iloc[i] != 'Fighting'):
                plays, pen_Home, pen_Away = PenaltyComp(plays.team_for.iloc[i], i, Home, Away, plays, pen_Home, pen_Away)
            
        # Convert list of tuples into nested list with start/end times of penalties
        # Used to add goal markers to mpl plots
        HomePens = []
        AwayPens = []
        
        for i in pen_Home:
            start = i[0]
            end = i[1]
            
            start = start[0] + round(start[1]/60,3)
            end = end[0] + round(end[1]/60,3)
            
            HomePens.append((start,end))
        for x in pen_Away:
            start = x[0]
            end = x[1]
            
            start = start[0] + round(start[1]/60,3)
            end = end[0] + round(end[1]/60,3)
            
            AwayPens.append((start,end))
        
        # Update plays df and add penalty list attributes
        self.plays = plays
        self.HomePens = HomePens
        self.AwayPens = AwayPens

    def GoalsDF(self):
        """
        
        """
        plays = self.plays
        Home = self.HomeAbrv
        Away = self.AwayAbrv
        ######################################################### Define CreateGoalsDF
        def CreateGoalsDF(plays, team):
            """
            Will create a time series of just goals with 
            minute and secod references. Used in top plot for
            vertical goal bars

            Parameters
            ----------
            plays : TYPE
                DESCRIPTION.
            team : TYPE
                DESCRIPTION.
            """
            df = plays.copy()
            df.set_index("Time", inplace=True,drop=True)
            df = df[[team + " Goals"]].drop_duplicates()
            df = df.reset_index()
            
            for i in range(0,df.shape[0]):
                df.iloc[i,0] = str(df.iloc[i,0])
                
            df['Hour'] = df.Time.str.slice(start=0, stop=2)
            df['Hour'] = pd.to_numeric(df.Hour,downcast='integer')    
            df['Minute'] = df.Time.str.slice(start = 3, stop = 5)
            df['Minute'] = pd.to_numeric(df.Minute,downcast='integer')
            df['Seconds'] = df.Time.str.slice(start=6, stop = 8)
            df['Seconds'] = pd.to_numeric(df.Seconds,downcast='integer')
        
            df.set_index('Time',inplace=True)
            max_Goal = df[team + " Goals"].iloc[:].max()
            
            return df, max_Goal
            
        # Home Team Goals / total goals scored
        home_goals, max_hGoal = CreateGoalsDF(plays, Home)
        away_goals, max_aGoal = CreateGoalsDF(plays, Away)
        
        max_Goal = max([max_aGoal,max_hGoal])
        self.Goals = [home_goals, away_goals, max_hGoal, max_aGoal, max_Goal]
    
    def SumDF(self):
        """
        

        Returns
        -------
        TYPE
            DESCRIPTION.

        """
        plays = self.plays
        Home = self.HomeAbrv
        Away = self.AwayAbrv
        #self.GameIndex, self.OT = getIndex(self)        
        
        # Determine if game went to OT
        if 4 in plays.period.unique():
            self.OT = True
        else:
            self.OT = False
            
        if self.OT == False:
            periods = 4     # Add 1 to inlcude room for a summary column
        else:
            periods = 5     # Assume only 1 OT period played
            # Will need to add flexibility for playoff OT format
        
        # Define sum stats we want to collect
        lst = ["Goals", "Shots", "Shot %", "Shot Attempts", "S/SA %", "Blocked Shots", "Missed Shots", "Hits", "Power Plays", "PPG", "SHG", "PIM"]
        dic = {}    
        
        for p in range(1,periods,1):
            tempHlst = []  # Reset temp lists for each loop of `p`
            tempAlst = []

            for i in lst:

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

                tempH = plays[(plays.event_type == 'PERIOD_END') & (plays.period == p)][f"{Home} {i}"].min()
                tempA = plays[(plays.event_type == 'PERIOD_END') & (plays.period == p)][f"{Away} {i}"].min()
    
                tempHlst.append(tempH)
                tempAlst.append(tempA)
        
            if p == 4:
                p = 'OT'
                
            dic.update({(p, Home) : tempHlst})
            dic.update({(p, Away) : tempAlst})
            
        # Create DF of selected summary stats
        SumStats = pd.DataFrame.from_dict(dic,orient='columns')
        
        # Transpose and rename columns for a better looking layout
        SumStats = SumStats.transpose(copy=True)
        SumStats.columns=lst
        
        idx = pd.IndexSlice
        
        if self.OT == False:
            fp = 3
        else:
            fp = 'OT'
        
        FS = SumStats.loc[idx[fp,:],:]
        FS.index = pd.MultiIndex.from_tuples([('Game Total', Home),
                                              ('Game Total', Away)],
                                             names=['Period', 'Team']
                                             )

        # Define styles and formats for html style DF
        def highlight(s):
            is_max = s == s.max()
            return ['background-color: #88D8B0' if v else '#D9D9D9' for v in is_max]
        
        def grey1(s):
            is_max = s == s.max()
            return ['background-color: #C8C8C8' if v else '#C8C8C8' for v in is_max.index]
        
        def grey2(s):
            is_max = s == s.max()
            return ['background-color: #AFAFAF' if v else '#AFAFAF' for v in is_max.index]
        
        def grey3(s):
            is_max = s == s.max()
            return ['background-color: #969696' if v else '#969696' for v in is_max.index]
        
        
        def hover(Home_Color, hover_color='lightblue'):
            return dict(selector="tr:hover",
                        props=[("background-color", "%s" % hover_color),
                                ("border", f"4px solid {self.Home_Color1}")])
        
        cols = ["Goals","Shots", "Shot Attempts", "Blocked Shots", "Missed Shots", "Hits", "Power Plays", "PPG", "SHG", "PIM"]
    
        SumStats.loc[idx[2,Home],cols] = SumStats.loc[idx[2,Home],cols] - \
                                         SumStats.loc[idx[1,Home],cols]
        SumStats.loc[idx[3,Home],cols] = SumStats.loc[idx[3,Home],cols] - \
                                         SumStats.loc[idx[2,Home],cols] - \
                                         SumStats.loc[idx[1,Home],cols]
    
        SumStats.loc[idx[2,Away],cols] = SumStats.loc[idx[2,Away],cols] - \
                                         SumStats.loc[idx[1,Away],cols]
        SumStats.loc[idx[3,Away],cols] = SumStats.loc[idx[3,Away],cols] - \
                                         SumStats.loc[idx[2,Away],cols] - \
                                         SumStats.loc[idx[1,Away],cols]
    
        if self.OT == True:
            SumStats.loc[idx['OT',Home],cols] = SumStats.loc[idx['OT',Home],cols] - \
                                                SumStats.loc[idx[3,Home],cols] - \
                                                SumStats.loc[idx[2,Home],cols] - \
                                                SumStats.loc[idx[1,Home],cols]
            SumStats.loc[idx['OT',Away],cols] = SumStats.loc[idx['OT',Away],cols] - \
                                                SumStats.loc[idx[3,Away],cols] - \
                                                SumStats.loc[idx[2,Away],cols] - \
                                                SumStats.loc[idx[1,Away],cols]
        
        SS = pd.concat([FS,SumStats])
    
        SS['Shot %'] = (SS["Goals"] / SS['Shots']) * 100
        SS['Shot %'] = pd.Series(["{0:.0f}%".format(val) for val in SS['Shot %']], index = SS.index)
    
        SS['S/SA %'] = (SS['Shots'] / SS['Shot Attempts']) * 100
        SS['S/SA %'] = pd.Series(["{0:.0f}%".format(val) for val in SS['S/SA %']], index = SS.index)
    
        SS = SS.transpose(copy=False)
    
        custom_styles = [
            hover(self.Home_Color2),
            dict(selector="th", props=[("font-size", "150%"),
                                       ("text-align", "center"),
                                      ('border','1px solid #000000')]),
            dict(selector="td", props=[("font-size", "125%"),
                                       ("text-align", "center"),
                                       ('border','1px solid #000000')]),
            dict(selector="caption", props=[("caption-side", "bottom")])]
        
        SSstyle = SS.style.set_properties(**{'text-align': 'center',
                                            'color': 'black',
                                            'border-color': 'grey'}) \
                          .apply(highlight,axis=1, subset=["Game Total"]) \
                          .apply(grey1, axis=1, subset=[1]) \
                          .apply(grey2, axis=1, subset=[2]) \
                          .apply(grey3, axis=1, subset=[3]) \
                          .set_table_styles(custom_styles) \
    
        SS_html = SSstyle.render()
        
        self.SumStats = SumStats
        self.SumStatsStylehtml = SS_html  
        self.SumStatsStyle = SSstyle
    
    def Plot(self, save=False, AltColor=[False, False]):
        """
        

        Parameters
        ----------
        save : TYPE, optional
            DESCRIPTION. The default is False.
        AltColor : TYPE, optional
            DESCRIPTION. The default is [False, False].

        Returns
        -------
        r : TYPE
            DESCRIPTION.
        x : TYPE
            DESCRIPTION.

        """
        plays = self.plays
        plays.set_index("Time",drop=True,inplace=True)
        
        gameday = self.gameDay
        OT = self.OT
        
        Home = self.HomeAbrv
        # Determine which colors user wants (default to standard home/away colors for each team)
        if AltColor[0] == False:
            Home_Color = self.Home_Color1   # Use standard home color for the team
        else:
            Home_Color = self.Home_Color2   # Use the away color for the team (for better looking plots)
        
        home_goals = self.Goals[0]
        
        # Determine which colors user wants (default to standard home/away colors for each team)
        if AltColor[1] == False:
            Away_Color = self.Away_Color1
        else:
            Away_Color = self.Away_Color2
            
        Away = self.AwayAbrv
        
        away_goals = self.Goals[1]
        
        max_Goal = self.Goals[4]
        prior_5_shots = self.prior_5_shots
        prior_5_hits = self.prior_5_hits
        
        HomePens = self.HomePens
        AwayPens = self.AwayPens
        
        pd.plotting.register_matplotlib_converters()
        
        # Collect team logos
        filePath = "C:\\Users\\grega\\Google Drive\\Python\\NHLstats\\Team Logos\\"
        HomeIm = image.imread(filePath + f"{Home}.png")
        AwayIm = image.imread(filePath + f"{Away}.png")
        
        def ResizeIm(ax, image=None):
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)
        
            ax.get_xaxis().set_ticks([])
            ax.get_yaxis().set_ticks([])
        
            if len(image) > 0:
                ax.set_xlim([0,image.shape[1]])
                ax.set_ylim([image.shape[0],0])
        
            ax.patch.set_alpha(0)
            plt.grid(b=None)
            
        def PeriodLines(ax, OT=False):
            # Set face color of subplot
            ax.set_facecolor('#757171')
            
            # Add vertical bars to graph to mark end of periods.
            plt.axvline(x=1200,c='black',linestyle='--', lw=5)
            plt.axvline(x=2400,c='black',linestyle='--', lw=5)
            plt.axvline(x=3600,c='black',linestyle='--', lw=5)    
            
            # Turn axis grid off and add standard x label
            ax.grid(False)
            plt.xlabel('Game Time Elapsed (HH:MM)')
            
            # Determine xlim and values to use as tick marks
            r = 65
            if OT == True:
                plt.axvline(x=3900,c='red',linestyle='--')
                ax.set_xlim([0,60*65])
                r = 70
            else:
                ax.set_xlim([0,60*60])    
        
            x = [i * 60 for i in range(5,r-5,5)] # Create list of tick label positions for 5 minute intervals
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            
            formatter = mpl.ticker.FuncFormatter(lambda ms, x: time.strftime('%H:%M', time.gmtime(ms)))
            ax.xaxis.set_major_formatter(formatter)
            ax.set_xticks(x)
            
           #mpl.rc('axes', titlesize=35)     # fontsize of the axes title
           #mpl.rc('xtick', labelsize=18)    # fontsize of the tick labels
           #mpl.rc('ytick', labelsize=24)    # fontsize of the tick labels
           #mpl.rc('legend', fontsize=16)    # legend fontsize
            
            return r, x
        
        style.use('ggplot')
        plt.style.use(['seaborn-dark'])
        #######################################################################################################
        # 1                                                                                                   #
        #######################################################################################################
        
        ################################################################# Create figure and axis objects for plot
        fig = plt.figure(figsize=(20.25,35))
        
        plt.subplots_adjust(hspace=0.04)
        #make outer gridspec
        outer = gridspec.GridSpec(2, 1, height_ratios = [1, 6]) 
        #make nested gridspecs
        gs1 = gridspec.GridSpecFromSubplotSpec(1, 5, subplot_spec = outer[0], hspace = 0.25)
        gs2 = gridspec.GridSpecFromSubplotSpec(4, 1, subplot_spec = outer[1], hspace = 0.5)
        
        #######################################################################################################
        # 2                                                                                                   #
        #######################################################################################################
        
        ############################################ Add team logos to top row of gridspec
        
        ####################### Away image
        imA = fig.add_subplot(gs1[0,1])
        
        ResizeIm(imA, AwayIm)
        
        plt.xlabel(self.Away, fontsize=26)
        
        AIm = plt.imshow(AwayIm)
        
        ####################### @ image
        imT = fig.add_subplot(gs1[0,2])
        
        ResizeIm(imT, [])
        
        imT.set_xlim([0,1])
        imT.set_ylim([0,0.15])
        
        plt.text(0.15,0.05,"@", fontsize=96)
        plt.text(0.05,0.1, f"{gameday}", fontsize=26)
        
        ####################### Home image
        imH = fig.add_subplot(gs1[0,3])
        
        ResizeIm(imH, HomeIm)
        
        plt.xlabel(self.Home, fontsize=26)
        
        HIm = plt.imshow(HomeIm)
        
        #######################################################################################################
        # 3                                                                                                   #
        #######################################################################################################
        mpl.rc('xtick', labelsize=26)    # fontsize of the tick labels
        mpl.rc('xtick', color='red')
        mpl.rc('ytick', labelsize=26)    # fontsize of the tick labels
        mpl.rc('legend', fontsize=20)    # legend fontsize     
        mpl.rc('axes', titlesize=35)     # fontsize of the axis title
        mpl.rc('axes', labelsize=30)     # fontsize of the axis labels
        ################################################################# Create Top Plot - Shots & Goals
        ax0 = fig.add_subplot(gs2[:2,0])
        
        ############################################# Plot shots and differential data
        ######################## Away Plots
        plt.plot(plays.index,
                 plays[Away + " Shots"],
                 c=Away_Color,
                 lw=4,
                 label=Away + " Shots")
        
        plt.plot(plays.index,
                 plays[Away + " Shot Attempts"],
                 c = Away_Color, 
                 linestyle='--', 
                 lw=4,
                 label=Away + " Shot Attempts")
        
        ######################## Home Plots
        plt.plot(plays.index,
                 plays[Home + " Shots"],
                 c=Home_Color,
                 lw=4,
                 label=Home + " Shots")
        
        plt.plot(plays.index,
                 plays[Home + " Shot Attempts"],
                 c = Home_Color,
                 linestyle='--',
                 lw=4,
                 label=Home + " Shot Attempts")
        
        ############################################# Add vertical bars to graph to mark end of periods.
        r, x = PeriodLines(ax0, OT)
        
        ############################################# Add xlabels and ylabels to `ax0`
        plt.ylabel('Shots on Goal')
        plt.legend(loc=2)
        plt.grid(b=True, axis='x',color='grey')             
        ###################################################################### Add goals to right side axis of ax0
        ax1 = ax0.twinx()
        
        ############################################# Plot goals per team
        ############################################# Define labels to use for legend
        my_label = {'Home' : Home + " Goals", 'Away' : Away + " Goals"}
        
        ############################################# Add vertical lines for away goals
        for i in range(0,away_goals.shape[0]):
            goals = away_goals[Away + " Goals"].iloc[i]
            g_time = (60 * away_goals.Hour.iloc[i].max()) + \
                      away_goals.Minute.iloc[i].max() + \
                      (away_goals.Seconds.iloc[i].max()/60)
            
            plt.axvline(x = 60*g_time,
                        ymin=0,
                        ymax = goals / (max_Goal+1),
                        c=Away_Color,
                        label=my_label['Away'],
                        lw = 10)
            my_label['Away'] = "_nolegend_"
            
        ############################################# Add vertical lines for home goals
        for i in range(0,home_goals.shape[0]):
            goals = home_goals[Home + " Goals"].iloc[i]
            g_time = (60 * home_goals.Hour.iloc[i].max()) + \
                      home_goals.Minute.iloc[i].max() +\
                      (home_goals.Seconds.iloc[i].max()/60)
            
            plt.axvline(x = 60*g_time,
                        ymin=0,
                        ymax=goals / (max_Goal+1),
                        c=Home_Color,
                        label=my_label['Home'],
                        lw = 10)
            my_label['Home'] = "_nolegend_"
            
        ############################################# Format goals axis so that only round integers are displayed
        max_goals = plays[[Away + " Goals",Home + " Goals"]].iloc[-1].max()
        y = [i for i in range(0,max_goals+2)]
        ax1.set_yticks(y)
   
        plt.ylabel('Goals')
        plt.title(f"{Away} @ {Home} - Shots & Goals")
        plt.legend(bbox_to_anchor=(0.17,.84))
        
        #######################################################################################################
        # 4                                                                                                   #
        #######################################################################################################
        
        ################################################################### Create 2nd Plot - Prior 5 min shots
        ax2 = fig.add_subplot(gs2[2,0])
        
        plt.title('Prior 5 Minutes - Shots')
        
        ############################################# Plot prior 5 minutes shot data
        plt.plot(prior_5_shots.index, prior_5_shots[Away + " Shots - Prior 5 min"],
                 c=Away_Color,
                 linestyle='dotted',
                 lw=6,
                 label=Away + " Shots - Prior 5 min")
        
        plt.plot(prior_5_shots.index,
                 prior_5_shots[Home + " Shots - Prior 5 min"],
                 c=Home_Color,
                 linestyle='dotted',
                 lw=6,
                 label=Home + " Shots - Prior 5 min")
        
        #Fill between bars marking penalty kill/power play - Test
        ######################################################################
        for h in HomePens:
            ax2.axvspan(h[0]*60, h[1]*60, alpha=0.5, color=Away_Color)
        for a in AwayPens:
            ax2.axvspan(a[0]*60, a[1]*60, alpha=0.5, color=Home_Color)
        ######################################################################
        
        plt.ylabel('Shots on Goal')
        plt.legend(bbox_to_anchor=(1,1.27))
        
        ############################################# Add vertical bars to graph to mark end of periods.
        r, x = PeriodLines(ax2, OT)
        
        plt.text(0,-3,'*Shaded areas represent \n powerplays for each team', fontsize=18)
        plt.grid(b=True, axis='x',color='grey')
        #######################################################################################################
        # 5                                                                                                   #
        #######################################################################################################
        
        ###################################################################### Add hits - prior 5 mins to third axis object
        ax3 = fig.add_subplot(gs2[3,0])
        
        plt.title('Prior 5 Minutes - Hits')
        
        ############################################# Plot prior 5 min. hits data
        plt.plot(prior_5_hits.index,
                 prior_5_hits[Away + " Hits - Prior 5 min"],
                 c=Away_Color,
                 linestyle=(0, (1, 2)),
                 lw=6,
                 label=Away + " Hits - Prior 5 min")
        
        plt.plot(prior_5_hits.index,
                 prior_5_hits[Home + " Hits - Prior 5 min"],
                 c=Home_Color,
                 linestyle=(0, (1, 2)),
                 lw=6,
                 label=Home + " Hits - Prior 5 min")
        
        #Fill between bars marking penalty kill/power play - Test
        ######################################################################
        for h in HomePens:
            ax3.axvspan(h[0]*60, h[1]*60, alpha=0.5, color=Away_Color)
        for a in AwayPens:
            ax3.axvspan(a[0]*60, a[1]*60, alpha=0.5, color=Home_Color)
        ######################################################################
        
        plt.legend(bbox_to_anchor=(1,1.27))
        
        ############################################# Add vertical bars to graph to mark end of periods.
        r, x = PeriodLines(ax3, OT)
        
        ############################################# Add axis labels and fontsizes    
        plt.ylabel('Hits')
        plt.grid(b=True, axis='x',color='grey')
        plt.text(0,-3,'u/AvsStats', fontsize=20)        
        #######################################################################################################
        # 6                                                                                                   #
        #######################################################################################################
        
        ###################################################################### Update frame size and save fig
        
        if save == True:
            filePath ="C:\\Users\\grega\\Google Drive\\Python\\NHLstats\\Live NHL Stats\\" + f"{gameday} {Away} @ {Home}\\" + "Game Plots.png"
            # First remove the file if it already exists
            if os.path.exists(filePath) == True:
                os.remove(filePath)
            
            # Determine if a new file directory needs to be made
            try:
                os.mkdir("C:\\Users\\grega\\Google Drive\\Python\\NHLstats\\Live NHL Stats\\" + f"{gameday} {Away} @ {Home}")
            except:
                print('Directory Already Exists')
                
            # Save figure
            plt.savefig(filePath,dpi=1040,bbox_inches= 'tight', pad_inches=.5)
        
        self.GPlot = fig
        
class GameMap():
    
    def __init__(self, game_id):

        pd.set_option('mode.chained_assignment', None)

        self.game_id = game_id
        
        self.plays = pd.DataFrame(list_plays(game_id))
        self.shots = pd.DataFrame(list_shots(game_id))
        self.shift = pd.DataFrame(list_shifts(game_id))
                
        self.gameDay = pd.to_datetime(self.plays['datetime']).iloc[0].date() 
        self.Teams = pd.DataFrame(list_games(str(self.gameDay + dt.timedelta(days=-1)), str(self.gameDay)))
        self.Teams = self.Teams[self.Teams.game_id == game_id]
        
        self.Home = self.Teams.home_team.iloc[0]
        self.Away = self.Teams.away_team.iloc[0]
        
        # Define team name references
        tL = pd.read_csv('teamList.csv') # store as csv file in GH?

        self.HomeAbrv = tL[tL.team_name == self.Home].team_abbrv.max()    
        self.AwayAbrv = tL[tL.team_name == self.Away].team_abbrv.max()
    
        self.Home_Color1 = tL[tL.team_abbrv == self.HomeAbrv].home_c.max()
        self.Home_Color2 = tL[tL.team_abbrv == self.HomeAbrv].away_c.max()
    
        self.Away_Color1 = tL[tL.team_abbrv == self.AwayAbrv].away_c.max()    
        self.Away_Color2 = tL[tL.team_abbrv == self.AwayAbrv].home_c.max() 
        
    def XY_SnG(self):
        shots = self.shots
        Home = self.HomeAbrv
        Away = self.AwayAbrv
        
        def IndexToMarker(index):
            return f"${index}$"
        
        # Refine `shots` DF columns
        cols = ['event_type','team_for','x','y','period']
        XY = shots[cols]
    
        # Odd logic problem where adjustments for direction of attack is not consistent across all home teams
        # Need to test with more games to determine formula to automate process of making x,y adjustments
    
        # Standardize direction of play/attack for each team
        XY.loc[(XY.team_for == Home), 'x'] = -1 * abs(XY['x'])
        XY.loc[(XY.team_for == Away), 'x'] = abs(XY['x'])
        
        #XY.loc[(XY.team_for == Away) & ((XY.period == 1) | (XY.period == 3)), 'y'] = -1 * XY['y']
        XY.loc[((XY.period == 2)), 'y'] = -1 * XY['y']
        
        # Seperate out each team's shots and goals
        XYhome = XY[(XY.team_for == Home)]
        XYhomeS = XYhome[XYhome.event_type == 'SHOT']
        XYhomeSA = XY[((XY.team_for == Home) & (XY.event_type == 'MISSED_SHOT')) | ((XY.team_for == Away) & (XY.event_type == 'BLOCKED_SHOT'))]
        XYhomeSA.loc[:,'x'] = -1 * abs(XYhomeSA['x'])
        XYhomeG = XYhome[XYhome.event_type == 'GOAL']
    
        XYaway = XY[(XY.team_for == Away)]
        XYawayS = XYaway[XYaway.event_type == 'SHOT']
        XYawaySA = XY[((XY.team_for == Away) & (XY.event_type == 'MISSED_SHOT')) | ((XY.team_for == Home) & (XY.event_type == 'BLOCKED_SHOT'))]     
        XYawaySA.loc[:,'x'] = abs(XYawaySA['x'])
        XYawayG = XYaway[XYaway.event_type == 'GOAL']
        XYhomeSA.loc[:,'x'] = -1 * abs(XYhomeSA['x'])
        # Reset index of goals df's to match goal # within this game
        XYhomeG.index = np.arange(1,len(XYhomeG)+1)
    
        XYhomeG['MarkerStyle'] = XYhomeG.index.copy(dtype='int64')
        XYhomeG['MarkerStyle'] = XYhomeG.apply(lambda x: IndexToMarker(x['MarkerStyle']),axis=1)
    
        XYawayG.index = np.arange(1,len(XYawayG)+1)
    
        XYawayG['MarkerStyle'] = XYawayG.index.copy(dtype='int64')
        XYawayG['MarkerStyle'] = XYawayG.apply(lambda x: IndexToMarker(x['MarkerStyle']),axis=1)
        
        self.HomeG = XYhomeG
        self.HomeS = XYhomeS
        self.HomeSA = XYhomeSA
        
        self.AwayG = XYawayG
        self.AwayS = XYawayS
        self.AwaySA = XYawaySA
        
    def XY_Plays(self):
        plays = self.plays
        Home = self.HomeAbrv
        Away = self.AwayAbrv
        
        hits = plays[plays.event_type == 'HIT'][['team_for','x','y']]
        take = plays[plays.event_type == 'TAKEAWAY'][['team_for','x','y']]
        give = plays[plays.event_type == 'GIVEAWAY'][['team_for','x','y']]
        face = plays[plays.event_type == 'FACEOFF'][['team_for','x','y']]
    
        XYhomeH = hits[hits.team_for == Home]           #x,y data for home team hits
        XYawayH = hits[hits.team_for == Away]           #x,y data for away team hits
    
        XYhomeT = take[take.team_for == Home]           #x,y data for home team takeaways
        XYawayT = take[take.team_for == Away]           #x,y data for away team takeaways
    
        XYhomeGA = give[give.team_for == Home]          #x,y data for home team giveaways
        XYawayGA = give[give.team_for == Away]          #x,y data for away team giveaways
    
        XYhomeF = face[face.team_for == Home]           #Faceoff win xy data
        XYawayF = face[face.team_for == Away]           #Faceoff win xy data - possibly useful for looking at draws likely to win/lose
        
        self.HomeH = XYhomeH
        self.HomeT = XYhomeT
        self.HomeGA = XYhomeGA
        self.HomeFO = XYhomeF
        
        self.AwayH = XYawayH
        self.AwayT = XYawayT
        self.AwayGA = XYawayGA
        self.AwayFO = XYawayF
        
    def Map(self, save=False, AltColor=[False, False], shots=True):
        Home = self.HomeAbrv
        # Determine which colors user wants (default to standard home/away colors for each team)
        if AltColor[0] == False:
            Home_Color = self.Home_Color1   # Use standard home color for the team
        else:
            Home_Color = self.Home_Color2   # Use the away color for the team (for better looking plots)
        
        Away = self.AwayAbrv
        # Determine which colors user wants (default to standard home/away colors for each team)
        if AltColor[1] == False:
            Away_Color = self.Away_Color1
        else:
            Away_Color = self.Away_Color2
            
        gameday = self.gameDay
            
        def mscatter(x,y, ax=None, m=None, **kw):
            ax = ax or plt.gca()
            sc = ax.scatter(x,y,**kw)
            if (m is not None) and (len(m)==len(x)):
                paths = []
                for marker in m:
                    if isinstance(marker, mmarkers.MarkerStyle):
                        marker_obj = marker
                    else:
                        marker_obj = mmarkers.MarkerStyle(marker)
                    path = marker_obj.get_path().transformed(
                                marker_obj.get_transform())
                    paths.append(path)
                sc.set_paths(paths)
            return sc  
        
        def CreatePatches(Home, Away, Home_Color, Away_Color):
            # Create the LHS House & Trapezoid
            poly1 = HouseNoffice(1)
            poly2 = HouseNoffice(2)
        
            # Create the RHS House & Trapezoid
            poly3 = HouseNoffice(3)
            poly4 = HouseNoffice(4)
        
            polys = [poly1, poly2, poly3, poly4]
        
        
            circ1 = FOcircle(1)           # LHS top faceoff circle
            circ2 = FOcircle(2)           # LHS bottom faceoff circle
            circ3 = FOcircle(3)           # Center Ice Circle
            circ4 = FOcircle(4)           # RHS top faceoff circle
            circ5 = FOcircle(5)           # RHS bottom faceoff circle
        
            circles = [circ1, circ2, circ3, circ4, circ5]
        
        
            arrow1 = FancyArrow(Home, Home, Away, Home_Color, Away_Color)               # Home team arrow
            arrow2  = FancyArrow(Away, Home, Away, Home_Color, Away_Color)              # Away team arrow
        
            return polys + circles + [arrow1, arrow2]
        
        def VLines():
            plt.axvline(x=-89,c='r',lw=2)       # Add first goal line
            plt.axvline(x=-25,c='b',lw=6)       # Add first blue line
            plt.axvline(x=0,c='r',lw=6)         # Add red line
            plt.axvline(x=25,c='b',lw=6)        # Add second blue line
            plt.axvline(x=89,c='r', lw=2)       # Add second goal line
        
        def Lcrease():                          # Add LHS goalie crease 
            arc1 = patches.Arc((-84.5,0), 8,7.8,theta1=-90,theta2=90, edgecolor='b')   
            rect1 = plt.Rectangle((-89-(40/12),-3), 40/12, 6, color='k', alpha = 0.5)
            plt.axhline(y=3.95,xmin=(11/200),xmax=(15.5/200), c='b', lw=1)
            plt.axhline(y=-3.8,xmin=(11/200),xmax=(15.5/200), c='b', lw=1)
            
            return arc1, rect1
        
        def Rcrease():                          # Add RHS goalie crease 
            arc2 = patches.Arc((84.5,0), 8,7.8,theta1=90,theta2=-90, edgecolor='b')   
            rect2 = plt.Rectangle((89,-3), 40/12, 6, color='k', alpha = 0.5)
            plt.axhline(y=3.95,xmin=(184.5/200),xmax=(189/200), c='b', lw=1)
            plt.axhline(y=-3.8,xmin=(184.5/200),xmax=(189/200), c='b', lw=1)
        
            return arc2, rect2
        
        def HouseNoffice(item):
            if item == 1:                       # Add LHS "House"
                poly = plt.Polygon([[-89,-4],[-69,-22],[-54,-22],[-54,22],[-69,22],[-89,4]], color='black',fill=False,lw=3,ls='dotted')
            
            elif item == 2:                     # Add LHS "Office"
                poly = plt.Polygon([[-100,14],[-100,-14],[-89,-9],[-89,9]], color='r',fill=False, lw = 1)
        
            elif item == 3:                     # Add RHS "House"
                poly = plt.Polygon([[89,-4],[69,-22],[54,-22],[54,22],[69,22],[89,4]], color='black',fill=False, lw=3,ls='dotted')
            
            elif item == 4:                     # Add RHS "Office"
                poly = plt.Polygon([[100,14],[100,-14],[89,-9],[89,9]], color='r',fill=False, lw = 1)        
        
            return poly
        
        def FOcircle(item):
            if item == 1:                       # LHS top faceoff circle
                circ = plt.Circle((-69,22), 15, ec='r',fill=False, lw=2)   
        
            elif item == 2:                     # LHS bottom faceoff circle
                circ = plt.Circle((-69,-22), 15, ec='r',fill=False, lw=2)
        
            elif item == 3:                     # Center ice faceoff circle
                circ = plt.Circle((0,0), 15, ec='r', fill=False, lw=2)
            
            elif item == 4:                     # RHS top faceoff circle 
                circ = plt.Circle((69,22), 15, ec='r',fill=False, lw=2)       
        
            elif item == 5:                     # RHS bottom faceoff circle   
                circ = plt.Circle((69,-22), 15, ec='r',fill=False, lw=2) 
        
            return circ
            
        def FancyArrow(team, Home, Away, Home_Color, Away_Color):
            
            if team == Home:                    # Home team fancy arrow
                arrow = patches.FancyArrowPatch((100,-50), 
                                                (-100,-50), 
                                                mutation_scale=100, 
                                                clip_on=False, 
                                                color=Home_Color, 
                                                label=(f"{Home} Attacks"))
                
            elif team == Away:                  # Away team fancy arrow
                arrow = patches.FancyArrowPatch((-100,-60), 
                                                (100,-60), 
                                                mutation_scale=100, 
                                                clip_on=False, 
                                                color=Away_Color, 
                                                label=(f"{Away} Attacks"))     
            return arrow
        
        fig = plt.figure(figsize=(22,0.425*22))
        ax = fig.add_subplot(1,1,1)
        ax.set_ylim(-42.5,42.5)
        ax.set_xlim(-100,100)
        
        ########################################################################## Format plot to overlay ice rink
        VLines()                      # Red and Blue line markers
        arc1, rect1 = Lcrease()       # Create LHS goalie crease 
        arc2, rect2 = Rcrease()       # Create RHS goalie crease 
        
        # Add RHS/LHS goalie crease's to frame
        creases = [arc1, rect1, arc2, rect2]
        
        for crease in creases:
            ax.add_patch(crease)
        
        mypatches = CreatePatches(Home, Away, Home_Color, Away_Color)
        
        for patch in mypatches:
            ax.add_patch(patch)
        
        ax.annotate(f"{Home} Attacks",xy=(0,-0.1),xycoords='axes fraction', xytext=(.45, -0.15), fontsize=20) 
        ax.annotate(f"{Away} Attacks",xy=(0,-0.1),xycoords='axes fraction', xytext=(.45, -0.275), fontsize=20) 
        
        if shots == True:
            DFtoPlot = [self.HomeS, self.HomeSA, self.HomeG, self.AwayS, self.AwaySA, self.AwayG]
            Legend = (Home + ' Shots', Away + ' Shots', Home + ' Attempts', Away + ' Attempts', Home + ' Goals', Away + ' Goals')
            
            sizes = [100,200,1250]
            marker = ['o', 'X', list(DFtoPlot[2]['MarkerStyle']), list(DFtoPlot[5]['MarkerStyle'])]
            
            Title = "Shots & Goals"
            anchor= (0.445,1.15)
            
        else:
            DFtoPlot = [self.HomeH, self.HomeT, self.HomeGA, self.AwayH, self.AwayT, self.AwayGA]
            Legend = (Home + ' Hit', Away + ' Hit', Home + ' Takeaway', Away + ' Takeaway', Home + ' Giveaway', Away + ' Giveaway')
            
            sizes = [150,150,150]
            marker = ['s', '^', 'o', 'o']
            
            Title = "Hits, TA's, GA's"
            anchor= (0.46,1.15)
        
        ########################################################################## Plot Data
        if len(DFtoPlot[0]) > 0:
            a= mscatter(DFtoPlot[0]['x'],DFtoPlot[0]['y'],color=Home_Color, s=sizes[0], marker=marker[0])        #Scatter plot of home team shots OR hits
        else:
            a= None
        
        if len(DFtoPlot[1]) > 0:
            b= mscatter(DFtoPlot[1]['x'],DFtoPlot[1]['y'],color=Home_Color,s=sizes[1], marker=marker[1])         #Scatter plot of home team shot attempts OR takeaways
        else:
            b= None
            
        if len(DFtoPlot[2]) > 0:
            c= mscatter(DFtoPlot[2]['x'],DFtoPlot[2]['y'],color=Home_Color,s=sizes[2], m=marker[2])     #Scatter plot of home team goals OR giveaways
        else:
            c= None
        
        
        if len(DFtoPlot[3]) > 0:
            d= mscatter(DFtoPlot[3]['x'],DFtoPlot[3]['y'],color=Away_Color, s=sizes[0], marker=marker[0])        #Scatter plot of away team shots OR hits
        else:
            d= None
            
        if len(DFtoPlot[5]) > 0:
            e= mscatter(DFtoPlot[4]['x'],DFtoPlot[4]['y'],color=Away_Color,s=sizes[1], marker=marker[1])         #Scatter plot of away team shot attempts OR takeaways
        else:
            e= None
        
        if len(DFtoPlot[5]) > 0:
            f= mscatter(DFtoPlot[5]['x'],DFtoPlot[5]['y'],color=Away_Color,s=sizes[2], m=marker[3])     #Scatter plot of away team goals OR giveaways
        else:
            f= None
        ##########################################################################
        mpl.rc('axes', titlesize=30)                           #fontsize of the axes title
        plt.title(f"{Away} @ {Home} | {Title}", loc='right',)
        plt.legend((a,d,b,e,c,f), Legend, scatterpoints=1, ncol=3, \
                   fontsize=22, bbox_to_anchor=anchor, markerscale=1.1, \
                   borderpad=0.2, handletextpad=.1, columnspacing=1)
            
        ax.set_xticks([])
        ax.set_yticks([])
        
        if save == True:
            filePath ="C:\\Users\\grega\\Google Drive\\Python\\NHLstats\\Live NHL Stats\\" + f"{gameday} {Away} @ {Home}\\" + f"{Title} Map.png"
            # First remove the file if it already exists
            if os.path.exists(filePath) == True:
                os.remove(filePath)
            
            # Determine if a new file directory needs to be made
            try:
                os.mkdir("C:\\Users\\grega\\Google Drive\\Python\\NHLstats\\Live NHL Stats\\" + f"{gameday} {Away} @ {Home}")
            except:
                print('Directory Already Exists')
                
            # Save figure
            plt.savefig(filePath,dpi=1040,bbox_inches= 'tight', pad_inches=.5)
        
        #plt.show()
        self.Map = fig