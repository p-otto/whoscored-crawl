from bs4 import BeautifulSoup
import re
from datetime import date, datetime
import requests
import ast

#import browser
from matchstats import MatchStats, TeamGameStats
from database import Database


class MatchInfo:
    def __init__(self, match_id, homeTeam_id, awayTeam_id):
        self.match_id = match_id
        self.homeTeam_id = homeTeam_id
        self.awayTeam_id = awayTeam_id


def toNum(val):
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return 0


def whoScoredHeader() -> dict:
    headers = dict()
    headers['Host'] = "www.whoscored.com"
    headers['User-Agent'] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.109 Safari/537.36"
    headers['X-Requested-With'] = "XMLHttpRequest"
    headers['Accept-Language'] = "en-US,en;q=0.8,de;q=0.6"
    return headers


def whoScoredMatchList(daystring: str) -> requests.Response:
    url = "https://www.whoscored.com/matchesfeed/?d=" + daystring
    headers = whoScoredHeader()
    headers['Accept'] = "text/plain, */*; q=0.01"
    headers['Referer'] = "https://www.whoscored.com/LiveScores"
    return requests.get(url, headers=headers)


def whoScoredPlayerInfo(match_id: str, team_id: str) -> requests.Response:
    liveStatPage = "https://www.whoscored.com/Matches/" + match_id + "/LiveStatistics"

    def getModelLastMode() -> str:
        source = requests.get(liveStatPage, headers=whoScoredHeader()).text
        match = re.search("Model-Last-Mode\': \'(.*)\'", source)
        return match.group(1)

    # TODO: check if category=passing ... return different values
    url = "https://www.whoscored.com/StatisticsFeed/1/GetMatchCentrePlayerStatistics?category=summary&subcategory=all&statsAccumulationType=0&isCurrent=true&playerId=&teamIds=" + team_id + "&matchId=" + match_id + "&stageId=&tournamentOptions=&sortBy=&sortAscending=&age=&ageComparisonType=&appearances=&appearancesComparisonType=&field=&nationality=&positionOptions=&timeOfTheGameEnd=&timeOfTheGameStart=&isMinApp=&page=&includeZeroValues=&numberOfPlayersToPick="
    headers = whoScoredHeader()
    headers['Accept'] = "application/json, text/javascript, */*; q=0.01"
    headers['Referer'] = liveStatPage
    headers['Accept-Encoding'] = "gzip, deflate, sdch"
    headers['Model-Last-Mode'] = getModelLastMode()
    return requests.get(url, headers=headers)


def extractTeamInfoFromGame(match_id: str, team_id: str) -> TeamGameStats:
    # TODO: replace with proper schema for teams
    url = "https://www.whoscored.com/Teams/" + team_id
    response = requests.get(url, headers=whoScoredHeader()).text
    teamName = re.findall("team-header-name\">([\w\.\-]*)<", response)[0]

    # get player stats
    response = whoScoredPlayerInfo(match_id, team_id)
    playerInfo = response.text.replace("null", "None").replace("true", "True").replace("false", "False")
    playerInfo = re.sub("\s+", "", playerInfo)  # remove whitespace
    playerInfo = ast.literal_eval(playerInfo)

    # TODO: filter for useful stats
    playerStatList = playerInfo['playerTableStats']
    playerStatNames = list(playerStatList[0].keys())
    playerStatNames.remove("incidents")  # TODO: add schema for incidents
    allPlayerStats = dict()
    for playerStats in playerStatList:
        curPlayerStats = []
        player_id = playerStats['playerId']
        for key in playerStatNames:
            curPlayerStats.append(playerStats[key])
        allPlayerStats[player_id] = curPlayerStats

    teamGameStats = TeamGameStats(teamName)
    teamGameStats.playerStatNames = [Database.stringToAttribute(x) for x in playerStatNames]
    teamGameStats.playerStats = allPlayerStats
    return teamGameStats


def extractGamesFromDay(gamedate: date) -> [MatchInfo]:
    response = whoScoredMatchList(gamedate.isoformat().replace("-", ""))
    matchList = response.text

    while True:
        last = str(matchList)
        matchList = re.sub(',,', ',0,', matchList)
        if matchList == last:
            break

    matchList = ast.literal_eval(matchList)
    leagues = matchList[1]
    matches = matchList[2]

    matchInfos = []
    for match in matches:
        match_id = match[1]
        statsAvailable = bool(match[15])

        if statsAvailable:
            home_id = match[4]
            away_id = match[8]
            matchInfos.append(MatchInfo(match_id, home_id, away_id))

    return matchInfos

def test():
    matchInfos = extractGamesFromDay(date(2016, 2, 15))
    assert len(matchInfos) == 2
    print("Tests done.")


def main():
    db_url = "sqlite:///data/whoscored.sqlite"

    db = Database(db_url)

    matchInfos = extractGamesFromDay(date(2016, 2, 15))
    for matchInfo in matchInfos:
        homeStats = extractTeamInfoFromGame(str(matchInfo.match_id), str(matchInfo.homeTeam_id))
        awayStats = extractTeamInfoFromGame(str(matchInfo.match_id), str(matchInfo.awayTeam_id))
        matchStats = MatchStats()
        matchStats.homeTeamStats = homeStats
        matchStats.awayTeamStats = awayStats
        db.insert(matchStats)


if __name__ == "__main__":
    main()
