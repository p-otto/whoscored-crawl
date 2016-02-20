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
    response = communication.playerInfo(match_id, team_id)
    playerInfo = response.replace("null", "None").replace("true", "True").replace("false", "False")
    playerInfo = re.sub("\s+", "", playerInfo)  # remove whitespace
    playerInfo = ast.literal_eval(playerInfo)

    # TODO: filter for useful stats (blacklist?)
    playerStatList = playerInfo['playerTableStats']
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
    """curDate = date(2010, 1, 1)

    while curDate < date(2016, 1, 1):
        matchInfos = extractGamesFromDay(curDate)
        for matchInfo in matchInfos:
            if db.matchExists(matchInfo.match_id):
                print("Match " + str(matchInfo.match_id) + " already in DB")
                continue

            homeStats = extractTeamInfoFromGame(str(matchInfo.match_id), str(matchInfo.homeTeam_id))
            awayStats = extractTeamInfoFromGame(str(matchInfo.match_id), str(matchInfo.awayTeam_id))
            matchStats = MatchStats(matchInfo.match_id)
            matchStats.homeTeamStats = homeStats
            matchStats.awayTeamStats = awayStats
            db.insertMatchStats(matchStats)
        curDate += timedelta(days=1)"""

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--test", action="store_true")
    args = argparser.parse_args()

    if args.test:
        test()
    else:
        ti = communication.TournamentInfo(regionToId("Germany"), tournamentNameToId("Bundesliga"), 8, 5)
        print(len(ti.seasonGames(2015)))

if __name__ == "__main__":
    main()
