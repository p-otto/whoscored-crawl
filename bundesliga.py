from bs4 import BeautifulSoup
import re

import browser
from matchstats import MatchStats, TeamGameStats
from database import Database


def toNum(val):
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return 0


def extractInfoFromGame(url: str):
    source = browser.getPageSource(url)
    soup = BeautifulSoup(source, "html.parser")

    # extract player stats
    def tableToTeamStats(table):
        stats = table.thead.text.splitlines()
        stats = [x for x in stats if x]
        teamName = stats[0]
        playerStatNames = stats[2:]  # ignore "Spieler" row
        playerStatNames = [Database.stringToAttribute(x) for x in playerStatNames]
        players = table.tbody

        teamStats = TeamGameStats(teamName)
        teamStats.playerStatNames = playerStatNames
        for playerData in players.find_all("tr"):
            playerName = playerData.find("span", {"class": "longName"}).text
            playerStats = playerData.find_all("td")[2:]  # ignore empty and name row
            playerStats = [toNum(x.text) for x in playerStats]
            teamStats.playerStats[playerName] = playerStats

        return teamStats

    elem = soup.find("div", {"id": "wwe-player-tracking-distance"})
    tables = elem.find_all("table")
    homeTable = tables[0]
    awayTable = tables[1]
    homeTeamStats, awayTeamStats = tableToTeamStats(homeTable), tableToTeamStats(awayTable)

    # extract team stats
    def extractValuesFromTag(soup, id_name: str):
        elem = soup.find("div", {"id": id_name})
        if elem is None:
            return False
        children = list(elem.children)
        if len(children) < 2:
            return False
        return children[0].text, children[1].text

    statNames = []
    statIds = re.findall("wwe-data-[\w\-]+", source)
    for statId in statIds:
        values = extractValuesFromTag(soup, statId)
        if values is False:
            continue
        statName = Database.stringToAttribute(statId.replace("wwe-data-", ""))
        statNames.append(statName)
        homeTeamStats.teamStats.append(toNum(values[0]))
        awayTeamStats.teamStats.append(toNum(values[1]))

    homeTeamStats.teamStatNames = list(statNames)
    awayTeamStats.teamStatNames = list(statNames)

    matchStats = MatchStats()
    matchStats.homeTeamStats = homeTeamStats
    matchStats.awayTeamStats = awayTeamStats
    return matchStats


def extractGamesFromDay(url: str):
    source = browser.getPageSource(url)
    matches = set(re.findall("/de/\w*/matches/\d*/\d*/[\w\-\.]*/Analyse/index.jsp", source))
    return matches


def urlForGameday(league: str, year: int, day: int):
    return "http://www.bundesliga.de/de/" + league + "/matches/" + str(year) + "/Spieltags%C3%BCbersicht/#/" + str(day)


def urlForGame(postfix: str):
    return "http://www.bundesliga.de" + postfix


def writeGameDayIntoDb(db: Database, league: str, year: int, day: int):
    urlGameDay = urlForGameday(league, year, day)
    gamePostfixes = extractGamesFromDay(urlGameDay)

    for gamePostfix in gamePostfixes:
        print(gamePostfix)
        urlGame = urlForGame(gamePostfix)
        matchStats = extractInfoFromGame(urlGame)
        db.insert(matchStats)


def test():
    games = extractGamesFromDay(urlForGameday("liga", 2015, 1))
    assert(len(games) == 9)
    # TODO: test for match scraping
    print("Tests passed.")


def main():
    db_url = "sqlite:///data/bundesliga.sqlite"

    try:
        db = Database(db_url)

        for i in range(1, 22):
            print("Spieltag " + str(i))
            writeGameDayIntoDb(db, "liga", 2015, i)
            writeGameDayIntoDb(db, "liga2", 2015, i)
    finally:
        browser.close()


if __name__ == "__main__":
    main()
