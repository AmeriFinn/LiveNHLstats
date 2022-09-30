# -*- coding: utf-8 -*-
"""
Summarize each game played on a certain day.
Created on Sun Nov 21 21:05:15 2021

@author: grega
"""
#%% Import the necessary modules from nhlstats
from FigureFrames import FigureFrames
from GameStats import GameStats
from GameScatter import GameScatter
from StatsTables import StatsTables
from PuckPlot import PuckPlot
from TeamStats import TeamStats
from DataPanePost import DataPane
from nhlstats import list_games

# Import the necessary standard modules
import pandas as pd
import datetime as dt
from datetime import datetime as dt
import time
import os

# Import the necessary plotly modules
from plotly.offline import plot
import plotly.graph_objects as go
from PIL import ImageColor as IC  # For converting hex color codes to RGB codes

# Adjust some pandas display options for when I'm working in this individual script
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 12)
pd.set_option('display.width', 1500)

# Define a function for converting Hex color codes into RGB codes that can be processed by plotly
def my_Hex_to_RGBA(Hex, opacity = 0.5):
    tup = IC.getcolor(Hex, 'RGB') + tuple([0.5])
    tup_str = f'rgba({tup[0]}, {tup[1]}, {tup[2]}, {str(opacity)})'
    return tup_str

