from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep
import re
import dataset

db_url = "sqlite:///data/bundesliga.sqlite"
path_to_chromedriver = './chrome/chromedriver'
path_to_adblock = "./chrome/uBlock.crx"
chrome_options = Options()
chrome_options.add_extension(path_to_adblock)
chrome_options.add_argument("--disable-plugins​")
chrome_options.add_argument("--disable-bundled-ppapi-flash​")
browser = webdriver.Chrome(executable_path=path_to_chromedriver, chrome_options=chrome_options)
SLEEP_LENGTH = 5


class TeamGameStats:
    def __init__(self, name):
        self.name = name
        self.teamStatNames = []
        self.teamStats = []
        self.playerStatNames = []
        self.playerStats = dict()

    def __str__(self):
        result = list()
        result.append(self.name)
        result.append(str(self.teamStatNames))
        result.append(str(self.teamStats))
        result.append(str(self.playerStatNames))
        for player, stats in self.playerStats.items():
            result.append(player + " " + str(stats))
        return "\n".join(result)


class Database:
    def __init__(self, url):
        self.db = dataset.Database(url)

    def insert(self, statsHome, statsAway):
        match_id = self.db['match'].insert(dict())

        def insertTeam(stats):
            team = self.db['team'].find_one(name=stats.name)
            if team is None:
                team_id = self.db['team'].insert(dict(name=stats.name))
            else:
                team_id = team['id']

            # insert all stats into the table
            teamMatchDict = dict(zip(stats.teamStatNames, stats.teamStats))

            # insert foreign keys
            teamMatchDict['match_id'] = match_id
            teamMatchDict['team_id'] = team_id

            teamMatch_id = self.db['teamMatchInfo'].insert(teamMatchDict)

            # insert all players of the team into the table
            for playerName, statValues in stats.playerStats.items():
                player = self.db['player'].find_one(name=playerName)
                if player is None:
                    player_id = self.db['player'].insert(dict(name=playerName))
                else:
                    player_id = player['id']

                playerMatchInfoDict = dict(zip(stats.playerStatNames, statValues))
                playerMatchInfoDict['player_id'] = player_id
                playerMatchInfoDict['teamMatch_id'] = teamMatch_id
                self.db['playerMatchInfo'].insert(playerMatchInfoDict)

        insertTeam(statsHome)
        insertTeam(statsAway)

        self.db.commit()


def toNum(val):
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return 0


def extractValuesFromTag(soup, id_name):
    elem = soup.find("div", {"id": id_name})
    if elem is None:
        return False
    children = list(elem.children)
    if len(children) < 2:
        return False
    return children[0].text, children[1].text


def getPageSource(url):
    browser.get(url)
    sleep(SLEEP_LENGTH)
    source = browser.page_source
    return source


def stringToAttribute(inp):
    return inp.replace("-", "_").replace(" ", "_").replace(".", "")


def extractInfoFromGame(url):
    source = getPageSource(url)
    soup = BeautifulSoup(source, "html.parser")

    # extract player stats
    def tableToTeamStats(table):
        stats = table.thead.text.splitlines()
        stats = [x for x in stats if x]
        teamName = stats[0]
        playerStatNames = stats[2:]  # ignore "Spieler" row
        playerStatNames = [stringToAttribute(x) for x in playerStatNames]
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
    statNames = []
    statIds = re.findall("wwe-data-[\w\-]+", source)
    for statId in statIds:
        values = extractValuesFromTag(soup, statId)
        if values is False:
            continue
        statName = stringToAttribute(statId.replace("wwe-data-", ""))
        statNames.append(statName)
        homeTeamStats.teamStats.append(toNum(values[0]))
        awayTeamStats.teamStats.append(toNum(values[1]))

    homeTeamStats.teamStatNames = list(statNames)
    awayTeamStats.teamStatNames = list(statNames)

    return homeTeamStats, awayTeamStats


def extractGamesFromDay(url):
    source = getPageSource(url)
    matches = set(re.findall("/de/\w*/matches/\d*/\d*/[\w\-\.]*/Analyse/index.jsp", source))
    return matches


def urlForGameday(leagueString, year, day):
    return "http://www.bundesliga.de/de/" + leagueString + "/matches/" + str(year) + "/Spieltags%C3%BCbersicht/#/" + str(day)


def urlForGame(postfix):
    return "http://www.bundesliga.de" + postfix


def writeGameDayIntoDb(db, league, year, day):
    urlGameDay = urlForGameday(league, year, day)
    gamePostfixes = extractGamesFromDay(urlGameDay)

    for gamePostfix in gamePostfixes:
        print(gamePostfix)
        urlGame = urlForGame(gamePostfix)
        homeStats, awayStats = extractInfoFromGame(urlGame)
        db.insert(homeStats, awayStats)


def test():
    games = extractGamesFromDay(urlForGameday("liga", 2015, 1))
    assert(len(games) == 9)
    # TODO: test for match scraping
    print("Tests passed.")


def main():
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
