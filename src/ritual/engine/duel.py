from ritual.engine.errors import CombatFullException
from ritual.types.types import CombatParticipant, Duel


class DuelEngine():
    def __init__(self, duel: Duel) -> None:
        self.duel: Duel = duel
        self.low_team_id: int = -1
        self.high_team_id: int = -1

    def teams(self) -> dict[int, list[CombatParticipant]]:
        teams: dict[int, list[CombatParticipant]] = {}
        for cbt in self.duel.m_flatParticipantList:
            if cbt is None:
                continue
            teams.get(cbt.m_teamID, []).append(cbt)
        return teams


    def add_participant(self, participant: CombatParticipant):
        cur_teams = self.teams()
        if participant.m_teamID in cur_teams:
            p_team = cur_teams[participant.m_teamID]
            if len(p_team) < 4:
                self.duel.m_flatParticipantList.append(participant)
            else:
                raise CombatFullException()
        elif self.low_team_id == -1:
            self.low_team_id = participant.m_teamID
            self.duel.m_flatParticipantList.append(participant)
        elif self.high_team_id == -1:
            self.high_team_id = participant.m_teamID
            self.duel.m_flatParticipantList.append(participant)
        else:
            raise CombatFullException()