# -*- coding: utf-8 -*-
"""
Created on Sun Nov 21 13:26:39 2021

@author: grega
"""
# Import the necessary plotly modules
from plotly.subplots import make_subplots
from datetime import datetime as dt
import numpy as np

class FigureFrames:
    
    def GameRecapMaster(GameDay, HomeAbrv, AwayAbrv, txtColor, template):
        GPdict = {"secondary_y": True, 'colspan': 1, 'rowspan': 2}   # GameStats specs
        MMdict = {"secondary_y": True, 'colspan': 1, 'rowspan': 1}   # Momentum & P5 plot specs
        MPdict = {"secondary_y": True, 'colspan': 2, 'rowspan': 1}   # GameMap specs
        SBdict = {"type": "sunburst", 'colspan': 1, 'rowspan': 1}    # Sunburst plot specs
        TBdict = {"type": "table", 'colspan': 1, 'rowspan': 2}       # Table specs
        
        fig = make_subplots(
            rows  = 7,
            cols  = 3,
            specs = [
                [GPdict, MPdict, None],
                [None, SBdict, SBdict],
                [MMdict, MPdict, None],
                [MMdict, SBdict, SBdict],
                [MMdict, SBdict, SBdict],
                [TBdict, SBdict, SBdict],
                [None, SBdict, SBdict]
            ],
            column_widths  = [2, 1, 1],
            row_heights    = [1.5, 1, 1.5, 1, 1, 1, 1],
            subplot_titles = (
                "Goals, Shots, & Shot Attempts Time Series",
                "Goals, Shots, & Shot Attempts Map",
                "GSA | By PLAYER", "GSA | By PERIOD",
                "Net Momentum Over Prior 5 Minutes",
                "Hits, Takeaways, & Giveaways Map",
                "Shots Over Prior 5 Minutes",
                "HTG | By PLAYER", "HTG | By PERIOD",
                "Hits Over Prior 5 Minutes",
                "Goals | By PLAYER", "Goals | By PERIOD",
                "Summary Stats",
                "Points | By PLAYER", "Points | By PEIRIOD",
                "Shots | By PLAYER", "Shots | By PERIOD"
            ),
            vertical_spacing   = 0.06,
            horizontal_spacing = 0.05
        )
        
        ### Adjust figure formats
        # Adjust subplot title font sizes
        for i in fig['layout']['annotations']:
            i['font']['size'] = 24
        
        # Adjust figure fonts and font sizes,
        # add figure title, adjust size and bg color
        height = 2800  # 2250
        width  = 1400
        
        fig.update_layout(font            = dict(family = "Arial",
                                                 size   = 24,
                                                 color  = txtColor),
                          title_text      = f"{AwayAbrv} @ {HomeAbrv} | {GameDay}",
                          title_font_size = 32,
                          autosize        = True,
                          width           = width,
                          height          = height,
                          margin          = dict(l=15, r=15, b=15, t=65, pad=0),
                          template        = template,
                          hovermode       = "x",
                          hoverlabel      = dict(namelength = -1),
                          legend          = dict(x = 0, y = 1, traceorder = 'normal',
                                                 font = dict(size = 12)))
        
        return fig
        
    def GameRecapTable(GameDay, HomeAbrv, AwayAbrv, txtColor, template):
        TBdict = {"type": "table", 'colspan': 1, 'rowspan': 2}  # Table specs
        
        fig = make_subplots(
            rows  = 2,
            cols  = 2,
            specs = [
                [TBdict, TBdict],
                [None, None],
            ],
            column_widths  = [1, 1],
            row_heights    = [1, 1],
            subplot_titles = (
                f"{AwayAbrv} Player Stats",
                f"{HomeAbrv} Player Stats",
            ),
            # vertical_spacing   = 0.06,
            horizontal_spacing = 0.01
        )
        
        ## Adjust figure formats for fig
        # Adjust subplot title font sizes
        for i in fig['layout']['annotations']:
            i['font']['size'] = 24
        
        # Adjust figure fonts and font sizes,
        # add figure title, adjust size and bg color
        height = 1000
        width  = 1400
        
        fig.update_layout(
            font            = dict(family = "Arial",
                                   size   = 24,
                                   color  = txtColor),
            title_text      = f"{AwayAbrv} @ {HomeAbrv} | {GameDay}",
            title_font_size = 32,
            autosize        = True,
            width           = width,
            height          = height,  # width * 5.5,
            margin          = dict(l=15, r=15, b=15, t=65, pad=0),
            template        = template,
            hovermode       = "x",
            hoverlabel      = dict(namelength = -1),
            legend          = dict(x = 0, y = 1, traceorder = 'normal',
                                   font = dict(size = 12))
        )
        
        return fig
    
    def NightRecapFigure(GameDay, rows, titles, txtColor, template):
        MMdict = {"secondary_y": True, 'colspan': 1, 'rowspan': 1}  # Momentum
        TBdict = {"type": "table", 'colspan': 2, 'rowspan': 1}      # Table specs
        SBdict = {"type": "sunburst", 'colspan': 1, 'rowspan': 1}   # Sunburst plot specs
        
        # Update the GameDay string format
        GameDay = dt.strptime(GameDay, '%Y-%m-%d').strftime('%d-%b-%y')
        
        fig = make_subplots(
            rows               = rows * 2,
            cols               = 3,
            specs              = [[MMdict, TBdict, None], [MMdict, SBdict, SBdict]] * rows,
            column_widths      = [1, 0.5, 0.5],
            row_heights        = [4 / 3, 1] * rows,
            subplot_titles     = (titles),
            vertical_spacing   = 0.05 * min(1 / np.log(rows), 1),
            horizontal_spacing = 0.05  # * min(1 / np.log(rows), 1)
        )
        
        ## Adjust figure formats for fig
        # Adjust subplot title font sizes
        for i in fig['layout']['annotations']:
            i['font']['size'] = 20
        
        # Adjust other formats such as global font, title, dimensions, and template
        fig.update_layout(
            font            = dict(family = "Arial",
                                   size   = 24,
                                   color  = txtColor),
            title_text      = f"{GameDay} All Game Summary",
            title_font_size = 32,
            autosize        = True,
            # width           = width,
            height          = 700 * rows,
            margin          = dict(l=0, r=0, b=15, t=65, pad=0),
            template        = template,
            hovermode       = "x",
            hoverlabel      = dict(namelength = -1),
            legend          = dict(x = 0, y = 1, traceorder = 'normal',
                                   font = dict(size = 12))
        )
        
        return fig
    
    def PlayoffPreviewFigure(HomeAbrv, AwayAbrv, txtColor, template):
        
        MPdict = {"secondary_y": True, 'colspan': 2, 'rowspan': 1}   # GameMap specs
        SBdict = {"type": "sunburst", 'colspan': 1, 'rowspan': 1}    # Sunburst plot specs
        TBdict = {"type": "table", 'colspan': 2, 'rowspan': 2}       # Table specs
        
        fig = make_subplots(
            rows  = 5,
            cols  = 4,
            specs = [
                [MPdict, None, MPdict, None],
                [SBdict, SBdict, SBdict, SBdict],
                [SBdict, SBdict, SBdict, SBdict],
                [TBdict, None, TBdict, None],
                [None, None, None, None],
            ],
            # column_widths  = [2, 1, 1],
            # row_heights    = [1.5, 1, 1, 1, 1],
            subplot_titles = (
                "Goals, Shots, & Shot Attempts Map",
                "Hits, Takeaways, & Giveaways Map",
                "Points | By PLAYER", "Goals | By PLAYER", "Shot Attempts | By PLAYER", "HTG | By PLAYER", 
                "Points | By PEIRIOD", "Goals | By PERIOD", "Shot Attempts | By PERIOD", "HTG | By PERIOD",
                "Summary Stats - Total", "Summary Stats - Per Game"
            ),
            vertical_spacing   = 0.02,
            horizontal_spacing = 0.075
        )
        
        ### Adjust figure formats
        # Adjust subplot title font sizes
        for i in fig['layout']['annotations']:
            i['font']['size'] = 24
        
        # TODO: Update all of this
        # Adjust figure fonts and font sizes,
        # add figure title, adjust size and bg color
        height = 2500  # 2250
        width  = 1400
        
        fig.update_layout(font            = dict(family = "Arial",
                                                 size   = 24,
                                                 color  = txtColor),
                          title_text      = f"{AwayAbrv} VS {HomeAbrv} | Series Preview",
                          title_font_size = 32,
                          autosize        = True,
                          width           = width,
                          height          = height,
                          margin          = dict(l=15, r=15, b=15, t=65, pad=0),
                          template        = template,
                          hovermode       = "x",
                          hoverlabel      = dict(namelength = -1),
                          legend          = dict(x = 0, y = 1, traceorder = 'normal',
                                                 font = dict(size = 12)))
        
        return fig
        