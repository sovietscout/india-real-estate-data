import time
import asyncio
import aiohttp
from magicbricks_api import MagicBricksAPI
from pymongo import MongoClient
import pandas as pd


async def main(collection):
    async with MagicBricksAPI() as api:
        tic = time.perf_counter()

        try:
            prop_data = await api.search_pages(city_code="6903", start_page=1, end_page=50)

            collection.insert_many(prop_data)
            print(f"Inserted {len(prop_data)} listings into MongoDB.")

            """
            # Pandas/CSV implementation (make sure to import pandas)
            df = pd.DataFrame(prop_data)
            df.to_csv("properties.csv", index=False)

            print(f"Fetched {len(prop_data)} listings in Kolkata.")
            """

        except aiohttp.ClientResponseError as e:
            print(f"\nAPI Error: Status {e.status} - {e.message}")
        except ValueError as e:
            print(f"\nData Error: {e}")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

        toc = time.perf_counter()
        print(f"Finished in {toc - tic:0.4f} seconds")


if __name__ == "__main__":
    client = MongoClient('mongodb://localhost:27017/')
    db = client['india-real-estate']

    properties_collection = db['properties']
    locations_collection = db['locations']

    asyncio.run(main(properties_collection))