# -*- coding: utf-8 -*-
"""
Will create scatter/line plots which summarize game stats throughout an individual game.
The goal is for the resulting figure that is created can be plugged directly into a
plotly subplots frame.

Created on Sun Aug  8 13:21:24 2021

@author: grega
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from PIL import ImageColor as IC  # For converting hex color codes to RGB codes
import datetime as dt

# Define a function for converting Hex color codes into RGB codes that can be processed by plotly
def my_Hex_to_RGBA(Hex, opacity = 0.75):
    tup = IC.getcolor(Hex, 'RGB') + tuple([0.5])
    tup_str = f'rgba({tup[0]}, {tup[1]}, {tup[2]}, {str(opacity)})'
    return tup_str

class GameScatter:
    def __init__(self, gs, fig, row, col, legendgroup, HCol, ACol, txtColor):
        # Assign input variables as class attributes
        self.gs          = gs
        self.fig         = fig
        self.row         = row
        self.col         = col
        self.legendgroup = legendgroup  # TODO: Create plot specific legends with this
        self.HCol        = HCol
        self.ACol        = ACol
        self.txtColor    = txtColor
        
        # Collect relevant attributes of the gs class object
        # and assign as attributes of `GameScatter`
        self.Home  = gs.HomeAbrv
        self.Away  = gs.AwayAbrv
        self.plays = gs.plays
        self.goals = gs.Goals
        
    # Define function used to add vertical bars every 20 minutes
    # ------------------------------------------------------------------------
    # ------------------------------------
    def PeriodLines(
            self, fig, df, Home, Away, row, col, stat,
            secondary_y=False, rng = None
    ):
        
        if stat == 'Net_Momentum':
            # height = max(df[0][stat].max(), df[1][stat].max()) + 5
            # base   = min(df[0][stat].min(), df[1][stat].min()) - 5
            height = rng[1]
            base   = rng[0]
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
                             line       = dict(
                                 color = my_Hex_to_RGBA(self.txtColor, 0.35),
                                 dash  = 'dot',
                                 width = 3
                            )
                        )
            fig.add_trace(bar, secondary_y=secondary_y, row = row, col = col)
        
        return fig
        
    # Define function to shade the Prior 5 to mark power plays
    # ------------------------------------------------------------------------
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
                                 opacity    = 0.35)
                fig.add_trace(bar, secondary_y=False, row=row, col=col)
        
        return fig
    
    def GSAscatter(self, row=None, col=None, showlegend=True):
        
        # Collect the relevant attributes
        gs          = self.gs
        fig         = self.fig
        row         = self.row if row is None else row
        col         = self.col if col is None else col
        # row         = self.row
        # col         = self.col
        legendgroup = self.legendgroup
        HCol        = self.HCol
        ACol        = self.ACol
        Home        = self.Home  # Note: Home & Away are the abbreviations in this module
        Away        = self.Away
        plays       = self.plays
        goals       = self.goals
        
        # Create the Goals, Shots, & Shot Attempts plot
        # ------------------------------------------------------------------------
        # ------------------------------------
        # Add the Home team shots + shot attepts, and the away team shots + shot attempts
        myRow, myCol = row, col
        zipped = zip(
            [f'{Home} Shots', f'{Away} Shots', f'{Home} Shot Attempts', f'{Away} Shot Attempts'],
            [HCol, ACol] * 2,
            ['solid', 'solid', 'dash', 'dash']
        )
        
        for trace, color, line in zipped:
            plot = go.Scatter(
                x          = plays.Time,
                y          = plays[trace],
                mode       = 'lines',
                showlegend = showlegend,
                name       = trace,
                line       = dict(color = color, dash = line),
                # legendgroup = str(legendgroup)
            )
            
            fig.add_trace(plot, secondary_y=False, row = row, col = col)
        
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
                g_time = goals[index].index[i]
                
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
                        if (player3 == player4) & (player4 in ['', None]):
                            player2, player4 = player4, player2
                        # If goal only had one assit, player3 needs to be swapped with player 4
                        elif (player4 in ['', None]) & (player3 not in ['', None]):
                            player3, player4 = player4, player3
                        
                        bar = go.Scatter(x          = [g_time, g_time],
                                         y          = [0, goal_n],
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
        
        # Add the period lines to the Game Scatter plot and update the plot formats
        fig = GameScatter.PeriodLines(
            self, fig, goals, Home, Away, myRow, myCol, 'Goals', secondary_y=True
        )
        
        if showlegend:
            title = "Game Time Elapsed"
        else:
            title = None
        fig.update_xaxes(title_text = title,
                         titlefont  = dict(size=14),
                         tickfont   = dict(size=14),
                         showgrid   = False,
                         row        = myRow,
                         col        = myCol,
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
        height = goals[4] + 1
        ntick = height if height < 10 else int(height / 2)
        
        fig.update_yaxes(title_text    = "Goals",
                         secondary_y   = True,
                         row           = myRow,
                         col           = myCol,
                         showgrid      = False,
                         zeroline      = False,
                         nticks        = ntick,
                         range         = (0, height))
        
        self.fig = fig
        
    def Momentum(self, row=None, col=None):
        # Add the momentum plot
        # ------------------------------------------------------------------------
        # ------------------------------------
        
        # Collect the relevant attributes
        gs   = self.gs
        fig  = self.fig
        row  = self.row + 2 if row is None else row
        col  = self.col if col is None else col
        HCol = self.HCol
        ACol = self.ACol
        Home = self.Home  # Note: Home & Away are the abbreviations in this module
        Away = self.Away
        
        Mom  = gs.Momentum
        HMom = gs.HomeMomentum
        AMom = gs.AwayMomentum
        
        zipped = zip([HMom, AMom], [HCol, ACol], [Home, Away])
        
        # Add the net momentum traces
        for trace, color, team in zipped:
            plot = go.Scatter(x          = trace.index,
                              y          = trace.Net_Momentum,
                              name       = f'{team} Momentum',
                              fill       = 'tozeroy',
                              fillcolor  = my_Hex_to_RGBA(color),
                              opacity    = 0.5,
                              line       = dict(color=color),
                              showlegend = False)
            fig.add_trace(plot, secondary_y = False, row = row, col = col)
        
            # Add the moving avg traces
            # TODO
            # For some reason, I can only do this if I add the trace
            # to the second y-axis. I think this is because the primary
            # y-axis uses a fill method. Need to investigate further.
            plot = go.Scatter(x          = trace.index,
                              y          = trace[f'{team} 5Min MA'],
                              name       = f'{team} 5 Min. MA',
                              mode       = 'lines',
                              opacity    = 1 / 3,
                              line       = dict(color=color),
                              showlegend = False)
            fig.add_trace(plot, secondary_y = True, row = row, col = col)
        
        # Format the 2nd subplot
        # height = HMom.Net_Momentum.max()
        height = HMom[f'{Home} 5Min MA'].max()
        ntick  = int(height / 3) if height < 30 else int(height / 5)
        # base   = AMom.Net_Momentum.min()
        base   = AMom[f'{Away} 5Min MA'].min()
        upper_bound = max(height, abs(base)) + 10
        lower_bound = upper_bound * -1
        
        fig.update_yaxes(title_text    = "Net Momentum",
                         secondary_y   = False,
                         showgrid      = True,
                         gridcolor     = my_Hex_to_RGBA(self.txtColor, 0.25),
                         row           = row,
                         col           = col,
                         titlefont     = dict(size=22),
                         nticks        = ntick,
                         range         = (lower_bound, upper_bound),
                         zeroline      = False)
        
        fig.update_yaxes(title_text    = None,
                         secondary_y   = True,
                         showgrid      = False,
                         showticklabels = False,
                         row           = row,
                         col           = col,
                         nticks        = 0,
                         range         = (lower_bound, upper_bound),
                         zeroline      = False)
        
        # Set x-axis title
        fig.update_xaxes(title_text = "Game Time Elapsed",
                         titlefont  = dict(size=14),
                         tickfont   = dict(size=14),
                         showgrid   = False,
                         row        = row,
                         col        = col,
                         # range      = ["00:00:00", str(HMom.index[-1])],
                         tickvals   = ["00:00:00"] +
                         [f"00:{m}:00" for m in range(10, 65, 10)] +
                         ["01:00:00"])
        
        # Add period seperating lines to momentum subplot
        fig = GameScatter.PeriodLines(
            self, fig, [HMom, AMom], Home, Away, row, col,
            'Net_Momentum', rng = [lower_bound, upper_bound]
        )
        
        # Add a text annotation denoting which team has created the most momentum.
        # This will be the integral of the momentum line between the curve and y = 0.
        Mom_Sum = HMom.Net_Momentum.sum() + AMom.Net_Momentum.sum()
        
        if Mom_Sum >= -50:
            if Mom_Sum > 50:
                Mom_Note = f'Momentum Favors <b><span style="color: {HCol}">{Home}</span><br></b>' + \
                    f'by <b>{int(Mom_Sum):,}</b> Points'
            else:
                Mom_Note = 'Momentum Favors Neither Team<br>' + \
                    f'Sum of Net Momentum = <b>{str(int(Mom_Sum))}</b> Points'
            
            ann_y = upper_bound - 15
            
            # Determine the appropriate period to place the annotation
            p1Mom = HMom[HMom.index <= dt.time(0, 20, 0)].Net_Momentum
            p2Mom = HMom[(HMom.index >= dt.time(0, 20, 0)) & (HMom.index <= dt.time(0, 40, 0))].Net_Momentum
            p3Mom = HMom[(HMom.index >= dt.time(0, 40, 0)) & (HMom.index <= dt.time(1, 0, 0))].Net_Momentum
            
            # Take the period with min. amount of positive momentum
            minMomSum = min(p1Mom.sum(), p2Mom.sum(), p3Mom.sum())
            # Take the max of each p, and then the max of those 3 numbers
            maxMomMax = max(p1Mom.max(), p2Mom.max(), p3Mom.max())
            
            if minMomSum == p1Mom.sum():
                ann_x = dt.time(0, 10, 0)
                
                # Shift the horizontal position of the annotation if the
                # 1st period is when the home team had the highest momentum
                if maxMomMax == p1Mom.max():
                    if p2Mom.max() < p3Mom.max():
                        # Shift the annotation to the 2nd period area
                        ann_x = dt.time(0, 30, 0)
                    elif p2Mom.max() >= p3Mom.max():
                        # Shift the annotation to the 3rd period area
                        ann_x = dt.time(0, 50, 0)
                        
            elif minMomSum == p2Mom.sum():
                ann_x = dt.time(0, 30, 0)
                
                # Shift the horizontal position of the annotation if the
                # 2nd period is when the home team had the highest momentum
                if maxMomMax == p2Mom.max():
                    if p1Mom.max() < p3Mom.max():
                        # Shift the annotation to the 1st period area
                        ann_x = dt.time(0, 10, 0)
                    elif p1Mom.max() >= p3Mom.max():
                        # Shift the annotation to the 3rd period area
                        ann_x = dt.time(0, 50, 0)
                        
            else:
                ann_x = dt.time(0, 50, 0)
                
                # Shift the horizontal position of the annotation if the
                # 3rd period is when the home team had the highest momentum
                if maxMomMax == p3Mom.max():
                    if p2Mom.max() < p1Mom.max():
                        # Shift the annotation to the 2nd period area
                        ann_x = dt.time(0, 30, 0)
                    elif p2Mom.max() >= p1Mom.max():
                        # Shift the annotation to the 3rd period area
                        ann_x = dt.time(0, 10, 0)
                        
        elif Mom_Sum < -50:
            Mom_Note = f'Momentum Favors <b><span style="color: {ACol}">{Away}</span></b><br>' + \
                f'by <b>{int(abs(Mom_Sum)):,}</b> Points'
            ann_y = lower_bound + 15
            
            # Determine the appropriate period to place the annotation
            p1Mom = AMom[AMom.index <= dt.time(0, 20, 0)].Net_Momentum.sum()
            p2Mom = AMom[(AMom.index >= dt.time(0, 20, 0)) & (AMom.index <= dt.time(0, 40, 0))].Net_Momentum.sum()
            p3Mom = AMom[(AMom.index >= dt.time(0, 40, 0)) & (AMom.index <= dt.time(1, 0, 0))].Net_Momentum.sum()
            
            # Take the period with max. amount of negative momentum
            maxMomSum = max(p1Mom.sum(), p2Mom.sum(), p3Mom.sum())
            # Take the min of each p, and then the min of those 3 numbers
            minMomMin = min(p1Mom.min(), p2Mom.min(), p3Mom.min())
            
            if maxMomSum == p1Mom.sum():
                ann_x = dt.time(0, 10, 0)
                
                # Shift the horizontal position of the annotation if the
                # 1st period is when the home team had the highest momentum
                if minMomMin == p1Mom.min():
                    if p2Mom.min() < p3Mom.min():
                        # Shift the annotation to the 2nd period area
                        ann_x = dt.time(0, 30, 0)
                    elif p2Mom.min() >= p3Mom.min():
                        # Shift the annotation to the 3rd period area
                        ann_x = dt.time(0, 50, 0)
                        
            elif maxMomSum == p2Mom.sum():
                ann_x = dt.time(0, 30, 0)
                
                # Shift the horizontal position of the annotation if the
                # 2nd period is when the home team had the highest momentum
                if minMomMin == p2Mom.min():
                    if p1Mom.min() < p3Mom.min():
                        # Shift the annotation to the 1st period area
                        ann_x = dt.time(0, 10, 0)
                    elif p1Mom.min() >= p3Mom.min():
                        # Shift the annotation to the 3rd period area
                        ann_x = dt.time(0, 50, 0)
                        
            else:
                ann_x = dt.time(0, 50, 0)
                
                # Shift the horizontal position of the annotation if the
                # 3rd period is when the home team had the highest momentum
                if minMomMin == p3Mom.min():
                    if p2Mom.min() < p1Mom.min():
                        # Shift the annotation to the 2nd period area
                        ann_x = dt.time(0, 30, 0)
                    elif p2Mom.min() >= p1Mom.min():
                        # Shift the annotation to the 3rd period area
                        ann_x = dt.time(0, 10, 0)
                        
        
        # Adjust the y annotation position
        ann_y = round(ann_y / 10, 0) * 10
        
        fig.add_annotation(
            xref = 'x', yref = 'y', # xanchor='left',
            x = ann_x, y = ann_y,  # yanchor = y_anchor,
            # x = HMom.index[50], y = ann_y,
            text = Mom_Note, showarrow = False,
            row = row, col = col, font = dict(size=14)
        )
        
        self.fig = fig
        
    def P5Shots(self, row=None, col=None):
        # Add the Prior 5 shots plot
        # ------------------------------------------------------------------------
        # ------------------------------------
        
        # Collect the relevant attributes
        gs   = self.gs
        fig  = self.fig
        row  = self.row + 3 if row is None else row
        col  = self.col if col is None else col
        HCol = self.HCol
        ACol = self.ACol
        Home = self.Home  # Note: Home & Away are the abbreviations in this module
        Away = self.Away
        
        # Collect the relevant stats for the prior 5 shots plot
        P5_shots = gs.prior_5_shots
        HomePens, AwayPens = gs.HomePens, gs.AwayPens
        Pens = [HomePens, AwayPens]
        
        # Create an iterable zipped list of the data, color, and line styles to add to the chart
        zipped = zip([f'{Home} Shots - Prior 5 min', f'{Away} Shots - Prior 5 min'],
                     ([HCol, ACol]),
                     ['solid', 'solid'])
        
        for trace, color, line in zipped:
            plot = go.Scatter(x          = P5_shots.Time,
                              y          = P5_shots[trace],
                              mode       = 'lines',
                              fill       = 'tozeroy',
                              fillcolor  = my_Hex_to_RGBA(color, 0.15),
                              showlegend = False,
                              name       = trace,
                              line       = dict(color=color,
                                                dash=line))
            fig.add_trace(plot, secondary_y=False, row = row, col = col)
        
        # Add period seperating lines to 3rd subplot
        fig = GameScatter.PeriodLines(
            self, fig, P5_shots, Home, Away, row, col, 'Shots - Prior 5 min'
        )
        
        # Shade areas for Home/Away team power plays
        # Note: Need to figure out a way to neatly
        #       make users aware of this via annotations
        Pens = [HomePens, AwayPens]
        height = max(P5_shots[f'{Home} Shots - Prior 5 min'].max(),
                     P5_shots[f'{Away} Shots - Prior 5 min'].max()) + 1
        
        fig = GameScatter.ShadePenalties(fig, Pens, [ACol, HCol], height, row, col)
        
        # Format the prior 5 shots subplot
        ntick = height if height < 10 else int(height / 2)
        
        fig.update_yaxes(title_text    = "Shots",
                         secondary_y   = False,
                         showgrid      = False,
                         row           = row,
                         col           = col,
                         titlefont     = dict(size=22),
                         nticks        = int(round(ntick,0)),
                         range         = (0, height),
                         zeroline      = False)
        
        # Set x-axis title
        fig.update_xaxes(title_text = "Game Time Elapsed",
                         titlefont  = dict(size=18),
                         tickfont   = dict(size=18),
                         showgrid   = False,
                         row        = row,
                         col        = col,
                         #range      = ["00:00:00", "00:01:00"],
                         tickvals   = ["00:00:00"] +
                         [f"00:{m}:00" for m in range(10, 65, 10)] +
                         ["01:00:00"])
        
        self.fig = fig
        
    def P5Hits(self, row=None, col=None):
        # Add the Prior 5 hits plot
        # ------------------------------------------------------------------------
        # ------------------------------------
        # Collect the relevant attributes
        gs   = self.gs
        fig  = self.fig
        row  = self.row + 4 if row is None else row
        col  = self.col if col is None else col
        HCol = self.HCol
        ACol = self.ACol
        Home = self.Home  # Note: Home & Away are the abbreviations in this module
        Away = self.Away
        
        P5_hits = gs.prior_5_hits
        HomePens, AwayPens = gs.HomePens, gs.AwayPens
        Pens = [HomePens, AwayPens]
        
        zipped = zip([f'{Home} Hits - Prior 5 min', f'{Away} Hits - Prior 5 min'],
                     ([HCol, ACol]),
                     ['solid', 'solid'])
        
        for trace, color, line in zipped:
            plot = go.Scatter(x          = P5_hits.Time,
                              y          = P5_hits[trace],
                              mode       = 'lines',
                              fill       = 'tozeroy',
                              fillcolor  = my_Hex_to_RGBA(color, 0.15),
                              showlegend = False,
                              name       = trace,
                              line       = dict(color=color,
                                                dash=line))
            fig.add_trace(plot, secondary_y=False, row = row, col = col)
        
        # Add period seperating lines to 4th subplot
        fig = GameScatter.PeriodLines(
            self, fig, P5_hits, Home, Away, row, col, 'Hits - Prior 5 min'
        )
        
        # Shade areas for Home/Away team power plays
        # Note: Need to figure out a way to neatly
        #       make users aware of this via annotations
        Pens = [HomePens, AwayPens]
        height = max(P5_hits[f'{Home} Hits - Prior 5 min'].max(),
                     P5_hits[f'{Away} Hits - Prior 5 min'].max()) + 2
        
        fig = GameScatter.ShadePenalties(fig, Pens, [ACol, HCol], height, row, col)
        
        # Format the 4th subplot
        ntick = height if height < 10 else int(height / 2)
        
        fig.update_yaxes(title_text    = "Hits",
                         secondary_y   = False,
                         showgrid      = False,
                         row           = row,
                         col           = col,
                         titlefont     = dict(size=22),
                         nticks        = int(round(ntick,0)),
                         range         = (0, height - 1),
                         zeroline      = False)
        
        # Set x-axis title
        fig.update_xaxes(title_text = "Game Time Elapsed",
                         titlefont  = dict(size=18),
                         tickfont   = dict(size=18),
                         showgrid   = False,
                         row        = row,
                         col        = col,
                         #range      = ["00:00:00", "00:01:00"],
                         tickvals   = ["00:00:00"] +
                         [f"00:{m}:00" for m in range(10, 65, 10)] +
                         ["01:00:00"])
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        self.fig = fig
