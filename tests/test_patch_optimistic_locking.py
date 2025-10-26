from random import randint, choice

from fastapi import status
from constants import RATE_LIMIT, NAME_FORBIDS_ACTIVATION_CODE, ACTIVATION_MODE
from utils.helpers import retry_until


def test_patch_optimistic_locking(
        create_applications_endpoint,
        generate_auth_token,
        generate_idempotency_key,
        consequent_post_distinct_applications_with_same_token
):
    api = create_applications_endpoint
    method = 'PATCH'
    path = api.application_endpoint

    # 1. Normalization & uniqueness
    responses = consequent_post_distinct_applications_with_same_token(count_of_apps=randint(1, RATE_LIMIT))
    my_app_response = api.post_application(
        authorization=generate_auth_token(),
        idempotency_key=generate_idempotency_key(),
        payload={'name': ' My-App '}
    )
    random_app = choice(responses).json()
    authorization = generate_auth_token()
    response = api.patch_application(
        app_id=random_app['id'],
        authorization=authorization,
        if_match=random_app['etag'],
        payload={'name': 'my-app'}
    )
    assert response.status_code == status.HTTP_409_CONFLICT, \
        (f'{method} {path.format(random_app['id'])} returned {response.status_code}. '
         f'Expected {status.HTTP_409_CONFLICT} due to non-unique normalized name.')
    actual_app_state = api.get_application(random_app['id']).json()
    assert actual_app_state == random_app, \
        f'Expected GET {path.format(random_app['id'])} to return initial app state after conflict!'

    # 2. Two-writer race with If-Match
    n = 2  # count of concurrent patches
    my_app = my_app_response.json()
    my_app_id = my_app['id']
    responses = api.parallel_patch_the_same_application(
        number_of_requests=n,
        authorization=authorization,
        app_id=my_app_id,
        if_match=my_app['etag'],
        generate_payload={'name': 'my_updated_app'}
    )
    success_responses = [response for response in responses if response.status_code == status.HTTP_200_OK]
    assert len(success_responses) == 1, \
        (f'Concurrent {method} {path.format(my_app_id)} expected exactly 1 success responses.\n'
         f'Actual success responses count: {len(success_responses)}')
    app_versions_difference = success_responses[0].json()['version'] - my_app['version']
    assert app_versions_difference == 1, \
        f'Expected version to be updated only once for concurrent {method} {path.format(my_app_id)} '

    wrong_unsuccess_status_codes = [
        response.status_code for response in responses
        if response.status_code != status.HTTP_200_OK and response.status_code != status.HTTP_412_PRECONDITION_FAILED
    ]
    assert not wrong_unsuccess_status_codes, \
        (f'Concurrent {method} {path.format(my_app_id)} returned unexpected status codes: {wrong_unsuccess_status_codes}. '
         f'All failures should be {status.HTTP_412_PRECONDITION_FAILED} (Precondition Failed)')

    # 3. Activation rule
    my_app_updated = success_responses[0].json()
    if_match = my_app_updated['etag']
    payload = {
        'name': 'My-App-Test',
        'is_active': True
    }
    response = api.patch_application(
        app_id=my_app_id,
        authorization=authorization,
        if_match=if_match,
        payload=payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, \
        (f'{method} {path.format(my_app_id)} with payload {payload} returned {response.status_code}. '
         f'Expected {status.HTTP_422_UNPROCESSABLE_CONTENT} due to breaking the activation rule"')
    assert response.json().get('detail').get('code') == NAME_FORBIDS_ACTIVATION_CODE, \
        (f'{method} {path.format(my_app_id)} returned wrong error code. '
         f'Expected: {NAME_FORBIDS_ACTIVATION_CODE}, Actual: {response.json().get('detail').get('code')}')

    actual_activation_state = api.get_application(my_app_id).json()['is_active']
    assert actual_activation_state is False, \
        f'Expected GET {path.format(my_app_id)} to return inactive app state after breaking activation rule'

    response = api.patch_application(
        app_id=my_app_id,
        authorization=authorization,
        if_match=if_match,
        payload=payload,
        is_force=True
    )
    response_status = response.status_code
    assert response_status == status.HTTP_200_OK or response_status == status.HTTP_202_ACCEPTED, \
        (f'Forced {method} {path.format(my_app_id)} returned {response_status}. '
         f'Expected {status.HTTP_200_OK} or {status.HTTP_202_ACCEPTED}. Payload: {payload}')
    if ACTIVATION_MODE == 'immediate':
        assert response.json()['is_active'], \
            f'{method} {path.format(my_app_id)} expected immediate activation but is_active is False'
    else:
        retry_until(lambda: api.get_application(my_app_id).json()['is_active'])

    # 4. Atomicity
    initial_my_app_state = api.get_application(my_app_id).json()
    existing_names = [app['name'] for app in api.get_applications().json()]
    response = api.patch_application(
        app_id=my_app_id,
        authorization=authorization,
        if_match=initial_my_app_state['etag'],
        payload={
            'name': choice(existing_names),
            'is_active': False
        }
    )
    assert response.status_code == status.HTTP_409_CONFLICT, \
        (f'{method} {path.format(my_app_id)} with non-unique name returned {response.status_code}. '
         f'Expected {status.HTTP_409_CONFLICT}. Payload: {response.json()}')
    final_my_app_state = api.get_application(my_app_id).json()
    assert initial_my_app_state == final_my_app_state, \
        (f'{method} {path.format(my_app_id)} should be atomic, but state changed after failed update.\n'
         f'Initial: {initial_my_app_state},\nFinal: {final_my_app_state}')
