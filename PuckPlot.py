# -*- coding: utf-8 -*-
"""
Will create the sunburst plots that I call PuckPlots.
The resulting figure that is created can be plugged directly
into a plotly frame.

Created on Sun Aug  8 13:31:12 2021

@author: grega
"""
import plotly.graph_objects as go
import plotly.express as px

def PuckPlot(gs, fig, row, col, stat, HCol, ACol, points=None, Both=True, horiz_aligned=True):
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
    Home  = gs.HomeAbrv
    Away  = gs.AwayAbrv
    plays = gs.plays
    
    if stat.upper() == 'GSA':
        ## Special procedure if SHOT ATTEMPT is entered for the stat parameter
        # Refine the plays df to the columns (cols) and rows (.isin()) needed
        cols  = ['team_for', 'period', 'player_1', 'event_type']
        shots = plays.loc[
            plays.event_type.isin(['BLOCKED_SHOT', 'MISSED_SHOT', 'SHOT', 'GOAL']),
            cols + ['player_2']
        ]
        
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
            
        shots.event_type = shots.event_type.apply(lambda x: x.replace('_', '<br>') + "s")
        
        # Return the shot attempt stats data to be used in the sunburst
        stats = shots[cols]
        
        # Define variables need to group data and for the sunburst path
        newCols = ['Team', 'Period', 'Player', "Type", stat + "s"]
        path1   = ['Team', 'Player', "Type", 'Period']
        path2   = ['Team', "Type", 'Period', 'Player']
        val     = stat + "s"
        depths  = [2, 3]
        
    elif stat.upper() == 'HTG':
        cols = ['team_for', 'period', 'player_1', 'event_type']
        HTG  = plays.loc[plays.event_type.isin(['HIT', 'TAKEAWAY', 'GIVEAWAY']), cols]
        
        stats = HTG
        
        newCols = ['Team', 'Period', 'Player', "Type", stat + "s"]
        path1   = ['Team', 'Player', "Type", 'Period']
        path2   = ['Team', "Type", 'Period', 'Player']
        val     = stat + "s"
        depths  = [2, 3]
        
    elif stat.upper() == 'POINT':
        cols = ['team_for', 'period', 'player', 'event_type']
        
        stats = points
        
        newCols = ['Team', 'Period', 'Player', "Type", stat]
        path1   = ['Team', 'Player', "Type", 'Period']
        # path1   = ['Team', "Type", 'Player', 'Period']
        path2   = ['Team', "Type", 'Period', 'Player']
        val     = stat
        depths  = [2, 3]
        
    else:
        # For all other stats, only a simple transformation is needed
        cols  = ['team_for', 'period', 'player_1']
        stats = plays.loc[plays.event_type == stat.upper(), cols]
        
        # Define variables need to group data and for the sunburst path
        newCols = ['Team', 'Period', 'Player', stat + "s"]
        path1   = ['Team', 'Player', 'Period']
        path2   = ['Team', 'Period', 'Player']
        val     = stat + "s"
        depths  = [2, 3]
        
    stat += "s"
    
    # Group the stats data by period and then by player
    if stats.shape[0] > 0:
        # Collect necessary data
        group = cols
        stats = stats.groupby(group).size().reset_index()
        stats.columns = newCols
        
        # Determine how the puck plots should be transposed
        if horiz_aligned:
            col_trans = [0, 1]
            row_trans = [0, 0]
        else:
            col_trans = [0, 0]
            row_trans = [0, 1]
        
        # Format the Period and Player column values
        stats.Period = stats.Period.astype('int')
        stats.Period = stats.Period.apply(lambda x: strPeriod(x))
        stats.Player = stats.Player.apply(lambda x: strPlayer(x))
        
        for path, col_, row_, depth in zip([path1, path2], col_trans, row_trans, depths):
            # Skip adding the second puck plot if desired
            if ((col_ == 1) | (row_ == 1)) & (Both == False):
                continue
            
            else:
                ## Create the left-hand side sunburst plot - 'Team', 'Player', 'Period'
                sun = px.sunburst(
                    stats,
                    path       = path,
                    values     = val,
                    hover_data = path,
                    color      = 'Team',
                    color_discrete_map = {Home: HCol, Away: ACol, '(?)': 'lightgrey'}
                )
                
                # Define the hovertemplate to be used in the sunburst  plot
                if stat.upper() == 'GSA':
                    # Special template for         shot attempts
                    hTemplate = '<b>Team: %{customdata[0]}</b><br>' + \
                                f'{path[1]}: ' + '%{customdata[1]}<br>' + \
                                f'{path[2]}: ' + '%{customdata[2]}<br>' + \
                                f'{path[3]}: ' + '%{customdata[3]}<br>' + \
                                f'{stat}: '    + '%{value:,.0f}'
                
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
                              row = row + row_,
                              col = col + col_)
                fig.update_yaxes(row = row + row_, col = col + col_, automargin = True)
        
    return fig
