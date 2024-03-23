from typing import List, Dict

'''
votes = {
    film1: bool
    ...
    filmn: bool
}

'''

class User():
    __init__(self, name: str, films: List[str], votes: Dict[str, bool], id: int):
        self.name: str = name
        self.films: List[str] = films
        self.votes: Dict[str, bool] = votes
        self.id: int = id

    def get_protiv_num(self) -> int:
        cnt: int = 0
        for vote in self.votes:
            if self.votes[vote] == False:
                cnt += 1
        return cnt

    def get_za_num(self) -> int:
        cnt: int = 0
        for vote in self.votes:
            if self.votes[vote] == True:
                cnt += 1
        return cnt

    def get_name(self) -> str:
        return self.name

    def get_films(self) -> List[str]:
        return self.films

    def get_votes(self) -> Dict[str, bool]:
        return self.votes

