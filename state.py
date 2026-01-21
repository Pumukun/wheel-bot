# state.py 
from typing import Dict, List
from user import User
from enum import Enum, auto 

# TODO: Это временное решение для изоляции Глобальных переменных 
# в идеале, все состояния нужно хранить в бд
# а состояние процесса голосования - управляться через FSM (Finite State Machine).

class VotingStatus(Enum):
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    FINISHED = auto()

users: Dict[int, User] = {}
film_ratings: Dict[str, int] = {}

fallback_shuffled_films_cache: Dict[int, str] = {}
cached_results_string: str = ""
fallback_cache_is_fresh: bool = False

current_status: VotingStatus = VotingStatus.NOT_STARTED
final_results_calculated: bool = False