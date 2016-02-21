import dataset
from matchstats import *


class Database:
    def __init__(self, url):
        self.db = dataset.Database(url)

    @staticmethod
    def stringToAttribute(inp: str):
        return inp.replace("-", "_").replace(" ", "_").replace(".", "")

    def begin(self):
        self.db.begin()

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    def teamExists(self, team_id: int) -> bool:
        team = self.db['team'].find_one(id=team_id)
        return team is not None

    def insertTeamInfo(self, team_id: int, teamInfoDict: dict):
        teamInfoDict['id'] = team_id
        self.db['team'].insert(teamInfoDict)

    def playerExists(self, player_id: int) -> bool:
        player = self.db['player'].find_one(id=player_id)
        return player is not None

    def insertPlayerInfo(self, player_id: int, playerInfoDict: dict):
        playerInfoDict['id'] = player_id
        self.db['player'].insert(playerInfoDict)

    def matchExists(self, match_id: int) -> bool:
        match = self.db['match'].find_one(id=match_id)
        return match is not None

    def insertMatchStats(self, matchStats: MatchStats):
        statsHome = matchStats.homeTeamStats
        statsAway = matchStats.awayTeamStats
        matchDict = dict(zip(matchStats.statNames, matchStats.stats))
        matchDict['id'] = matchStats.match_id
        self.db['match'].insert(matchDict)

        def insertTeam(teamStats: TeamGameStats):
            assert self.teamExists(teamStats.team_id)

            # insert all stats into the table
            teamMatchDict = dict(zip(teamStats.teamStatNames, teamStats.teamStats))

            # insert foreign keys
            teamMatchDict['match_id'] = matchStats.match_id
            teamMatchDict['team_id'] = teamStats.team_id

            teamMatch_id = self.db['teamMatchInfo'].insert(teamMatchDict)

            # insert all players of the team into the table
            for player_id, statValues in teamStats.playerStats.items():
                assert self.playerExists(player_id)

                playerMatchInfoDict = dict(zip(teamStats.playerStatNames, statValues))
                playerMatchInfoDict['player_id'] = player_id
                playerMatchInfoDict['teamMatch_id'] = teamMatch_id
                self.db['playerMatchInfo'].insert(playerMatchInfoDict)

        insertTeam(statsHome)
        insertTeam(statsAway)
