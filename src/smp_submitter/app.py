import logging

import fastapi
import fastapi.responses

from typing import Tuple

from .config import Config
from .consts import NICE_NAME, VERSION, BUILD_INFO, DEFAULT_ENCODING
from .logic import process


LOG = logging.getLogger(__name__)


app = fastapi.FastAPI(
    title=NICE_NAME,
    version=VERSION,
)


def _valid_token(request: fastapi.Request) -> bool:
    if Config.API_TOKEN is None:
        LOG.debug('Security disabled, authorized directly')
        return True
    auth = request.headers.get('Authorization', '')  # type: str
    if not auth.startswith('Bearer '):
        LOG.debug('Invalid token (missing or without "Bearer " prefix')
        return False
    token = auth.split(' ', maxsplit=1)[1]
    return token == Config.API_TOKEN


def _extract_content_type(header: str) -> Tuple[str, str]:
    type_headers = header.lower().split(';')
    input_format = type_headers[0]
    if len(type_headers) == 0:
        return input_format, DEFAULT_ENCODING
    encoding_header = type_headers[0].strip()
    if encoding_header.startswith('charset='):
        return input_format, encoding_header[9:]
    return input_format, DEFAULT_ENCODING


@app.get('/', response_class=fastapi.responses.HTMLResponse)
async def get_index(request: fastapi.Request):
    return fastapi.responses.JSONResponse(content=BUILD_INFO)


@app.post('/submit', response_class=fastapi.responses.JSONResponse)
async def post_submit(request: fastapi.Request):
    # (1) Verify authorization
    if not _valid_token(request=request):
        return fastapi.responses.PlainTextResponse(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            content='Unauthorized submission request.\n\n'
                    'The submission service is not configured properly.\n'
        )
    # (2) Get data
    content_type, encoding = _extract_content_type(
        header=request.headers.get('Content-Type', ''),
    )
    content = await request.body()
    content = content.decode(DEFAULT_ENCODING)
    # (3) Return response
    try:
        pr_link = await process(
            content=content,
            content_type=content_type,
        )

        return fastapi.responses.JSONResponse(
            headers={
                'Location': pr_link,
            },
            status_code=fastapi.status.HTTP_201_CREATED,
            content={
                'message': 'Notification sent successfully!',
            }
        )
    except Exception as e:
        return fastapi.responses.PlainTextResponse(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            content=str(e),
        )


@app.on_event("startup")
async def app_init():
    Config.check()
