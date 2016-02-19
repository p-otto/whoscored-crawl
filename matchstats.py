class MatchStats:
    def __init__(self):
        self.statNames = []
        self.stats = []
        self.homeTeamStats = None
        self.awayTeamStats = None


class TeamGameStats:
    def __init__(self, name:str ):
        self.name = name
        self.teamStatNames = []
        self.teamStats = []
        self.playerStatNames = []
        self.playerStats = dict()
