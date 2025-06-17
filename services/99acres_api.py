import lxml
import asyncio
import aiohttp
from http.cookies import SimpleCookie
from typing import Any, Dict, Optional
from base64 import b64encode
import logging
import time

logging.basicConfig(level=logging.ERROR)
log = logging.getLogger(__name__)


class NNAcresService:
    BASE_URL = "https://www.99acres.com"

    def __init__(self, connector: Optional[aiohttp.TCPConnector] = None):
        self._connector = connector
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            log.info("Creating new aiohttp ClientSession.")
            
            cookie_jar = aiohttp.CookieJar(unsafe=True)

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Referer": f"{self.BASE_URL}/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "apitoken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NDk2NzY4MTAuMzMxLCJleHAiOjE3NDk2NzY5MzAuMzMxLCJocSI6ImU1ZWU0ZGIxYjZkZGE1MDU1NzRmNGYwYjQ3ZjIzY2M2Iiwid2IiOiIwZWE3MzQ3OTBhMDYzMTc4NjQ4ZTkzMjc2MzliZjBlZSJ9.S04mVF-4Q4RzITvyp0lcV4Fi3F-DNhBIrqK4vJNr5-Q",
                "authorizationtoken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjoiNytwZklXekE2NzA3ZGlsSjI4TkFpa3JOc3llN0V2RzJJWnZOMm1CZVV5ZDdFUDBpaFVkSit6UGFHTTRYa05ndmQ5WHV3dlFEZzAvdFBVcXdYWWZ2VEdGQ3RObTAvM0F3Ky80UHpzSFVsQzVtLzIyTVZ2bUFpbXhqQ3lPT1Q2bS9nSFdFb1VlZWo2UlRiWFg4UVkvZWMwTWxYbmhQelVlSk9SaUo2eERFOVhiMmVUSWtDbU05SlhnMmcrV2swQkFCVVZHbkdjYncycU0renU0OFFIblVYYTJnTGlxVFVrNjlPbW83cWJITHBsV1dqMlhLNWRoSWJiZkRMUnNoU0ovQzRhZzFCYkZhN1p3di80NFRDMTFOVnlkL0tCanhYM0s5amlWMDZoTzBZS3QwdjFGS00reGNOZzBDNW9WdFQxdWIiLCJzMSI6IjhGSG45TkRIZHFVeDhiL1RvbUFOR2srS09oekY0Z0IwIiwiczIiOiJFdmFtamJqbFgrVm8xZTMrdW9RNkRWeGMrZExnUEd2NCIsInMzIjoiWWxwNVdGZHVhMDFHTDJnNVdVUnpNM0JoTW1wRE4xVkRZa1oyUWl0aVYzZENSa3A1VTNaSlFVRXJWVnBTUVVacmJuSkZLMlpoV2pGbGJWSTFkSFJpVjNvMU1rTkxZMEZ1U1ZwcU1VMDFPRlExWldndllWb3JTazR5YUdsRGVWazNiMEZtZDNkWlVteHBZa2RNSzFCc1JGWmFlQ3RaT1RWT2VFWmpWVEIwWTNsS09HTmliVkJRWlZReVJuRjZVM0pNYWs0d05rVndNVFYzZG5KWWFYcFhiRGhIVURjNVVuWlJabGR4V1ZwYVZVWnhZaTlHYVZkWldYZ3pjRE13U2pCaFVrMVVhVVZXWTFGU2VGSjNlR2RIVlhrelJrTmtSMkV3T1V0eFYwaFdWM0pMUlROQ2VTOU5NU3RHVmxCTFVVZElWalJpTlhWUlpXTlFSbmhNVVZveVJGVnJjME5hU3pWU1NYaDJSVmMxU0ZWeE1tVlVSVWxtTVZST1oyUlNjMFIyU0RrMVZUTTRXREl6ZUVWWVMxSTVhVVZzUW14cFV6aHVhMmx6TDJsMk5XMURiRU00TkVOdmNESkZLell2YmtaR2FsSnVTV2wxSzNBNFpHcFlRWFJDTm5wRWNIUkdibVZvTkhvd1BRbz0iLCJ2IjoiMiIsImlhdCI6MTc0OTY3NjYwMiwiZXhwIjoxNzQ5Njc3MjAyfQ.gQ_e5H8_ooaqy-z1BEr5o3PRgOIXycy5ZxfNz1P3h7k",
            }

            self._session = aiohttp.ClientSession(
                connector=self._connector,
                cookie_jar=cookie_jar,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            )

        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            log.info("Closing aiohttp ClientSession.")
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        session = await self._get_session()
        log.debug(f"Making {method.upper()} request to {url} with params: {kwargs.get('params')}")
        try:
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()

                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    data = await response.json()
                    log.debug(f"Received JSON response from {url}")
                    return data
                else:
                    text_response = await response.text()
                    log.warning(f"Received non-JSON response from {url}. Content-Type: {content_type}. Body: {text_response[:200]}...")
                    return text_response
        
        except aiohttp.ClientError as e:
            log.error(f"HTTP request failed: {e.__class__.__name__} - {e}", exc_info=True)
            raise
        
        except Exception as e:
            log.error(f"An unexpected error occurred during request: {e}", exc_info=True)
            raise

    async def _encrypt_params(self, **kwargs) -> Dict[str, Any]:
        pass


    async def search(self, city_id: int, locality_id: int, page: int = 1, **kwargs) -> Dict[str, Any]:
        params = {
            "city": city_id,
            "locality": locality_id,
            **kwargs
        }

        #url = f"{self.BASE_URL}/search/property/buy"
        url = f"{self.BASE_URL}/3-bhk-bedroom-apartment-flat-for-sale-in-bengal-shelter-teen-kanya-rajarhat-kolkata-east-1360-sq-ft-r1-spid-X79772315"
        log.info(f"Searching page {page} for city {city_id}...")

        resp = await self._request("GET", url)

        return resp

        """
        params = {
            "transact_type": "1",
            "locality_array": str(locality_id),
            "isPreLeased": "N",
            "area_unit": "1",
            "localityNameMap": "[object Object]",
            "platform": "DESKTOP",
            "moduleName": "GRAILS_SRP",
            "workflow": "GRAILS_SRP",
            "page_size": "25",
            "page": str(page),
            "city": str(city_id),
            "preference": "S",
            "res_com": "R",
            "seoUrlType": "DEFAULT",
            "recomGroupType": "VSP",
            "pageName": "SRP",
            "groupByConfigurations": "true",
            "lazy": "true"
        }

        resp = await self._request("GET", f"{self.BASE_URL}/api-aggregator/discovery/srp/search", params=params)
        return resp
        """


if __name__ == "__main__":
    async def main():
        async with NNAcresService() as service:
            result = await service.search(26, 1495)
            print(result)

    asyncio.run(main())
