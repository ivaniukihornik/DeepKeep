from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

import requests
from requests import Response

from constants import BASE_URL


class BaseApiClient:
    def __init__(self, base_url: str = BASE_URL):
        self._base_url = base_url

    def _get(self, endpoint: str) -> requests.Response:
        response = requests.get(url=self._base_url + endpoint, verify=False)
        return response

    def _post(self, endpoint: str, headers: dict = None, payload: dict = None) -> requests.Response:
        response = requests.post(url=self._base_url + endpoint, headers=headers, json=payload, verify=False)
        return response

    def _patch(self, endpoint: str, headers: dict = None, payload: dict = None) -> requests.Response:
        response = requests.patch(url=self._base_url + endpoint, headers=headers, json=payload, verify=False)
        return response

    @staticmethod
    def _run_parallel_requests(request: Callable, number_of_requests: int, *args, **kwargs) -> list[Response]:
        responses = []
        with ThreadPoolExecutor(max_workers=number_of_requests) as executor:
            futures = [executor.submit(request, *args, **kwargs) for _ in range(number_of_requests)]
            for future in as_completed(futures):
                responses.append(future.result())

        return responses
