from typing import List, Dict

'''
votes = {
    film1: bool
    ...
    filmn: bool
}

'''

class User():
    def __init__(self, name: str, films: List[str], id: int):
        self.name: str = name
        self.films: List[str] = films
        self.votes_for: int = 0
        self.votes_against: int = 0
        self.id: int = id
        self.shuffled_films: Dict[int, str] = {}

    def get_votes_for(self) -> int:
        return self.votes_for

    def get_votes_against(self) -> int:
        return self.votes_against 

    def get_name(self) -> str:
        return self.name

    def get_films(self) -> List[str]:
        return self.films

    def get_votes(self) -> Dict[str, bool]:
        return self.votes

    def get_id(self) -> int:
        return self.id

    def get_shuffled_films(self) -> Dict[int, str]:
        return self.shuffled_films

