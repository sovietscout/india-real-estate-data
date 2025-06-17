from patchright.async_api import async_playwright
import json
import time
import asyncio
import pandas as pd
from typing import List, Callable, Union

class NNAcresProperty(dict):
    @staticmethod
    def _parse(value: any, parser: Callable = lambda x: x) -> Union[any, None]:
        if value is None:
            return None

        return parser(value)

    def _handle_age(self, value: str = '') -> str:
        if value == '1':
            return '1 to 5 years'
        elif value == '2':
            return 'New Construction'
        elif value == '3':
            return "10+ Years"
        elif value == '':
            return None
        else:
            return value

    def _handle_possession_status(self, value: str = '') -> str:
        if value == 'I':
            return 'Ready to Move'
        elif value == '':
            return None
        else:
            return value
    
    def _handle_furnish(self, value: str = '') -> str:
        if value == '1':
            return 'Furnished'
        elif value == '2':
            return 'Unfurnished'
        elif value == '4':
            return 'Semi-Furnished'
        elif value == '0' or '':
            return None
        else:
            return value
    
    def _handle_floor(self, value: str = '') -> Union[int, None]:
        if value == 'B':
            return 0
        else:
            return int(value) if value else None

    def _handle_area(self, data: dict) -> Union[float, None]:
        keys = ['SUPERBUILTUP_SQFT', 'BUILTUP_SQFT']
        for key in keys:
            value = data.get(key)
            try:
                if value is not None:
                    return float(value)
            except (ValueError, TypeError):
                continue
        
        # Fallback to MIN_AREA + MAX_AREA
        try:
            min_area = float(data.get('MIN_AREA', 0))
            max_area = float(data.get('MAX_AREA', 0))
            area = (min_area + max_area) / 2

            if not min_area or not max_area:
                min_area = float(data.get('MIN_AREA', 0))
                max_area = float(data.get('MAX_AREA', 0))
                area = (min_area + max_area) / 2
            
            return area if min_area and max_area else None
        except (ValueError, TypeError):
            return None

    def _handle_parking(self, value: str = '') -> str:
        try:
            if not value:
                return 0

            parking_data = json.loads(value)
            
            if isinstance(parking_data, dict):
                return sum(v for v in parking_data.values() if isinstance(v, int))
            elif isinstance(parking_data, list):    # ["N"]
                return 0
            else:
                return 0
        
        except (json.JSONDecodeError, TypeError):
            return 0

    def __init__(self, data: dict):
        try:
            self['_id'] = f"nna-{data.get('PROP_ID', '')}"

            self['Latitude'] = self._parse(data['MAP_DETAILS'].get('LATITUDE'), float)
            self['Longitude'] = self._parse(data['MAP_DETAILS'].get('LONGITUDE'), float)

            self['Code_City'] = self._parse(data['location'].get('CITY'), str)
            self['Name_City'] = self._parse(data['location'].get('CITY_NAME'), str)
            self['Code_Locality'] = self._parse(data['location'].get('LOCALITY_ID'), str)
            self['Name_Locality'] = self._parse(data['location'].get('LOCALITY_NAME'), str)
            
            self['Price'] = self._parse(data.get('MIN_PRICE'), int)
            self['Price_SqFt'] = self._parse(float(data.get('PRICE_SQFT')), int)
            self['Area_SqFt'] = self._parse(self._handle_area(data), int)

            self['Status_Age_Construction'] = self._handle_age(data.get('AGE')) # Incomplete
            self['Status_Possession_Status'] = self._handle_possession_status(data.get('AVAILABILITY')) # Incomplete
            self['Status_Furnished'] = self._handle_furnish(data.get('FURNISH'))

            self['Num_Bedroom'] = self._parse(data.get('BEDROOM_NUM'), int)
            self['Num_Floor'] = self._handle_floor(data.get('FLOOR_NUM'))
            self['Num_Floor_Total'] = self._parse(data.get('TOTAL_FLOOR'), int)
            self['Num_Balcony'] = self._parse(data.get('BALCONY_NUM'), int)
            self['Num_Bathroom'] = self._parse(data.get('BATHROOM_NUM'), int)
            self['Num_Parking'] = self._handle_parking(data.get('RESERVED_PARKING'))
            # self['Type_Flooring'] = self._handle_flooring(data.get('flooringTyD')) # Mentioned in TOP_USPS only if Vtrified

            self['Code_Amenities'] = self._parse(data.get('FEATURES'), lambda x: x.split(','))
            """
            self['Name_Landmarks'] = self._parse(
                data.get('landmarkDetails'), lambda x: [item.split('|')[1] for item in x if item]
            )
            self['Type_Property'] = data.get('propTypeD')
            self['Type_Transaction'] = data.get('transactionTypeD')
            """
 
            self['Time_Scraped'] = int(time.time())
            self['Time_Posted'] = int(data.get('POSTING_DATE', 0) / 1000)

        except Exception as e:
            print(f"Error: {e}\nData:{data}")
            raise e


class NNAcresService:
    BASE_URL = "https://www.99acres.com"

    def __init__(self):
        self.listings: List[dict] = []

    async def post_processing(self, properties: List[NNAcresProperty]) -> List[NNAcresProperty]:
        semaphore = asyncio.Semaphore(10)

    async def _handle_response(self, response):
        if "/api-aggregator/discovery/srp/search" in response.url and response.status == 200:
            resp = await response.json()
            await self._sanitise_data(resp)

    async def _get_initial_data(self, page) -> None:
        resp_raw = await page.evaluate('''() => {
            const scripts = Array.from(document.querySelectorAll('script'));
            const target = scripts.find(script => script.textContent.includes('window.__initialData__'));
            return target ? target.textContent : null;
        }''')
        
        resp = json.loads(
            resp_raw.replace('window.__initialData__=', '').replace('; window.__masked__ = false', '')
        )['srp']['pageData'].get('properties', [])
        await self._sanitise_data(resp)

    async def _sanitise_data(self, data: List[dict]) -> int:
        # Converts each property dict to NNAcresProperty. Avoid project listings
        candidates = [NNAcresProperty(item) for item in data if 'SPID' in item]
        self.listings.extend(candidates)

        return len(candidates)

    async def search_page(self) -> None:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            await page.route("**/*", lambda route, request: route.abort()
                if request.resource_type in ["image", "font"]
                else route.continue_())

            await page.goto(self.BASE_URL)
            await page.wait_for_url("**/search/property/**", timeout=0, wait_until="documentloaded")

            await self._get_initial_data(page)

            # --- collect properties ---

            page.on("response", self._handle_response)
            
            await asyncio.sleep(5)
            await context.close()
            await browser.close()

            return self.listings


if __name__ == "__main__":
    async def main():
        service = NNAcresService()
        prop_data = await service.search_page()

        df = pd.DataFrame(prop_data)
        df.to_csv(f"output/nnnacres-{int(time.time())}.csv", index=False)

    asyncio.run(main())