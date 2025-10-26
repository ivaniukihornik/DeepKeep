import asyncio
import logging
import time
from datetime import datetime, UTC
from typing import Optional
from uuid import uuid4, UUID

from fastapi import FastAPI, HTTPException, Header, Request, status, Query
from fastapi.responses import JSONResponse

from constants import AUTHORIZATION_HEADER_PATTERN, RATE_LIMIT, ETAG_LENGTH, APPLICATION_ENDPOINT, \
    APPLICATIONS_ENDPOINT, ACTIVATION_MODE, ROOT_DIR, RESET_ENDPOINT
from mock_api.base_models.application import ApplicationPostPayloadModel, ApplicationPatchPayloadModel
from mock_api import app_helpers

app = FastAPI()

applications: list = []
idempotency_cache: dict = {}
token_rate_limit: dict = {}


@app.get(APPLICATIONS_ENDPOINT)
async def get_applications() -> list:
    return applications


@app.get(APPLICATION_ENDPOINT)
async def get_application(app_id: str) -> dict | None:
    for application in applications:
        if application['id'] == app_id:
            return application.copy()

    raise HTTPException(status.HTTP_404_NOT_FOUND, 'Application not found')


@app.post(APPLICATIONS_ENDPOINT, status_code=status.HTTP_201_CREATED)
async def post_application(
        payload: ApplicationPostPayloadModel,
        authorization: str = Header(pattern=AUTHORIZATION_HEADER_PATTERN),
        idempotency_key: UUID = Header(...),
) -> dict | None:
    token = authorization.replace('Bearer ', '')
    app_helpers.check_rate_limit(
        max_rate_limit=RATE_LIMIT,
        token_rate_limit=token_rate_limit,
        token=token
    )

    cache_key = (str(idempotency_key), token)
    if cache_key in idempotency_cache.keys():
        return idempotency_cache[cache_key]

    app_helpers.check_name_uniqueness_in_items(payload.name, applications)

    new_app_id = str(uuid4())
    new_app = {
        'id': new_app_id,
        'name': payload.name,
        'description': payload.description,
        'is_active': False,
        'version': 1,
        'etag': f'"{app_helpers.generate_etag(ETAG_LENGTH)}"',
        'created_at': f'{datetime.now(UTC).isoformat()}Z'
    }
    applications.append(new_app)
    idempotency_cache[cache_key] = new_app
    return new_app


@app.patch(APPLICATION_ENDPOINT, status_code=status.HTTP_200_OK, response_model=None)
async def patch_application(
    app_id: str,
    payload: ApplicationPatchPayloadModel,
    authorization: str = Header(pattern=AUTHORIZATION_HEADER_PATTERN),
    if_match: Optional[str] = Header(None),
    force: bool = Query(False)
) -> dict | None | JSONResponse:
    application = await get_application(app_id)

    app_helpers.update_application_by_if_match(application, if_match)
    app_helpers.check_name_uniqueness_in_items(payload.name, applications)
    app_helpers.update_application_by_payload(application, payload, force)

    if payload.is_active and ACTIVATION_MODE == 'eventual':
        asyncio.create_task(app_helpers.activate_application_later(application, applications))
        return JSONResponse(
            content={'status': 'activating'},
            status_code=status.HTTP_202_ACCEPTED
        )

    app_helpers.update_application_in_applications_list(application, applications)
    return application


@app.post(RESET_ENDPOINT, status_code=status.HTTP_200_OK)
async def reset_state():
    applications.clear()
    idempotency_cache.clear()
    token_rate_limit.clear()


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(f'{ROOT_DIR}/test_results/api.log'), logging.StreamHandler()]
)
logger = logging.getLogger('api_logger')


@app.middleware('http')
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000

    idempotency_key = request.headers.get('Idempotency-Key', '-')
    if_match = request.headers.get('If-Match', '-')

    logger.info(
        f'{request.method} {request.url.path} '
        f'Idempotency-Key={idempotency_key} If-Match={if_match} '
        f'status={response.status_code} time={process_time:.2f}ms'
    )

    return response
