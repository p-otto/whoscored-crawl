import argparse
import re
import ast

import communication
from communication import regionToId, tournamentNameToId
from matchstats import MatchStats, TeamGameStats
from whoscoreddb import Database

db_url = "sqlite:///data/whoscored.sqlite"
db = Database(db_url)


def extractTeamInfo(team_id: str):
    if db.teamExists(int(team_id)):
        return

    print("Fetching team info for " + team_id)

    response = communication.teamPage(str(team_id))
    teamName = re.findall("team-header-name\">([\w\.\-\s]*)<", response)[0]
    db.insertTeamInfo(int(team_id), dict(name=teamName))


def extractPlayerInfo(player_id: str):
    if db.playerExists(int(player_id)):
        return

    print("Fetching player info for " + player_id)

    response = communication.playerPage(player_id)
    playerName = re.findall("content=\"(.*) statistics", response)[0]
    db.insertPlayerInfo(int(player_id), dict(name=playerName))


def extractTeamInfoFromGame(match_id: str, team_id: str) -> TeamGameStats:
    print("Fetching match info: " + match_id + ", team: " + team_id)

    extractTeamInfo(team_id)

    # get player stats
    response = communication.playerStatsForTeam(match_id, team_id)
    playerStats = response.replace("null", "None").replace("true", "True").replace("false", "False")
    playerStats = re.sub("\s+", "", playerStats)  # remove whitespace
    playerStats = ast.literal_eval(playerStats)

    # TODO: filter for useful stats (blacklist?)
    playerStatList = playerStats['playerTableStats']
    playerStatNames = list(playerStatList[0].keys())
    playerStatNames.remove("incidents")  # TODO: add schema for incidents
    allPlayerStats = dict()
    for playerStats in playerStatList:
        curPlayerStats = []
        player_id = playerStats['playerId']
        extractPlayerInfo(str(player_id))
        for key in playerStatNames:
            curPlayerStats.append(playerStats[key])
        allPlayerStats[player_id] = curPlayerStats

    teamGameStats = TeamGameStats(int(team_id))
    teamGameStats.playerStatNames = [Database.stringToAttribute(x) for x in playerStatNames]
    teamGameStats.playerStats = allPlayerStats
    return teamGameStats


def test():
    # test tournament infos
    ti = communication.TournamentInfo(regionToId("Germany"), tournamentNameToId("Bundesliga"), 8, 5)
    assert ti.seasonIdAndLink(2015) == ("4336", "https://www.whoscored.com/Regions/81/Tournaments/3/Seasons/4336")
    assert ti.getStageId("https://www.whoscored.com/Regions/81/Tournaments/3/Seasons/4336") == "9192"
    assert ti.seasonIdAndLink(2014) == ("3863", "https://www.whoscored.com/Regions/81/Tournaments/3/Seasons/3863")
    assert(len(ti.seasonGames(2015))) == 306
    assert(len(ti.seasonGames(2014))) == 306

    # TODO: test games for month and season

    print("Tests done.")


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--test", action="store_true")
    args = argparser.parse_args()

    if args.test:
        test()
        return

    ti = communication.TournamentInfo(regionToId("Germany"), tournamentNameToId("Bundesliga"), 8, 5)
    games = ti.seasonGames(2015)
    for game in games:
        if db.matchExists(game.match_id):
            continue

        db.begin()
        try:
            matchStats = MatchStats(game.match_id)
            matchStats.homeTeamStats = extractTeamInfoFromGame(str(game.match_id), str(game.homeTeam_id))
            matchStats.awayTeamStats = extractTeamInfoFromGame(str(game.match_id), str(game.awayTeam_id))
            db.insertMatchStats(matchStats)
            db.commit()
        except:
            db.rollback()

if __name__ == "__main__":
    main()
