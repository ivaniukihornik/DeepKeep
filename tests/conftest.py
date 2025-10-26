from collections.abc import Callable
from uuid import uuid4

import pytest
from faker import Faker
from requests import Response
from fastapi import status

from api_client.endpoints.applications_endpoint import ApplicationsEndpoint
from constants import AUTH_TOKEN_LENGTH

fake = Faker()


@pytest.fixture
def create_applications_endpoint():
    return ApplicationsEndpoint()


@pytest.fixture
def generate_auth_token() -> Callable:
    def _generate():
        return 'Bearer ' + fake.hexify(text='^' * AUTH_TOKEN_LENGTH)

    return _generate


@pytest.fixture
def generate_idempotency_key() -> Callable:
    def _generate():
        return str(uuid4())

    return _generate


@pytest.fixture
def generate_app_payload() -> Callable:
    def _generate():
        return {
            'name': f'{fake.word()}_{fake.word()}',
            'description': fake.text()
        }
    return _generate


@pytest.fixture
def consequent_post_distinct_applications_with_same_token(
        create_applications_endpoint,
        generate_auth_token,
        generate_idempotency_key,
        generate_app_payload
):
    def _post(count_of_apps: int, min_delay_between_requests: int = 0, max_delay_between_requests: int = 1):
        api = create_applications_endpoint
        return api.consequent_post_distinct_applications(
            count_of_apps=count_of_apps,
            auth_token=generate_auth_token(),
            generate_idempotency_key=generate_idempotency_key,
            generate_payload=generate_app_payload,
            min_delay_between_requests=min_delay_between_requests,
            max_delay_between_requests=max_delay_between_requests
        )

    return _post


@pytest.fixture(autouse=True)
def reset_app_state_after_test(create_applications_endpoint):
    yield
    api = create_applications_endpoint
    response: Response = api.reset_app_state()
    if response.status_code != status.HTTP_200_OK:
        raise Exception('Server state was not reset after test')
