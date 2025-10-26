import time
from typing import Callable

from constants import RATE_LIMIT, ACTIVATION_DELAY_S


def get_expected_count_of_success_responses(actual_number_of_responses: int, rate_limit: int = RATE_LIMIT):
    return actual_number_of_responses if actual_number_of_responses < rate_limit else rate_limit


def get_expected_count_of_overrated_responses(actual_number_of_responses: int, rate_limit: int = RATE_LIMIT):
    return actual_number_of_responses - rate_limit if actual_number_of_responses > rate_limit else 0


def retry_until(predicate: Callable, timeout: float = ACTIVATION_DELAY_S + 1, interval: float = 0.25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(interval)
    raise AssertionError(f'Condition is not met within {timeout}s')
