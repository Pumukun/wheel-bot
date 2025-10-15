# state.py 
from typing import Dict, List
from user import User

# TODO: Это временное решение для изоляции Глобальных переменных 
# в идеале, все состояния нужно хранить в бд
# а состояние процесса голосования - управляться через FSM (Finite State Machine).

users: Dict[int, User] = {}
film_ratings: Dict[str, int] = {}

fallback_shuffled_films_cache: Dict[int, str] = {}
cached_results_string: str = ""

is_voting: bool = False
final_results_calculated: bool = False
fallback_cache_is_fresh: bool = False
