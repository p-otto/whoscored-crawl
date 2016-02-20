class MatchStats:
    def __init__(self, match_id: int):
        self.match_id = match_id
        self.statNames = []
        self.stats = []
        self.homeTeamStats = None
        self.awayTeamStats = None


class TeamGameStats:
    def __init__(self, team_id: int):
        self.team_id = team_id
        self.teamStatNames = []
        self.teamStats = []
        self.playerStatNames = []
        self.playerStats = dict()
