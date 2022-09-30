# -*- coding: utf-8 -*-
"""
Created on Thu Dec  2 22:12:42 2021

@author: grega
"""
# Import the necessary modules
from GameStats import GameStats
from FigureFrames import FigureFrames
from nhlstats import list_games

import pandas as pd
import datetime as dt
import os

# Import requests library to ping the NHL API directly
import requests

# Adjust some pandas display options for when I'm working in this individual script
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 15)
pd.set_option('display.width', 1500)

class NHLstandings:
    
    def __init__(self, on_date):
        
        self.on_date = on_date
        
        # Ping the NHL API for the standings info
        standings_link = f'https://statsapi.web.nhl.com/api/v1/standings?expand=standings.record&date={on_date}'
        r = requests.get(standings_link)
        
        # Collect the master records list and assign as class attribute
        api_standings = r.json()['records']
        self.raw_standings = api_standings
        
        # Read in standard tL
        tLUrl = 'https://raw.githubusercontent.com/AmeriFinn/LiveNHLstats/master/teamList.csv'
        tL = pd.read_csv(tLUrl, index_col=0)
        self.tL = tL
        
    def Full_to_Abbrv(self, tL, team):
        return tL.loc[tL.team_name == team, 'team_abbrv'].values[0]
    
    def collect(self):
        
        tL = self.tL
        
        # Collect raw standings and define storage list of cleaned standings
        standings = self.raw_standings
        all_divisions = list()
        
        # Iterate over the standings for each division to break up the json list of dictionaries
        for i in standings:
            
            # Create a storage dictionary
            stor = dict()
            x = 0
            
            # First collect relevant info on the division being scraped
            division = i['division']['nameShort'][:3].upper()
            conference = i['conference']['name'][:4]
            
            # Then collect the team records for the whole division
            records = i['teamRecords']
            
            ## TODO
            ## Move this to its own function/class/script
            # Iterate over the list that is returned to collect individual team records
            for rec in records:
                
                stor_lst = []
                
                # Collect standard team stats (wins, losses, OTL, points, etc.)
                team = self.Full_to_Abbrv(tL, rec['team']['name'])
                gp   = rec['gamesPlayed']
                pnts = rec['points']
                wins = rec['leagueRecord']['wins']
                loss = rec['leagueRecord']['losses']
                otl  = rec['leagueRecord']['ot']
                row  = rec['row']
                for e in [team, conference, division, gp, pnts, wins, loss, otl, row]:
                    stor_lst.append(e)
                
                # Collect the teams division, conference, and league wide rankings
                divRank = int(rec['divisionRank'])
                conRank = int(rec['conferenceRank'])
                legRank = int(rec['leagueRank'])
                wcdRank = int(rec['wildCardRank'])
                streak  = rec['streak']['streakCode']
                for e in [divRank, conRank, legRank, wcdRank, streak]:
                    stor_lst.append(e)
                
                # Collect each teams record against the divisions
                for div in rec['records']['divisionRecords']:
                    divWin = div['wins']
                    divLos = div['losses']
                    divOtl = div['ot']
                    divTyp = div['type']
                    record = f'{divWin}-{divLos}-{divOtl}'
                    
                    if divTyp[:1] == 'P':
                        pacRec = record
                    elif divTyp[:1] == 'C':
                        cenRec = record
                    elif divTyp[:1] == 'M':
                        metRec = record
                    elif divTyp[:1] == 'A':
                        atlRec = record
                    
                for e in [pacRec, cenRec, metRec, atlRec]:
                    stor_lst.append(e)
                
                # Append the team specific data to the storage dictionary
                stor[x] = stor_lst
                x += 1
                
            # Create a dataframe of the division specific data
            df = pd.DataFrame(stor).T
            cols = [
                'Team', 'Conference', 'Division', 'GP', 'Points', 'Wins', 'Losses', 'OTL',
                'ROW', 'Division_Rank', 'Conference_Rank', 'League_Rank', 'Wildcard_Rank',
                'Streak', 'PAC\n(W-L-O)', 'CEN\n(W-L-O)', 'MET (W-L-O)', 'ATL (W-L-O)'
            ]
            df.columns = cols
            
            # Store the dataframe in the master storage list
            all_divisions.append(df)
            
        league_wide = pd.concat(all_divisions)
        league_wide.sort_values(['League_Rank'], ascending = True, inplace = True)
        league_wide.reset_index(inplace = True, drop = True)
        
        return league_wide
    
    def team_record(self, team_abbrv):
        
        league_wide = self.collect()
        team_record = league_wide[league_wide.Team == team_abbrv.upper()]
        tr = team_record[['Wins', 'Losses', 'OTL', 'Points']]
        return f"{tr['Wins'].values[0]}-{tr['Losses'].values[0]}-{tr['OTL'].values[0]} ({tr['Points'].values[0]} PTS)"

# from plotly.offline import plot
# import datapane as dp

# token = os.environ.get("DataPane Token")
# dp.login(token)

# Define inputs
# team_abbrv = 'COL'
# to_date = False
# on_date = '2022-05-31'
# # end = dt.date.today() if to_date else end

# ns = NHLstandings(on_date)
# league_wide = ns.collect()
# tr = ns.team_record(team_abbrv)
# tr

# ns.team_record(team_abbrv)

# df = league_wide.copy()


# cols = ['GP', 'Wins', 'Losses', 'OTL', 'ROW', 'Points']
# df[cols] = df[cols].astype(int)
# df = df.style.background_gradient(cmap='viridis').set_sticky(axis="index")


# dp.enable_logging()
# page1 = dp.Page(
#     title = 'Leauge Standings',
#     blocks = ['### WORK IN PROGRESS', df]
# )
# r = dp.Report(
#     page1
# )

# r.upload(
#     name = 'table test',
#     visibility = "PRIVATE"
# )
   