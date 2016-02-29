import re
import requests
import bs4
import ast
from time import sleep
from random import randrange
from bs4 import BeautifulSoup
from datetime import date

WAIT_TIME = 5
WAIT_RANGE = 2


def whoScoredHeader(isXHtml: bool = True) -> dict:
    result = {
        'Host': "www.whoscored.com",
        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.109 Safari/537.36",
        'Accept-Language': "en-US,en;q=0.8,de;q=0.6",
        'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    if isXHtml:
        result['X-Requested-With'] = "XMLHttpRequest"
    return result


def getRequest(url, headers):
    waitTime = randrange(WAIT_TIME - WAIT_RANGE, WAIT_TIME + WAIT_RANGE + 1)
    sleep(waitTime)
    return requests.get(url, headers=headers)


def getModelLastMode(page: str) -> str:
    source = getRequest(page, headers=whoScoredHeader(False)).text
    match = re.search("Model-Last-Mode\':\s*\'(.*)\'", source)
    return match.group(1)


def playerStatsForTeam(match_id: str, team_id: str) -> str:
    liveStatPage = "https://www.whoscored.com/Matches/" + match_id + "/LiveStatistics"

    # TODO: check if category=passing ... return different values
    url = "https://www.whoscored.com/StatisticsFeed/1/GetMatchCentrePlayerStatistics?category=summary&subcategory=all&statsAccumulationType=0&isCurrent=true&playerId=&teamIds=" + team_id + "&matchId=" + match_id + "&stageId=&tournamentOptions=&sortBy=&sortAscending=&age=&ageComparisonType=&appearances=&appearancesComparisonType=&field=&nationality=&positionOptions=&timeOfTheGameEnd=&timeOfTheGameStart=&isMinApp=&page=&includeZeroValues=&numberOfPlayersToPick="
    referer = liveStatPage
    headers = whoScoredHeader()
    headers['Accept'] = "application/json, text/javascript, */*; q=0.01"
    headers['Referer'] = referer
    headers['Accept-Encoding'] = "gzip, deflate, sdch"
    headers['Model-Last-Mode'] = getModelLastMode(referer)
    return getRequest(url, headers=headers).text


def teamPage(team_id: str) -> str:
    url = "https://www.whoscored.com/Teams/" + team_id
    return getRequest(url, headers=whoScoredHeader()).text


def playerPage(player_id: str) -> str:
    url = "https://www.whoscored.com/Players/" + player_id
    return getRequest(url, headers=whoScoredHeader()).text


def tournamentNameToId(name):
    tounamentDict = {
        "PremierLeague": 2,
        "Bundesliga": 3,
        "LaLiga": 4,
        "Championship": 7,
        "Ligue1": 22,
        "Eredivisie": 13,
        "SerieA": 5
    }
    id = tounamentDict.get(name, -1)
    assert id != -1

    return id


def regionToId(name):
    regionDict = {
        "England": 252,
        "Germany": 81,
        "Spain": 206,
        "France": 74,
        "Netherlands": 155,
        "Italy": 108
    }
    id = regionDict.get(name, -1)
    assert id != -1

    return id


class MatchInfo:
    def __init__(self, match_id, homeTeam_id, awayTeam_id):
        self.match_id = match_id
        self.homeTeam_id = homeTeam_id
        self.awayTeam_id = awayTeam_id


class TournamentInfo:
    def __init__(self, region_id: int, tournament_id: int, startMonth: int, endMonth: int):
        self.region_id = region_id
        self.tournament_id = tournament_id
        self.startMonth = startMonth
        self.endMonth = endMonth
        self.tournamentPage = "https://www.whoscored.com/Regions/" + str(self.region_id) + "/Tournaments/" + str(self.tournament_id)

    def seasonIdAndLink(self, endYear: int):
        url = self.tournamentPage
        response = getRequest(url, headers=whoScoredHeader(isXHtml=False))
        soup = BeautifulSoup(response.text, "html.parser")
        seasons = soup.find("select", {"name": "seasons"}).contents
        seasons = [x for x in seasons if type(x) == bs4.Tag]
        season_id = None
        for seasonTag in seasons:
            seasonEndYear = seasonTag.text.split("/")[1]
            if int(seasonEndYear) == endYear:
                linkSuffix = seasonTag.attrs['value']
                season_id = linkSuffix.split("/")[-1]
                break
        assert season_id is not None

        return season_id, url + "/Seasons/" + season_id

    def getStageId(self, seasonLink: str) -> str:
        source = getRequest(seasonLink, headers=whoScoredHeader(isXHtml=False)).text
        match = re.search("/Stages/(\d*)/", source)
        return match.group(1)

    def monthGames(self, referer: str, modelLastMode: str, stage_id: str, arg: str) -> [MatchInfo]:
        url = "https://www.whoscored.com/tournamentsfeed/" + stage_id + "/Fixtures/?d=" + arg + "&isAggregate=false"
        headers = whoScoredHeader()
        headers['Accept'] = "text/plain, */*; q=0.01"
        headers['Referer'] = referer
        headers['Model-Last-Mode'] = modelLastMode
        headers['Accept-Encoding'] = "gzip, deflate, sdch"

        matchList = getRequest(url, headers=headers).text
        matchList = ast.literal_eval(matchList)

        matchInfos = []
        for match in matchList:
            match_id = match[0]
            home_id = match[4]
            away_id = match[7]
            matchInfos.append(MatchInfo(match_id, home_id, away_id))

        return matchInfos

    def seasonGames(self, endYear: int) -> [MatchInfo]:
        def appendMonth(inp: date):
            if inp.month == 12:
                return inp.replace(year=inp.year+1, month=1)
            return inp.replace(month=inp.month+1)

        season_id, seasonLink = self.seasonIdAndLink(endYear)
        stage_id = self.getStageId(seasonLink)

        referer = self.tournamentPage + "/Seasons/" + season_id + "/Stages/" + stage_id
        modelLastMode = getModelLastMode(referer)

        startYear = endYear - 1
        startDate = date(startYear, self.startMonth, 1)
        endDate = date(endYear, self.endMonth, 28)

        curDate = startDate
        result = []
        while curDate < endDate:
            arg = curDate.isoformat().split("-")
            arg = arg[0] + arg[1]
            result.extend(self.monthGames(referer, modelLastMode, stage_id, arg))
            curDate = appendMonth(curDate)

        return result
