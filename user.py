from typing import List, Dict, Tuple
import random
import logging

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
        self._shuffled_based_on_signature: Tuple[str, ...] = tuple()
        self.voted_on: Dict[str, str] = {}

    def get_votes_for(self) -> int:
        return self.votes_for

    def get_votes_against(self) -> int:
        return self.votes_against

    def get_name(self) -> str:
        return self.name

    def get_films(self) -> List[str]:
        return self.films

    def get_id(self) -> int:
        return self.id

    def get_shuffled_films(self) -> Dict[int, str]:
        return self.shuffled_films

    def get_voted_on(self) -> Dict[str, str]:
        return self.voted_on

    def add_vote_on(self, film_name: str):
        self.voted_on[film_name] = 'за'
        self.votes_for += 1

    def add_vote_against(self, film_name: str):
        self.voted_on[film_name] = 'против'
        self.votes_against += 1

    def has_voted_for(self, film_name: str) -> bool:
        return self.voted_on.get(film_name) == 'за'

    def has_voted_agains(self, film_name: str) -> bool:
        return self.voted_on.get(film_name) == 'против'

    def reset_votes(self):
        self.votes_for = 0 
        self.votes_against = 0 
        self.voted_on.clear()
        logging.info(f"Votes for user {self.user_id} ({self.name}) have been reset.")


    def ensure_shuffled_list_exists(self, current_global_film_names: List[str]):
        current_signature = tuple(sorted(current_global_film_names))

        if not self.shuffled_films or self._shuffled_based_on_signature != current_signature:
            if not current_global_film_names:
                self.shuffled_films = {}
                self._shuffled_based_on_signature = tuple()
                return

            user_specific_list_to_shuffle = list(current_global_film_names)
            random.shuffle(user_specific_list_to_shuffle)

            self.shuffled_films.clear()
            for i, film_name in enumerate(user_specific_list_to_shuffle):
                self.shuffled_films[i + 1] = film_name

            self._shuffled_based_on_signature = current_signature
            logging.info(
                f"User {self.id} ({self.name}): Personal film list (re)shuffled with {len(self.shuffled_films)} items.")

    def get_votes(self) -> Dict[str, bool]:
        raise NotImplementedError("self.votes is not initialized or used in the current bot logic.")
