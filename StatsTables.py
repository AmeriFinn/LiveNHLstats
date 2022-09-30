# -*- coding: utf-8 -*-
"""
Will create and configure a plotly table in the desired format -
with respect to what type of summarization is being done.
The resulting figure that is created is plugged directly into a plotly frame.

Created on Sun Aug  8 13:31:12 2021

@author: grega
"""
import pandas as pd
import plotly.graph_objects as go
from PIL import ImageColor as IC  # For converting hex color codes to RGB codes

# Define a function for converting Hex color codes into RGB codes that can be processed by plotly
def my_Hex_to_RGBA(Hex, opacity = 0.75):
    tup = IC.getcolor(Hex, 'RGB') + tuple([0.5])
    tup_str = f'rgba({tup[0]}, {tup[1]}, {tup[2]}, {str(opacity)})'
    return tup_str

class StatsTables:
    
    def __init__(self, gs, fig, row, col, HCol, ACol):
        
        self.gs   = gs
        self.fig  = fig
        self.row  = row
        self.col  = col
        self.HCol = HCol
        self.ACol = ACol
        
        # Collect the alternate team colors to be used in the game and season summary stats tables
        # First load in the full df of team names and colors
        Home  = gs.HomeAbrv
        Away  = gs.AwayAbrv
        tLUrl = 'https://raw.githubusercontent.com/AmeriFinn/LiveNHLstats/master/teamList.csv'
        tL = pd.read_csv(tLUrl, index_col=0)
        
        HomeCols = tL[tL.team_abbrv == Home][['home_c', 'away_c']]
        if HCol == HomeCols['home_c'].values[0]:
            HCol_text = HomeCols['away_c'].values[0]
        else:
            HCol_text = HomeCols['home_c'].values[0]
            
        AwayCols = tL[tL.team_abbrv == Away][['home_c', 'away_c']]
        if ACol == AwayCols['home_c'].values[0]:
            ACol_text = AwayCols['away_c'].values[0]
        else:
            ACol_text = AwayCols['home_c'].values[0]
        
        self.HCol_text = HCol_text
        self.ACol_text = ACol_text
        
    def SumStats(self, playoffs = False, po_table = 'master'):
        gs   = self.gs
        fig  = self.fig
        row  = self.row
        col  = self.col
        HCol = self.HCol
        ACol = self.ACol
        if playoffs:
            if po_table.lower() == 'master':
                SS = gs.SumStats_Master
            else:
                SS = gs.SumStats_avg
        else:
            SS = gs.SumStats
        
        # Adjust SumStats multi-index dataframe to be compatible with plotly
        SS.columns = [(c[0], c[1]) for c in SS.columns]
        SS.reset_index(inplace=True, drop=False)
        SS.rename(columns={'index': ('Period', 'Team')}, inplace=True)
        
        # Create a list of fill colors for the table cells
        cell_fill_color = []
        head_fill_color = []
        n = SS.shape[1]
        for i in range(n + 1):
            if i == 0:
                cell_fill_color.append(['slategray'] * n)
                head_fill_color.append(['slategray'] * 2)
            
            elif i <= 2:
                cell_fill_color.append(['white'] * n)
                head_fill_color.append(['slategray', [ACol, HCol][(i % 2)]])
            
            elif i <= 4:
                cell_fill_color.append(['#d4d4d4'] * n)
                head_fill_color.append(['slategray', [ACol, HCol][(i % 2)]])
            
            elif i <= 6:
                cell_fill_color.append(['#a8a5a5'] * n)
                head_fill_color.append(['slategray', [ACol, HCol][(i % 2)]])
            
            elif i <= 8:
                cell_fill_color.append(['#8c8c8c'] * n)
                head_fill_color.append(['slategray', [ACol, HCol][(i % 2)]])
            
            elif i <= 10:
                cell_fill_color.append(['beige'] * n)
                head_fill_color.append(['slategray', [ACol, HCol][(i % 2)]])
            
        # Create the table object to be added to the figure
        table = go.Table(header = dict(values     = list(SS.columns),
                                       font       = dict(size=17, color='white'),
                                       line_color = 'darkslategray',
                                       fill_color = head_fill_color,
                                       align      = 'left'),
                         cells  = dict(values     = [SS[col] for col in SS.columns],
                                       font       = dict(size=13, color='black'),
                                       line_color = 'darkslategray',
                                       fill_color = cell_fill_color,
                                       align      = 'left',
                                       height     = 25),
                         columnwidth = [1.4, 1.1, 1.1] + [0.9 for j in range(n - 3)],
                         )
        
        # Add the figure
        fig.add_trace(table, row = row, col = col)
        
        return fig
    
    def PlayerSummary(self, fig, ts, Team1_Abrv):
        
        HCol      = self.HCol
        HCol_text = self.HCol_text
        ACol      = self.ACol
        ACol_text = self.ACol_text
        
        if ts.Team1[0] == Team1_Abrv:
            Team1 = ts.Team1[1]
            Team2 = ts.Team2[1]
        else:
            Team2 = ts.Team1[1]
            Team1 = ts.Team2[1]
            
        for df, color, text_color, col in zip([Team1, Team2], [ACol, HCol], [ACol_text, HCol_text], [1, 2]):
            # Format the player column to link to their profile on NHL.com
            NHL_url = 'https://www.nhl.com/player/'
            for i in df.index:
                # Determine the appropriate NHL url to ping
                player              = df.loc[i, 'Player']
                player_url          = player.replace(' ', '-').lower()
                ID                  = df.loc[i, 'ID']
                player_url          = NHL_url + player_url + '-' + str(ID)
                df.loc[i, 'Player'] = f'<a href="{player_url}" style="color: {text_color}">' + \
                    f'{player.replace(" ", "<br>")}</a>'
            
            df.drop(columns=['ID'], inplace=True)
            
            # Create a list of fill colors for the table cells
            cell_fill_color = []
            head_fill_color = []
            n = df.shape[1]
            for i in range(n + 1):
                if i == 0:
                    cell_fill_color.append([my_Hex_to_RGBA(color, 0.6)] * n)
                    head_fill_color.append([color])
                
                elif i <= 2:
                    cell_fill_color.append([my_Hex_to_RGBA(color, 0.5)] * n)
                    head_fill_color.append([color])
                
                else:
                    cell_fill_color.append(['white'] * n)
                    head_fill_color.append([color])
                
            # Create the table object to be added to the figure
            table = go.Table(
                header = dict(values     = list(df.columns),
                              font       = dict(size=16, color='white'),
                              line_color = 'darkslategray',
                              fill_color = head_fill_color,
                              align      = 'center'),
                cells  = dict(values     = [df[col] for col in df.columns],
                              font       = dict(size=14, color='black'),
                              line_color = 'darkslategray',
                              fill_color = cell_fill_color,
                              align      = 'left',
                              height     = 25),
                # columnwidth = [1.5, 0.6, 0.7] + [0.5 for j in range(n - 6)] + [1.2, 0.9, 0.9],
                columnwidth = [3 / n, 1 / n, 1.5 / n] + [1 / n for j in range(n - 6)] + [2.25 / n, 1.5 / n, 1.5 / n],
            )
            
            # Add the figure
            fig.add_trace(table, row = 1, col = col)
        
        return fig
    
    def TeamSummary(self, fig, ts, col, teamCol):
        
        df         = ts.full_df
        text_color = ts.teamCol_text
        
        # Format the player column to link to their profile on NHL.com
        NHL_url = 'https://www.nhl.com/player/'
        for i in df.index:
            # Determine the appropriate NHL url to ping
            player              = df.loc[i, 'Player']
            player_url          = player.replace(' ', '-').lower()
            ID                  = df.loc[i, 'ID']
            player_url          = NHL_url + player_url + '-' + str(ID)
            # df.loc[i, 'Player'] = f'<a href="{player_url}">{player.replace(" ", "<br>")}</a>'
            df.loc[i, 'Player'] = f'<a href="{player_url}" style="color: {text_color}">' + \
                f'{player.replace(" ", "<br>")}</a>'
        
        df.drop(columns=['ID'], inplace=True)
        
        # Create a list of fill colors for the table cells
        cell_fill_color = []
        head_fill_color = []
        n = df.shape[1]
        for i in range(n + 1):
            if i == 0:
                cell_fill_color.append([my_Hex_to_RGBA(teamCol, 0.6)] * n)
                head_fill_color.append([teamCol])
            
            elif i <= 2:
                cell_fill_color.append([my_Hex_to_RGBA(teamCol, 0.5)] * n)
                head_fill_color.append([teamCol])
            
            else:
                cell_fill_color.append(['white'] * n)
                head_fill_color.append([teamCol])
            
        # Create the table object to be added to the figure
        table = go.Table(
            header = dict(values     = list(df.columns),
                          font       = dict(size=16, color='white'),
                          line_color = 'darkslategray',
                          fill_color = head_fill_color,
                          align      = 'left'),
            cells  = dict(values     = [df[col] for col in df.columns],
                          font       = dict(size=14, color='black'),
                          line_color = 'darkslategray',
                          fill_color = cell_fill_color,
                          align      = 'left',
                          height     = 25),
            columnwidth = [1.5, 0.5, 0.7, 0.6] + [0.5 for j in range(n - 7)] + [1.2, 0.85, 0.85],
        )
        
        # Add the figure
        fig.add_trace(table, row = 1, col = col)
        
        return fig
    