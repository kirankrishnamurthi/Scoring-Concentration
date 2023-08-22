import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#-- NBA API Modules --#

from nba_api.stats.endpoints import boxscoretraditionalv2
from nba_api.stats.endpoints import teamgamelog
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.static import teams 

import time
import os

### Put your working directory here ###
os.chdir('')

### Get team ID ###

team_name = 'Los Angeles Lakers' #-- Enter the team name here --#

from nba_api.stats.static import teams 

team_list = teams.get_teams()

NBA_TEAM = [x for x in team_list if x['full_name'] == team_name][0]
NBA_TEAM_id = NBA_TEAM['id']

### Get team game log data ###

### fix the JSONDecodeError: Expecting value: line 1 column 1 (char 0) error ###
NBA_GLDATA = teamgamelog.TeamGameLog(team_id = NBA_TEAM_id, season = '2021').get_data_frames()[0]
NBATEAM_GAMEID = NBA_GLDATA['Game_ID'].tolist()

bxsdata = pd.DataFrame()

HHI_TS_INDEX = []
HHI_PS_INDEX = []
HHI_PCS_INDEX = []

### All Games Loop ###

for i in range(0, len(NBATEAM_GAMEID)):

    ### Data Retrieval & Cleanup ###
    bxdata = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id = NBATEAM_GAMEID[i]).get_data_frames()[0]

    ### Selecting only Team Players who were eligible to play ###
    bxdata = bxdata.loc[(bxdata['TEAM_ID'] == NBA_TEAM_id) & (bxdata['COMMENT'].str.contains('DNP - Injury/Illness') == False)].reset_index(drop = True)

    ### Fill all NaN values with 0 ###
    bxdata = bxdata.fillna(0)

    ### Create a value for time in minutes ###
    bxdata['MINUTES'] = bxdata['MIN'].str.split(':', expand = True).fillna(0)[0].astype(float)
    bxdata['SECONDS'] = bxdata['MIN'].str.split(':', expand = True).fillna(0)[1].astype(float)
    bxdata['TIME'] = bxdata['MINUTES'] + bxdata['SECONDS'] / 60

    ### Basic Share Calculations ###
    bxdata['TIMESHARE'] = bxdata['TIME'] / bxdata['TIME'].sum()
    bxdata['PTSSHARE'] = bxdata['PTS'] / bxdata['PTS'].sum()

    ### Point Capitalization ###
    bxdata['PTSCAP'] = bxdata['TIME'] * bxdata['PTS']
    bxdata['PTSCAPSHARE'] = bxdata['PTSCAP'] / bxdata['PTSCAP'].sum()

    ### Game ID Primary Key ###
    bxdata['GAME_ID'] = NBATEAM_GAMEID[i]
    
    ### Output Check ###
    bxdata = bxdata[[
                'GAME_ID'
                , 'TEAM_ID'
                , 'PLAYER_NAME'
                , 'TIME'
                , 'TIMESHARE'
                , 'PTS'
                , 'PTSSHARE'
                , 'PTSCAP'
                , 'PTSCAPSHARE'
            ]]

    ### HHI Index Calculations ###
    HHI_TS = ( bxdata['TIMESHARE'] ** 2 ).sum()
    HHI_PS = ( bxdata['PTSSHARE'] ** 2 ).sum()
    HHI_PCS = ( bxdata['PTSCAPSHARE'] ** 2 ).sum() 

    ### Updating ###
    bxsdata = pd.concat([bxsdata, bxdata])

    HHI_TS_INDEX.append(HHI_TS)
    HHI_PS_INDEX.append(HHI_PS)
    HHI_PCS_INDEX.append(HHI_PCS)

    time.sleep(2)

### Make Game ID variable an interger for joining compatability ###

bxsdata['GAME_ID'] = bxsdata['GAME_ID'].astype(int)
NBA_GLDATA['Game_ID'] = NBA_GLDATA['Game_ID'].astype(int)
NBA_GLDATA['GAME_DATE'] = pd.to_datetime(NBA_GLDATA['GAME_DATE'])

### Join Game Data to Boxscore Data ###

bxsdata = bxsdata.join(NBA_GLDATA.set_index('Game_ID')[['GAME_DATE', 'MATCHUP', 'WL', 'W_PCT', 'PTS']]
                , on = 'GAME_ID'        
                , how = 'left'
                , lsuffix = '_TEAM')

### HHI Dataframe ###
HHI_DF = pd.DataFrame([NBATEAM_GAMEID, HHI_TS_INDEX, HHI_PS_INDEX, HHI_PCS_INDEX]).T
HHI_DF.columns = ['GAME_ID', 'HHI_TS', 'HHI_PS', 'HHI_PCS']
HHI_DF['GAME_ID'] = HHI_DF['GAME_ID'].astype(int)
HHI_DF = HHI_DF.set_index('GAME_ID')

### Join Data and Save to CSV ###
bxsdata = bxsdata.join(HHI_DF, on = 'GAME_ID', how = 'left')
bxsdata.to_csv('./{} BXS Data.csv'.format(team_name))