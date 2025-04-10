import asyncio
import aiohttp
from typing import List, Dict, Optional, Callable, Union,Any
from http.cookies import SimpleCookie
import time
import logging

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


class Property(dict):
    @staticmethod
    def _parse(value: any, parser: Callable = lambda x: x) -> Union[any, None]:
        if value is None:
            return None

        return parser(value)
    
    @staticmethod
    def _handle_parking(parking_input: Union[str, None]) -> int:
        if parking_input is None:
            return 0
        elif isinstance(parking_input, str):
            try:
                return sum([int(i.split()[0]) for i in parking_input.split(',')])
            except ValueError:
                raise ValueError(f"Unknown parking designation: {parking_input}")
        else:
            raise ValueError(f"Unknown parking designation: {parking_input}")

    
    @staticmethod
    def _handle_floor(floor_input: Union[str, int, None]) -> Union[int, None]:
        if floor_input is None:
            return None
        elif isinstance(floor_input, int):
            return floor_input
        elif floor_input.lower() == 'ground':
            return 0
        elif floor_input.lower() == 'upper basement':
            return -1
        elif floor_input.lower() == 'lower basement':
            return -2
        else:
            try:
                return int(floor_input)
            except ValueError:
                raise ValueError(f"Unknown floor designation: {floor_input}")
        
    def __init__(self, data: Dict):
        self['_id'] = data.get('id')
        #self['Name_Project'] = data.get('prjname')
        #self['Name_Developer'] = data.get('companyname')

        self['Latitude'] = self._parse(data.get('pmtLat'), float)
        self['Longitude'] = self._parse(data.get('pmtLong'), float)

        self['Code_City'] = self._parse(data.get('ct'), str)
        self['Code_Locality'] = self._parse(data.get('lt'), str)

        self['Price'] = self._parse(data.get('price'), int)
        self['Price_SqFt'] = self._parse(data.get('sqFtPrD'), int)
        self['Area_SqFt'] = self._parse(data.get('ca'), int)

        self['Code_Age_Construction'] = self._parse(data.get('ac'), str)
        self['Code_Possession_Status'] = self._parse(data.get('ps'), str)

        self['Num_Bedroom'] = self._parse(data.get('bedroomD'), int)
        self['Num_Floor'] = self._handle_floor(data.get('floorNo'))
        self['Num_Floor_Total'] = self._parse(data.get('floors'), int)
        self['Num_Balcony'] = self._parse(data.get('noBfCt'), int)
        self['Num_Bathroom'] = self._parse(data.get('bathD'), int)
        self['Num_Parking'] = self._handle_parking(data.get('parkingD'))

        self['Code_Amenities'] = self._parse(data.get('amenities'), lambda x: x.split(' '))
        self['Name_Landmarks'] = self._parse(
            data.get('landmarkDetails'), lambda x: [item.split('|')[1] for item in x if item]
        )
        self['Type_Property'] = data.get('propTypeD')
        self['Type_Transaction'] = data.get('transactionTypeD')

        self['Status_Furnished'] = data.get('furnishedD')

        #self['Is_Luxury'] = self.parse(data.get('isLuxury'), lambda x: int(x != 'F'))
        #self['Is_Prime_Location'] = self.parse(data.get('isPrimeLocProp'), lambda x: int(x == 'Y'))

        self['Time_Scraped'] = int(time.time())
        self['Time_Post'] = int(data.get('pd') / 1000) 

        #self['URL'] = data.get('newUrl')

    def __repr__(self):
        return f"<Property id={self['_id']} city='{self['Code_City']}' price='{self['Price']}' area='{self['Area_SqFt']}' sqFtPrice='{self['Price_SqFt']}' bedrooms='{self['Num_Bedroom']}' floor='{self['Num_Floor']}' totalFloors='{self['Num_Floor_Total']}'>"


