# -*- coding: utf-8 -*-
"""
Will create and configure a plotyl scatter plot to look like an ice rink.
The resulting figure that is created can be plugged directly
into a plotly frame.

Created on Sun Aug  8 13:21:19 2021

@author: grega
"""
import plotly.graph_objects as go
import plotly.express as px
from PIL import ImageColor as IC  # For converting hex color codes to RGB codes
import numpy as np, pandas as pd

# Define a function for converting Hex color codes into RGB codes that can be processed by plotly
def my_Hex_to_RGBA(Hex, opacity = 0.75):
    tup = IC.getcolor(Hex, 'RGB') + tuple([0.5])
    tup_str = f'rgba({tup[0]}, {tup[1]}, {tup[2]}, {str(opacity)})'
    return tup_str

class RinkScatter:
    
     def __init__(self, gs, fig, row, col, legendgroup, HCol, ACol, txtColor):
        self.gs          = gs
        self.fig         = fig
        self.row         = row
        self.col         = col
        self.legendgroup = legendgroup
        self.HCol        = HCol
        self.ACol        = ACol
        self.txtColor    = txtColor
        
        # Collect relevant attributes of the gs class object
        # and assign as attributes of `GameScatter`
        self.Home  = gs.HomeAbrv
        self.Away  = gs.AwayAbrv
        # self.plays = gs.plays
        # self.goals = gs.Goals
    
     def Append(self, vertically_aligned = True):
        # Define function to format the Ice Map scatter plots
        # ------------------------------------------------------------------------
        # ------------------------------------
        def FormatMap(fig, Home, HCol, Away, ACol, row, col):
            
            # LEFT & RIGHT y-axis
            for LoR, HoA, standoff in zip([False, True], [Home, Away], [0, 10]):
                fig.update_yaxes(title_text     = f"{HoA} Attacks",
                                 showgrid       = False,
                                 range          = (-42.5, 42.5),
                                 secondary_y    = LoR,
                                 zeroline       = False,
                                 row            = row,
                                 col            = col,
                                 title          = dict(standoff=standoff),
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
            for x, y, color in zip([-89, -25, 0, 25, 89], [40, 42.5, 42.5, 42.5, 40],
                                   ['indianred', 'steelblue', 'indianred', 'steelblue', 'indianred']):
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
                              line_color       = "indianred",
                              row  = row, col  = col,
                              opacity          = 0.35)
            
            # Add shaded areas for each teams attacking zone & to denotre the boards
            xs = [i / 100 for i in range(7375, 10010, 5)]
            xs = pd.Series(xs)
            
            ys = [((x - 73.75)**5 / (26.25**4)) - 42.5 for x in xs]
            ys = pd.Series(ys)
            
            for x, y, color in zip([xs, xs, -xs, -xs],
                                   [ys, -ys, ys, -ys],
                                   [ACol, ACol, HCol, HCol]):
                
                Shade = go.Scatter(x          = x,
                                   y          = y,
                                   line       = dict(color=color, width=6),
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
                                line       = dict(color=my_Hex_to_RGBA(self.txtColor, 0.5),
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
                                line       = dict(color=my_Hex_to_RGBA(self.txtColor, 0.5),
                                                  dash='dot',
                                                  width=1))
            fig.add_trace(RHouse, secondary_y=False, row=row, col=col)
            
            # Add LHS/RHS Goal Creases
            for x, y in zip([[-89, -85], [89, 85]], [[-4, 4], [-4, 4]]):
                fig.add_shape(
                    type="rect", x0=x[0], x1=x[1], y0=y[0], y1=y[1],
                    row=row, col=col, fillcolor='steelblue', opacity=0.45,
                    line_color = 'rgba(0,0,0,0)'
                )
            
            return fig
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Collect relevant attributes
        gs   = self.gs
        fig  = self.fig
        row  = self.row
        col  = self.col
        HCol = self.HCol
        ACol = self.ACol
        Home = self.Home  # Note: Home & Away are the abbreviations in this class
        Away = self.Away
        
        # Collect relevant X/Y df's from gs
        
        # Home team shots, shot attempts, goals
        HomeS, HomeSA, HomeG  = gs.HomeS, gs.HomeSA, gs.HomeG
        # Away team shots, shot attempts, goals
        AwayS, AwaySA, AwayG  = gs.AwayS, gs.AwaySA, gs.AwayG
        
        # Home team hits, takeaways, giveaways
        HomeH, HomeT, HomeGA  = gs.HomeH, gs.HomeT, gs.HomeGA
        # Away team hits, takeaways, giveaways
        AwayH, AwayT, AwayGA = gs.AwayH, gs.AwayT, gs.AwayGA
        
        # Create storage lists of relevant df's
        GoalsDfs   = [HomeG, AwayG]
        ShotsDfs   = [HomeS, AwayS]
        ShotAttDfs = [HomeSA, AwaySA]
        HitsDfs    = [HomeH, AwayH]
        TkawDfs    = [HomeT, AwayT]
        GvawDfs    = [HomeGA, AwayGA]
        Colors     = [HCol, ACol]
        
        # Create the Goals, Shots & Shot Attempts map
        # ------------------------------------------------------------------------
        # ------------------------------------
        myRow = row
        myCol = col
        
        # Start by adding goal markers to the map
        Legend = [Home + ' Goals', Away + ' Goals']
        SecndY = [False, True]
        zipped = zip(GoalsDfs, Colors, Legend, SecndY)
        for Df, color, name, second_y in zipped:
            # Skip team df's if the team scored no goals
            if Df.shape[0] > 0:
                
                # Create reference for customdata that will be displayed in hoverlabels.
                # Note: If no goals were scored with two assists, then there will be
                # no column for player_4. A list of empty strings will be created
                # to mimic a player_4 column. Also, if there is a column for player_3 in
                # the df, but on one of the goals there was no secondary assist, there will
                # be a NaN value in the player_3 column. Therefore, we need to ensure every
                # value used in the hoverlables is an actual string, hence str(i or '')
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
                    # If 'player_4' & 'player_3' are NOT in `Df`, then no goals were
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
                        
                        # If player_3 position is also empty, the goal was unassisted
                        if str(i[2] or '') == '':
                            i[3], i[1] = i[1], i[3]
                        
                        # Otherwise, just player_4 is empty
                        else:
                            i[3], i[2] = i[2], i[3]
                
                # Now add the goal data (w/ hover the abovelabels) to the scatter plot / map
                # Df.MarkerStyle = 218
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
                                  text          = Df.MarkerStyle.values,
                                  textfont      = dict(family = "Arial",
                                                       size   = 26,
                                                       color  = my_Hex_to_RGBA(color, 0.75)),
                                  mode          = "markers+text",
                                  showlegend    = False,
                                  marker_symbol = Df.MarkerStyle,
                                  name          = name,
                                  marker        = dict(color=color, size=1, opacity = 0.5),
                                  line          = dict(color=color, width=5))
                
                fig.add_trace(plot, secondary_y=second_y, row = myRow, col = myCol)
            
        # Add the `Shots` markers to the scatter plot / map
        Legend = [Home + ' Shots', Away + ' Shots']
        SecndY = [False, True]
        zipped = zip(ShotsDfs, Colors, Legend, SecndY)
        
        for Df, color, name, secnd_y in zipped:
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
                              marker        = dict(color = color, size = 8, opacity = 0.3),
                              line          = dict(color = color, width = 10))
            fig.add_trace(plot, secondary_y=secnd_y, row = myRow, col = myCol)
            del plot
            
        # Add the `Shot Attempt` markers to the scatter plot / map
        Legend = [Home + ' Attempts', Away + ' Attempts']
        SecndY = [False, True]
        zipped = zip(ShotAttDfs, Colors, Legend, SecndY)
        
        for Df, color, name, secnd_y in zipped:
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
                              'Shot By: %{customdata[0]}<br>' +
                              'Blocked By: %{customdata[1]}<br>' +
                              '<extra></extra>',
                              text          = Df['MarkerStyle'],
                              mode          = "markers",
                              showlegend    = False,
                              marker_symbol = Df.MarkerStyle,
                              name          = name,
                              marker        = dict(color = color, size = 7, opacity = 0.25),
                              line          = dict(color = color, width = 10))
            fig.add_trace(plot, secondary_y=secnd_y, row = myRow, col = myCol)
            
        # Format the map to look more like an ice rink
        fig = FormatMap(fig, Home, HCol, Away, ACol, myRow, myCol)
        # ------------------------------------
        # ------------------------------------------------------------------------
        
        # Create the Hits, Takeaways, & Giveaways map
        # ------------------------------------------------------------------------
        # ------------------------------------
        if vertically_aligned:
            myRow += 2
        else:
            myCol += 2
        
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
                              marker        = dict(color=color, size=10, opacity = 0.65),
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
                                                   size=10,
                                                   opacity = 0.65),
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
                                                   size=10,
                                                   opacity = 0.65),
                              marker_symbol = Df.MarkerStyle,
                              name          = name,
                              line          = dict(color=color,
                                                   width=10))
            fig.add_trace(plot, secondary_y=False, row = myRow, col = myCol)
        
        # Format the subplot to look more like an ice rink
        fig = FormatMap(fig, Home, HCol, Away, ACol, myRow, myCol)
        # ------------------------------------
        # ------------------------------------------------------------------------
        self.fig = fig
