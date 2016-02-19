import dataset
from matchstats import *


class Database:
    def __init__(self, url):
        self.db = dataset.Database(url)

    @staticmethod
    def stringToAttribute(inp: str):
        return inp.replace("-", "_").replace(" ", "_").replace(".", "")

    def insert(self, matchStats: MatchStats):
        statsHome = matchStats.homeTeamStats
        statsAway = matchStats.awayTeamStats
        matchDict = dict(zip(matchStats.statNames, matchStats.stats))
        match_id = self.db['match'].insert(matchDict)

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