class MagicBricksAPI:
    BASE_URL = "https://www.magicbricks.com"

    def __init__(self, connector: Optional[aiohttp.TCPConnector] = None):
        self._connector = connector
        self._session: Optional[aiohttp.ClientSession] = None


    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            log.info("Creating new aiohttp ClientSession.")
            
            cookie_jar = aiohttp.CookieJar(unsafe=True)

            cookies_to_set = SimpleCookie()
            static_cookies = [
                ("propCategory", "Residential", "/", ".magicbricks.com"),
                ("projectCategory", "B", "/", ".magicbricks.com"),
            ]
            for name, value, path, domain in static_cookies:
                 cookies_to_set[name] = value
                 cookies_to_set[name]['path'] = path
                 cookies_to_set[name]['domain'] = domain

            cookie_jar.update_cookies(cookies_to_set, aiohttp.helpers.URL(self.BASE_URL))

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
            }

            self._session = aiohttp.ClientSession(
                headers=headers,
                cookie_jar=cookie_jar,
                connector=self._connector,
                timeout=aiohttp.ClientTimeout(total=60)
            )

            log.info("Session created with headers and initial cookies.")
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
                    raise ValueError(f"Unexpected content type: {content_type}")
        
        except aiohttp.ClientError as e:
            log.error(f"HTTP request failed: {e.__class__.__name__} - {e}", exc_info=True)
            raise
        
        except Exception as e:
            log.error(f"An unexpected error occurred during request: {e}", exc_info=True)
            raise

    async def search(
        self,
        city_code: str,
        page: int = 1,
        property_types: Optional[List[str]] = None,
        bedrooms: Optional[List[str]] = None,
        **kwargs: Any
    ) -> List[Property]:
        if property_types is None:
            property_types = ["10002", "10003", "10021", "10022", "10001", "10017"] # Removed 10000 (Plot?)
        if bedrooms is None:
            bedrooms = ["11701", "11702", "11700", "11703", "11704", "11705", "11706"] # 1, 2, 3, 4, 5, 6+

        params = {
            "editSearch": "Y",
            "category": "S", # S = Sale, R = Rent
            "propertyType": ",".join(property_types),
            "bedrooms": ",".join(bedrooms),
            "city": city_code,
            "page": str(page),
            "sortBy": "postRecency",
            "postedSince": "-1", # All time
            "isNRI": "N",
            "multiLang": "en",
            **kwargs
        }

        url = f"{self.BASE_URL}/mbsrp/propertySearch.html"
        log.info(f"Searching page {page} for city {city_code}...")

        resp_data = await self._request("GET", url, params=params)

        if "resultList" not in resp_data or not isinstance(resp_data["resultList"], list):
             log.warning(f"Unexpected response structure from search API: 'resultList' missing or not a list. Keys: {resp_data.keys()}")
             return []

        return [Property(data) for data in resp_data["resultList"]]

    async def search_pages(
        self,
        city_code: str,
        start_page: int,
        end_page: int,
        property_types: Optional[List[str]] = None,
        bedrooms: Optional[List[str]] = None,
        delay_between_requests: float = 0.1,
        **kwargs: Any
    ) -> List[Property]:
        if start_page > end_page:
            raise ValueError("start_page must be less than or equal to end_page")

        tasks = []
        log.info(f"Starting batch search for city {city_code}, pages {start_page} to {end_page}")
        for page_num in range(start_page, end_page + 1):
            task = self.search(
                city_code=city_code,
                page=page_num,
                property_types=property_types,
                bedrooms=bedrooms,
                **kwargs
            )
            tasks.append(task)
            if delay_between_requests > 0:
                await asyncio.sleep(delay_between_requests)

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        all_properties: List[Property] = []
        for i, result in enumerate(results_list):
            page = start_page + i

            if isinstance(result, Exception):
                log.error(f"Failed to fetch page {page} for city {city_code}: {result}")
            
            elif isinstance(result, list):
                log.info(f"Successfully fetched {len(result)} properties from page {page}")
                all_properties.extend(result)
            
            else:
                log.warning(f"Unexpected result type for page {page}: {type(result)}")

        log.info(f"Batch search complete. Total properties fetched: {len(all_properties)}")
        return all_properties

    async def property_count(self, city_code: str) -> Dict[str, int]:
        params = { "cityCode": city_code }
        url = f"{self.BASE_URL}/mbutility/getPropertyCountGroup"
        log.info(f"Fetching property counts for city {city_code}...")

        resp_data = await self._request("GET", url, params=params)

        if "propCount" not in resp_data or not isinstance(resp_data["propCount"], dict):
            log.warning(f"Unexpected response structure from property count API: 'propCount' missing or not a dict. Keys: {resp_data.keys()}")
            return {}

        return resp_data["propCount"]

    async def all_cities(self) -> List[Dict[str, str]]:
        url = f"{self.BASE_URL}/mbsrp/getAllCities"
        log.info("Fetching list of all cities...")

        resp_data = await self._request("GET", url)

        if not isinstance(resp_data, list):
            log.warning(f"Unexpected response structure from all cities API: Expected list, got {type(resp_data)}")
            return []

        return resp_data
