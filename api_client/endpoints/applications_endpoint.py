import time
from random import uniform
from typing import Callable

from requests import Response

from api_client.base_api_client import BaseApiClient
from constants import APPLICATIONS_ENDPOINT, APPLICATION_ENDPOINT, RESET_ENDPOINT


class ApplicationsEndpoint(BaseApiClient):
    def __init__(
            self,
            applications_endpoint: str = APPLICATIONS_ENDPOINT,
            application_endpoint: str = APPLICATION_ENDPOINT,
            reset_endpoint: str = RESET_ENDPOINT
    ):
        super().__init__()
        self.applications_endpoint = applications_endpoint
        self.application_endpoint = application_endpoint
        self.reset_endpoint = reset_endpoint

    def get_applications(self) -> Response:
        return self._get(self.applications_endpoint)

    def get_applications_count(self) -> int:
        return len(self.get_applications().json())

    def get_application(self, app_id: str) -> Response:
        return self._get(self.application_endpoint.format(app_id=app_id))

    def post_application(self, authorization: str, idempotency_key: str, payload: dict) -> Response:
        return self._post(
            endpoint=self.applications_endpoint,
            headers={
                'Authorization': authorization,
                'Idempotency-Key': idempotency_key
            },
            payload=payload
        )

    def respect_retry_posting_after(self, authorization: str, idempotency_key: str, payload: dict, retry_after_s: int) \
            -> Response:
        time.sleep(retry_after_s)
        return self.post_application(
            authorization=authorization,
            idempotency_key=idempotency_key,
            payload=payload
        )

    def parallel_post_the_same_application(
            self,
            number_of_apps: int,
            authorization: str,
            idempotency_key: str,
            payload: dict
    ) -> list[Response]:
        return self._run_parallel_requests(
            self.post_application,
            number_of_apps,
            authorization,
            idempotency_key,
            payload
        )

    def consequent_post_distinct_applications(
            self,
            count_of_apps: int,
            auth_token: str,
            generate_idempotency_key: Callable,
            generate_payload: Callable,
            min_delay_between_requests: int = 0,
            max_delay_between_requests: int = 5
    ) -> list[Response]:
        responses = []
        for try_number in range(count_of_apps):
            response = self.post_application(
                authorization=auth_token,
                idempotency_key=generate_idempotency_key(),
                payload=generate_payload()
            )
            responses.append(response)
            if try_number < count_of_apps - 1:
                time.sleep(uniform(min_delay_between_requests, max_delay_between_requests))

        return responses

    def patch_application(self, app_id: str, authorization: str, if_match: str, payload: dict, is_force: bool = False) \
            -> Response:
        endpoint = self.application_endpoint.format(app_id=app_id)
        if is_force:
            endpoint = endpoint + '?force=true'
        return self._patch(
            endpoint=endpoint,
            headers={
                'Authorization': authorization,
                'If-Match': if_match
            },
            payload=payload
        )

    def parallel_patch_the_same_application(
            self,
            number_of_requests: int,
            authorization: str,
            app_id: str,
            if_match: str,
            generate_payload: Callable
    ) -> list[Response]:
        return self._run_parallel_requests(
            self.patch_application,
            number_of_requests,
            app_id,
            authorization,
            if_match,
            generate_payload
        )

    def reset_app_state(self):
        return self._post(endpoint=self.reset_endpoint)