#%%
class NightRecap:
    
    #%%
    def __init__(self, GameDay, template='plotly_white', publish=False):
        self.GameDay  = GameDay
        self.template = template
        self.publish  = publish
        self.txtColor = '#FFFFFF' if template == 'plotly_dark' else '#000000'
        
        # Collect games played on the given date
        Games_df = pd.DataFrame(
            list_games(GameDay, GameDay)
        )
        Games_df = Games_df[~Games_df.game_state.isin(['Postponed', 'Scheduled', 'Pre-Game'])]
        GamesN = Games_df.shape[0]
        
        # Collect the team abbreviations and colors, and direction of attack for the relevant arena
        # Collect team info provided in teamList.csv file in my github repo.
        tLUrl = 'https://raw.githubusercontent.com/AmeriFinn/LiveNHLstats/master/teamList.csv'
        tL = pd.read_csv(tLUrl, index_col=0)
        
        self.Games_df = Games_df
        self.GamesN   = GamesN
        self.tL       = tL
        
    #%%
    def Recap(self):
        GameDay  = self.GameDay
        template = self.template
        txtColor = self.txtColor
        Games_df = self.Games_df
        GamesN   = self.GamesN
        tL       = self.tL
        
        #%% Create a list of relevant subplot names to be used,
        # and also collect the necessary game stats for each game
        GameTeams  = []
        GameTitles = []
        GameData   = []
        TeamData   = []
        GameColors = []
        for row in Games_df.index:
            # Collect the home and away team names
            Home    = Games_df.loc[row, 'home_team']
            Away    = Games_df.loc[row, 'away_team']
            game_id = Games_df.loc[row, 'game_id']
            print(f'{Away} @ {Home}\t| {game_id}')
            
            # Determine the Home and Away colors to be used
            HCol = tL[tL.team_name == Home]['home_c'].values[0]
            ACol = tL[tL.team_name == Away]['away_c'].values[0]
            GameTeams.append([Home, Away])
            GameColors.append([HCol, ACol])
            
            ## Create the subplot titles
            # Start with the team names
            AwayStr = f'<b><span style="color: {ACol}">{Away}</span></b>'
            HomeStr = f'<b><span style="color: {HCol}">{Home}</span></b>'
            Title1  = f'{AwayStr} <b>@</b> {HomeStr}'
            GameTitles.append(Title1)
            
            # Then create the relevant links to place aboce the table
            GameCenter = f'https://www.nhl.com/gamecenter/{game_id}'
            Link1      = f'<a href="{GameCenter}">NHL GameCenter</a>'
            GameCenter += f'#game={game_id},game_state=final'
            Link2      = f'<a href="{GameCenter}">Recap & Highlights</a>'
            Title2     = f'{Link1}  |  {Link2}'
            GameTitles.append(Title2)
            
            # Then create the momentum plot title
            GameTitles.append("Net Momentum")
            
            # Finally add the sunburst plots
            GameTitles.append('Points by Player')
            GameTitles.append('GSA by Player')
            
            # Collect the game stats
            gs = GameStats(game_id)
            gs.All()
            GameData.append(gs)
            
            # Collect the team stats for the game
            ts = TeamStats
            ts.Summarize_Game(ts, game_id, gs)
            points = ts.PuckPlot_Points(gs)
            TeamData.append(points)
        
        # Create the figure for the nightly recap
        fig = FigureFrames.NightRecapFigure(
            GameDay, GamesN, GameTitles, txtColor, template
        )
        
        #%% Iterate over each game to add the momentum plot on the left and summary stats table on
        # the right of each games plot area
        row = 1
        for gs, colors, points in zip(GameData, GameColors, TeamData):
            HCol = colors[0]
            ACol = colors[1]
            
            # Add the GSA Game Scatter plot
            GScatter = GameScatter(gs, fig, 1, 1, 1, HCol, ACol, txtColor)
            GScatter.GSAscatter(row, showlegend=False)
            
            # Add the summary stats table
            ST  = StatsTables(gs, fig, row, 2, HCol, ACol)
            fig = ST.SumStats()
            
            # Add the momentum plot
            GScatter.Momentum(row + 1, 1)
            
            ## Add the relevant Puck Plots
            # Create and add the POINTS puck plot
            fig = PuckPlot(gs, fig, row + 1, 2, 'POINTS', HCol, ACol, points, Both = False)
            
            # Add the goals, shots, attempts puck plot
            fig = PuckPlot(gs, fig, row + 1, 3, 'GSA', HCol, ACol, Both = False)
            
            row += 2
        
        # Update the GameDay string format
        GameDay = dt.strptime(GameDay, '%Y-%m-%d').strftime('%d-%b-%y')
        
        # Publish the figure if desired, otherwise display it in the users web browser
        if self.publish:
            # Publish the report to DataPane
            DP = DataPane()
            DP.Night(GameDay, fig)
        else:
            plot(fig)
        
        self.fig = fig
        #%% Save the figures locally
        save_path = os.path.join(
            os.getcwd(), 'HTML Outputs', 'Night Recaps'
        )
        
        # Create the local directories if necessary
        if not os.path.exists(os.path.join(os.getcwd(), 'HTML Outputs')):
            os.mkdir(os.path.join(os.getcwd(), 'HTML Outputs'))
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        
        # Save the figure
        fig.write_html(
            os.path.join(
                save_path,
                f'{GameDay}_Recap.html'
            )
        )
        
    def GoalsAndMomentum(fig, row, col, gs, HCol, ACol, txtColor):
        
        goals = gs.Goals
        Home  = gs.HomeAbrv
        Away  = gs.AwayAbrv
        
        # On the second y-axis, add vertical bars denoting goals for each team
        for team, color, index in zip([Home, Away], [HCol, ACol], [0, 1]):
            
            # Replace instances where a game goes to OT causing a period value greater
            # than 3 appears in the goals df
            goals[index]['period'] = goals[index].period.apply(
                lambda x: str(int(x)) if str(x) != 'nan' else 'OT'
            )
            
            # Add goal bars
            for i in range(goals[index].shape[0]):
                
                # The nth goal provided in the Goals df
                goal_n  = goals[index][f"{team} Goals"].iloc[i]
                # The time the nth goal was scored
                g_time    = goals[index].index[i]
                # g_time_dt = dt.strptime(g_time, '%H:%M:%S').strftime('%H:%M:%S')
                # print(g_time, type(g_time))
                # print(g_time_dt, type(g_time_dt))
                
                # Collect time of goal scored and  player references for the goal
                cols = ['period', 'period_time', 'player_1', 'player_2', 'player_3', 'player_4']
                # Drop player_3 and/or player_4 columns if no goal was scored
                # with an assist or secondary assit.
                cols = [c for c in cols if c in goals[index].columns]
                
                # Use a conditional statement to handle shootout goals which are
                # recorded with the same `time` value in the NHL stats API
                if type(goals[index].loc[g_time, cols]) == pd.core.series.Series:
                    
                    if len(cols) == 4:
                        period, time, player1, player2 = goals[index].loc[g_time, cols]
                        player3, player4 = None, None
                    elif len(cols) == 5:
                        period, time, player1, player2, player3 = goals[index].loc[g_time, cols]
                        player4 = None
                    else:
                        period, time, player1, player2, player3, player4 = goals[index].loc[g_time, cols]
                    
                    # If goal was un-assited, player2 is the goalie & should be swapped with player4
                    if (player3 == player4) & (player4 in ['', None]):
                        player2, player4 = player4, player2
                    # If goal only had one assit, player3 needs to be swapped with player 4
                    elif (player4 in ['', None]) & (player3 not in ['', None]):
                        player3, player4 = player4, player3
                    
                    # Set a variable to be used to flip away team goals to the second quadrant
                    if index == 0:
                        y_bar = [0, goal_n]
                    else:
                        y_bar = [-goal_n, 0]
                    
                    bar = go.Scatter(x          = [time, time],
                                     y          = y_bar,
                                     hovertemplate = f'<b>Goal #: {goal_n}<b><br>' +
                                     f'Period: {period}<br>' +
                                     f'Time: {time}<br><br>' +
                                     f'Scored By: {player1}<br>' +
                                     f'Assit*: {player2}<br>' +
                                     f'Assit**: {player3}<br>' +
                                     f'Goalie: {player4}<br>'
                                     '<extra></extra>',
                                     mode       = 'lines',
                                     showlegend = False,
                                     name       = f"{team} Goal",
                                     line       = dict(color=my_Hex_to_RGBA(color),
                                                       dash='solid',
                                                       width=7.5))
                    fig.add_trace(bar, secondary_y=True, row = row, col = col)
                
                else:
                    # Handle the shootout goals
                    for j in range(goals[index].loc[g_time, cols].shape[0]):
                        
                        goal_n = goal_n + 1 if j > 0 else goal_n
                        
                        if len(cols) == 4:
                            period, time, player1, player2 = \
                                goals[index].loc[g_time, cols].iloc[j]
                            player3, player4 = None, None
                        elif len(cols) == 5:
                            period, time, player1, player2, player3 = \
                                goals[index].loc[g_time, cols].iloc[j]
                            player4 = None
                        else:
                            period, time, player1, player2, player3, player4 = \
                                goals[index].loc[g_time, cols].iloc[j]
                        
                        # If goal was un-assited, player2 is the goalie & should be swapped with player4
                        #player2, player4 = player4, player2 if player3 == player4 else player2, player4
                        if (player3 == player4) & (player4 in ['', None]):
                            player2, player4 = player4, player2
                        # If goal only had one assit, player3 needs to be swapped with player 4
                        #, player4 = player4, player3 if player4 is None else player3, player4
                        elif (player4 in ['', None]) & (player3 not in ['', None]):
                            player3, player4 = player4, player3
                        
                        # Set a variable to be used to flip away team goals to the second quadrant
                        if index == 0:
                            y_bar = [0, goal_n]
                        else:
                            y_bar = [-goal_n, 0]
                        
                        bar = go.Scatter(x          = [g_time, g_time],
                                         y          = y_bar,
                                         hovertemplate = f'<b>Goal #: {goal_n}<b><br>' +
                                         f'Period: {period}<br>' +
                                         f'Time: {time}<br><br>' +
                                         f'Scored By: {player1}<br>' +
                                         f'Assit*: {player2}<br>' +
                                         f'Assit**: {player3}<br>' +
                                         f'Goalie: {player4}<br>'
                                         '<extra></extra>',
                                         mode       = 'lines',
                                         showlegend = False,
                                         name       = f"{team} Goal",
                                         line       = dict(color=my_Hex_to_RGBA(color),
                                                           dash='solid',
                                                           width=7.5))
                        fig.add_trace(bar, secondary_y=True, row = row, col = col)
        
        fig.update_xaxes(title_text = "Game Time Elapsed",
                          titlefont  = dict(size=18),
                          tickfont   = dict(size=18),
                          showgrid   = False,
                          row        = row,
                          col        = col,
                          tickvals   = ["00:00:00"] +
                                      [f"00:{m}:00" for m in range(10, 65, 10)] +
                                      ["01:00:00"])
        
        # Set y-axes titles
        ## Left side
        fig.update_yaxes(title_text  = "Net Momentum",
                          secondary_y = False,
                          zeroline    = False,
                          row         = row,
                          col         = col)
        ## Right side
        height = goals[4] + 1
        ntick = height if height < 10 else int(height / 2)
        
        fig.update_yaxes(title_text    = "Goals",
                         secondary_y   = True,
                         row           = row,
                         col           = col,
                         showgrid      = False,
                         zeroline      = False,
                         nticks        = ntick,
                         range         = (-height, height))
        
        return fig
        
#%%
# GameDay = '2021-12-02'
# nr = NightRecap(GameDay, publish=True)
# nr.Recap()
