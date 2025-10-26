import asyncio
from datetime import datetime, UTC, timedelta

from faker import Faker
from fastapi import HTTPException, status

from constants import WEAK_IF_MATCH_FORMAT_REGEX, ETAG_LENGTH, \
    RATE_UPDATING_PERIOD_S, NAME_FORBIDS_ACTIVATION_CODE, ACTIVATION_DELAY_S
from mock_api.base_models.application import ApplicationPatchPayloadModel

fake = Faker()


def check_rate_limit(max_rate_limit: int, token_rate_limit: dict, token: str) -> None:
    now = datetime.now(UTC)
    timestamps = token_rate_limit.get(token, [])
    timestamps = [time for time in timestamps if (now - time) < timedelta(minutes=1)]
    if len(timestamps) >= max_rate_limit:
        oldest_request_time = min(timestamps)
        retry_after = RATE_UPDATING_PERIOD_S - (now - oldest_request_time).seconds
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail='Rate limit exceed',
            headers={'Retry-After': str(retry_after)}
        )

    timestamps.append(now)
    token_rate_limit[token] = timestamps


def generate_etag(etag_length: int) -> str:
    return fake.hexify(text='^' * etag_length)


def check_name_uniqueness_in_items(name: str, items: list) -> None:
    if any(name.strip().casefold() == item['name'].strip().casefold() for item in items):
        raise HTTPException(status.HTTP_409_CONFLICT, 'Name is not unique')


def update_application_by_if_match(application: dict, if_match: str | None) -> None:
    if if_match is None:
        raise HTTPException(status.HTTP_412_PRECONDITION_FAILED, 'missing If-Match')

    match_of_weak_if_match = WEAK_IF_MATCH_FORMAT_REGEX.match(if_match)
    if match_of_weak_if_match:
        if_match_version = int(match_of_weak_if_match.group(1).lstrip('0'))
        if if_match_version != application['version']:
            raise HTTPException(status.HTTP_412_PRECONDITION_FAILED, 'stale If-Match')
    elif if_match.strip('"') != application['etag'].strip('"'):
        raise HTTPException(status.HTTP_412_PRECONDITION_FAILED, 'stale If-Match')

    application['version'] += 1
    application['etag'] = generate_etag(ETAG_LENGTH)


def update_application_by_payload(application: dict, payload: ApplicationPatchPayloadModel, force: bool) -> None:
    if 'test' in payload.name.casefold().strip() and payload.is_active and not force:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, {'code': NAME_FORBIDS_ACTIVATION_CODE})

    for key, value in payload.model_dump(exclude_unset=True).items():
        if key in application:
            application[key] = value


def update_application_in_applications_list(updated_application: dict, applications: list) -> None:
    for i, application in enumerate(applications):
        if application['id'] == updated_application['id']:
            applications[i] = updated_application
            return


async def activate_application_later(application: dict, applications: list, delay: float = ACTIVATION_DELAY_S):
    await asyncio.sleep(delay)
    update_application_in_applications_list(application, applications)
