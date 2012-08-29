#-*- coding: utf-8 -*-

import sys
from datetime import datetime
import sqlalchemy as sa
import sqlalchemy.sql.functions as func
from sqlalchemy import distinct
from pyramid.paster import bootstrap
from xonstat.models import *

from render import PlayerData, Skin


# maximal number of query results (for testing, set to 0 to get all)
NUM_PLAYERS = None

# we look for players who have activity within the past DELTA hours
DELTA = 6


# classic skin WITHOUT NAME - writes PNGs into "output//###.png"
skin_classic = Skin( "",
        bg              = "asfalt",
    )

# more fancy skin [** WIP **]- writes PNGs into "output/archer/###.png"
skin_archer = Skin( "archer",
        bg              = "background_archer-v1",
        overlay         = "",
    )

# minimal skin - writes PNGs into "output/minimal/###.png"
skin_minimal = Skin( "minimal",
        bg              = None,
        bgcolor         = (0.04, 0.04, 0.04, 1.0),
        overlay         = "overlay_minimal",
        width           = 560,
        height          = 40,
        num_gametypes   = 4,
        gametype_pos    = (25,30),
        gametype_text   = "%s :",
        gametype_width  = 120,
        gametype_fontsize = 10,
        elo_pos         = (75,30),
        elo_text        = "Elo %.0f",
        elo_color       = (1.0, 1.0, 0.6),
        rank_pos        = None,
        nostats_pos     = (80,30),
        nostats_fontsize = 10,
        nostats_angle   = 0,
        nostats_text    = "no stats!",
        kdr_pos         = (392,15),
        kills_pos       = None,
        deaths_pos      = None,
        winp_pos        = (508,15),
        wins_pos        = None,
        loss_pos        = None,
        ptime_pos       = (458,30),
        ptime_color     = (0.8, 0.8, 0.9),
    )

# parse cmdline parameters (for testing)

skins = []
for arg in sys.argv[1:]:
    if arg.startswith("-"):
        arg = arg[1:]
        if arg == "force":
            DELTA = 2**24   # large enough to enforce update, and doesn't result in errors
        elif arg == "test":
            NUM_PLAYERS = 200
        else:
            print """Usage:  gen_badges.py [options] [skin list]
    Options:
        -force      Force updating all badges (delta = 2^24)
        -testing    Limit number of players to 200 (for testing)
        -help       Show this help text
    Skin list:
        Space-separated list of skins to use when creating badges.
        Available skins:  classic, minimal, archer
        If no skins are given, classic and minmal will be used by default.
        NOTE: Output directories must exists before running the program!
"""
        sys.exit(-1)
    else:
        if arg == "classic":
            skins.append(skin_classic)
        elif arg == "minimal":
            skins.append(skin_minimal)
        elif arg == "archer":
            skins.append(skin_archer)

if len(skins) == 0:
    skins = [ skin_classic, skin_minimal ]


# environment setup
env = bootstrap('../../../development.ini')
req = env['request']
req.matchdict = {'id':3}

print "Requesting player data from db ..."
cutoff_dt = datetime.utcnow() - timedelta(hours=DELTA)
start = datetime.now()
players = []
if NUM_PLAYERS:
    players = DBSession.query(distinct(Player.player_id)).\
            filter(Player.player_id == PlayerElo.player_id).\
            filter(Player.player_id == PlayerGameStat.player_id).\
            filter(PlayerGameStat.create_dt > cutoff_dt).\
            filter(Player.nick != None).\
            filter(Player.player_id > 2).\
            filter(Player.active_ind == True).\
            limit(NUM_PLAYERS).all()
else:
    players = DBSession.query(distinct(Player.player_id)).\
            filter(Player.player_id == PlayerElo.player_id).\
            filter(Player.player_id == PlayerGameStat.player_id).\
            filter(PlayerGameStat.create_dt > cutoff_dt).\
            filter(Player.nick != None).\
            filter(Player.player_id > 2).\
            filter(Player.active_ind == True).\
            all()

playerdata = PlayerData()

if len(players) > 0:
    stop = datetime.now()
    td = stop-start
    total_seconds = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
    print "Query took %.2f seconds" % (total_seconds)

    print "Creating badges for %d players ..." % len(players)
    start = datetime.now()
    data_time, render_time = 0,0
    for player_id in players:
        req.matchdict['id'] = player_id

        sstart = datetime.now()
        playerdata.get_data(player_id)
        sstop = datetime.now()
        td = sstop-sstart
        total_seconds = float(td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
        data_time += total_seconds

        sstart = datetime.now()
        for sk in skins:
            sk.render_image(playerdata, "output/%s/%d.png" % (str(sk), player_id[0]))
        sstop = datetime.now()
        td = sstop-sstart
        total_seconds = float(td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
        render_time += total_seconds

    stop = datetime.now()
    td = stop-start
    total_seconds = float(td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
    print "Creating the badges took %.1f seconds (%.3f s per player)" % (total_seconds, total_seconds/float(len(players)))
    print "Total time for rendering images: %.3f s" % render_time
    print "Total time for getting data: %.3f s" % data_time

else:
    print "No active players found!"
