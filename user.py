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