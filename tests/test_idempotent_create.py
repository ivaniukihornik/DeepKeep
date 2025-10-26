import time

from fastapi import status

from constants import RATE_UPDATING_PERIOD_S, ALLOWABLE_RETRY_AFTER_DEVIATION_S
from utils import helpers


def test_idempotent_create(
        create_applications_endpoint,
        generate_auth_token,
        generate_idempotency_key,
        generate_app_payload,
        consequent_post_distinct_applications_with_same_token
):
    api = create_applications_endpoint
    method = 'POST'
    path = api.applications_endpoint

    # 1. Concurrency/idempotency
    n = 3  # number of parallel requests
    initial_applications_count = api.get_applications_count()
    responses = api.parallel_post_the_same_application(
        number_of_apps=n,
        authorization=generate_auth_token(),
        idempotency_key=generate_idempotency_key(),
        payload=generate_app_payload()
    )
    final_applications_count = api.get_applications_count()
    assert final_applications_count - initial_applications_count == 1, \
        (f'{method} {path} with same idempotency key: expected 1 app to be created!'
         f'Actual created: {final_applications_count - initial_applications_count}')

    success_responses = [response for response in responses if response.status_code == status.HTTP_201_CREATED]
    actual_count_of_success_responses = len(success_responses)
    expected_count_of_success_responses = helpers.get_expected_count_of_success_responses(n)
    assert actual_count_of_success_responses == expected_count_of_success_responses, \
        (f'{method} {path}: expected {expected_count_of_success_responses} success responses under rate limit, '
         f'got {actual_count_of_success_responses}, status codes={[r.status_code for r in responses]}')

    control_response_body = success_responses[0].json()
    mismatches = [response.json() for response in success_responses if response.json() != control_response_body]
    assert not mismatches, \
        (f'{method} {path}: success response bodies mismatch!\n'
         f'control_body={control_response_body}\n mismatches={mismatches}')

    # 2. Rate limiting
    n = 7  # number of distinct requests
    auth_token = generate_auth_token()
    start_time = time.time()
    responses = consequent_post_distinct_applications_with_same_token(
        count_of_apps=n,
        min_delay_between_requests=0,
        max_delay_between_requests=2
    )
    finish_time = time.time()
    actual_requests_time = finish_time - start_time
    if actual_requests_time >= RATE_UPDATING_PERIOD_S:
        raise RuntimeError(f'{method} {path}: requests execution time {actual_requests_time}s exceeds '
                           f'RATE_UPDATING_PERIOD ({RATE_UPDATING_PERIOD_S}s). Fix it to meet rate limit!')

    overrated_responses = [response for response in responses
                           if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS]
    actual_count_of_overrated_responses = len(overrated_responses)
    expected_count_of_overrated_responses = helpers.get_expected_count_of_overrated_responses(n)
    if expected_count_of_overrated_responses < 1:
        raise ValueError(f'{method} {path}: no {status.HTTP_429_TOO_MANY_REQUESTS} responses detected. '
                         f'Check test/API correctness')

    assert actual_count_of_overrated_responses == expected_count_of_overrated_responses, \
        (f'{method} {path}: expected {expected_count_of_overrated_responses} {status.HTTP_429_TOO_MANY_REQUESTS} '
         f'responses, got {actual_count_of_overrated_responses}, statuses={[r.status_code for r in responses]}')

    last_retry_after_s = min([int(response.headers['Retry-After']) for response in overrated_responses])
    expected_seconds_for_success_request = RATE_UPDATING_PERIOD_S - actual_requests_time
    assert abs(expected_seconds_for_success_request - last_retry_after_s) <= ALLOWABLE_RETRY_AFTER_DEVIATION_S, \
        (f'{method} {path}: invalid Retry-After header, '
         f'expected ~{expected_seconds_for_success_request}s, got {last_retry_after_s}s')

    response = api.respect_retry_posting_after(
        authorization=auth_token,
        idempotency_key=generate_idempotency_key(),
        payload=generate_app_payload(),
        retry_after_s=last_retry_after_s
    )
    assert response.status_code == status.HTTP_201_CREATED, \
        (f'{method} {path} after waiting {last_retry_after_s}s: '
         f'expected {status.HTTP_201_CREATED}, got {response.status_code}')

    # 3. Negative idempotency
    auth_token = generate_auth_token()
    idempotency_key = generate_idempotency_key()

    initial_applications_count = api.get_applications_count()
    first_response = api.post_application(
        authorization=auth_token,
        idempotency_key=idempotency_key,
        payload=generate_app_payload()
    )
    second_response = api.post_application(
        authorization=auth_token,
        idempotency_key=idempotency_key,
        payload=generate_app_payload()
    )
    final_applications_count = api.get_applications_count()
    assert final_applications_count - initial_applications_count == 1, \
        (f'{method} {path} with same idempotency_key={idempotency_key}: '
         f'expected 1 created, got {final_applications_count - initial_applications_count}')

    assert first_response.json() == second_response.json(), \
        (f'{method} {path} with same idempotency_key={idempotency_key}: '
         f'expected second response to equal first:\n'
         f'first={first_response.json()}\n second={second_response.json()}')
