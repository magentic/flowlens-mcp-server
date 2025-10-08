import httpx
from ..dto import dto
from ..models import enums
from ..utils import logger_setup
from ..utils.settings import settings

log = logger_setup.Logger(__name__)

class _RequestParameters:
    def __init__(self, token: str):
        self.end = token
        
class HttpRequestHandler:
    def __init__(self, token: str):
        self.base_url = settings.flowlens_url
        self._token = token
        self._headers = {"Authorization": f"Bearer {self._token}"}
        
    async def get(self, endpoint: str, response_model=None):
        params = dto.RequestParams(
            endpoint=endpoint,
            request_type=enums.RequestType.GET,
            response_model=response_model
        )
        return await self.send_request(params)

    async def post(self, endpoint: str, payload: dict, response_model=None):
        params = dto.RequestParams(
            endpoint=endpoint,
            request_type=enums.RequestType.POST,
            payload=payload,
            response_model=response_model
        )
        return await self.send_request(params)

    async def patch(self, endpoint: str, payload: dict, response_model=None):
        params = dto.RequestParams(
            endpoint=endpoint,
            request_type=enums.RequestType.PATCH,
            payload=payload,
            response_model=response_model
        )
        return await self.send_request(params)

    async def delete(self, endpoint: str, response_model=None):
        params = dto.RequestParams(
            endpoint=endpoint,
            request_type=enums.RequestType.DELETE,
            response_model=response_model
        )
        return await self.send_request(params)

    async def send_request(self, params: dto.RequestParams):
        url = f"{self.base_url}/{params.endpoint}"
        async with httpx.AsyncClient() as client:
            if params.request_type == enums.RequestType.GET:
                response = await client.get(url, headers=self._headers)
            elif params.request_type == enums.RequestType.POST:
                response = await client.post(url, headers=self._headers, json=params.payload)
            elif params.request_type == enums.RequestType.DELETE:
                response = await client.delete(url, headers=self._headers)
            elif params.request_type == enums.RequestType.PATCH:
                response = await client.patch(url, headers=self._headers, json=params.payload)
            else:
                raise ValueError(f"Unsupported request type: {params.request_type}")
            response.raise_for_status()
            if response.text.strip():
                return params.response_model(**response.json())
            raise Exception(f"Empty response from {url}")
        raise Exception(f"Failed to send request to {url}")
    