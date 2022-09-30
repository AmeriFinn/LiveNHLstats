# -*- coding: utf-8 -*-
"""
The replacement for 'myNHLstats.py' which I currently have saved
to the `Live NHL Stats` directory in my G-Drive.
Created on Sun Aug  8 13:31:12 2021

@author: grega
"""
from GameRecap import GameRecap
from NightRecap import NightRecap

class myNHLstats:
    
    def Recap(
            game_id, game_type, AltHomeColor=False, AltAwayColor=False,
            template='plotly_white', publish=True
    ):
        recap = GameRecap(game_id, game_type, AltHomeColor, AltAwayColor, template, publish)
        recap.Recap()
        return recap
    
    def Night(
            GameDay, template='plotly_white', publish=True
    ):
        night = NightRecap(GameDay, template, publish)
        night.Recap()
        return night

# game_id = 2021020259
# recap = myNHLstats.Recap(game_id)
