import time
import asyncio
import aiohttp
from magicbricks_api import MagicBricksAPI
import pandas as pd


async def main():
    async with MagicBricksAPI() as api:
        tic = time.perf_counter()
        city_id = "6903"

        try:
            prop_data = await api.search_pages(city_code=city_id, start_page=1, end_page=50)

            df = pd.DataFrame(prop_data)
            df.to_csv(f"properties-{city_id}.csv", index=False)

            print(f"Fetched {len(prop_data)} listings in City {city_id}.")

        except aiohttp.ClientResponseError as e:
            print(f"\nAPI Error: Status {e.status} - {e.message}")
        except ValueError as e:
            print(f"\nData Error: {e}")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

        toc = time.perf_counter()
        print(f"Finished in {toc - tic:0.4f} seconds")


if __name__ == "__main__":
    asyncio.run(main())