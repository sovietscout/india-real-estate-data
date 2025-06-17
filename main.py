import time
import asyncio
import aiohttp
import pandas as pd
from services.magicbricks import MagicBricksService
# from sites.magicbricks import MagicBricksService

"""
async def main():
    async with MagicBricksService() as api_mb:
        tic = time.perf_counter()
        city_id_mb = "6903"

        semaphore = asyncio.Semaphore(10)
        async def limited_search(coro):
            async with semaphore:
                return await coro

        coros_mb = await api_mb.search(city_code=city_id_mb)
        async with asyncio.TaskGroup() as tg:
            try:
                tasks = [tg.create_task(limited_search(c)) for c in coros_mb]

            except aiohttp.ClientResponseError as e:
                print(f"\nAPI Error: Status {e.status} - {e.message}")
            except ValueError as e:
                print(f"\nData Error: {e}")
            except Exception as e:
                print(f"\nAn unexpected error occurred: {e}")

        # List[List[Dict[str, Any]]]
        results = [t.result() for t in tasks if t.done() and not t.cancelled()]

        prop_data = []
        for result in results:
            prop_data.extend(result)

        df = pd.DataFrame(prop_data)
        df.to_csv(f"output/properties-{city_id_mb}.csv", index=False)

        toc = time.perf_counter()
        print(f"Finished in {toc - tic:0.4f} seconds")
"""

async def main():
    async with MagicBricksService() as api:
        tic = time.perf_counter()
        city_id = "2395"

        try:
            prop_data = await api.search(city_code=city_id)

            df = pd.DataFrame(prop_data)
            df.to_csv(f"output/properties-{city_id}.csv", index=False)

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