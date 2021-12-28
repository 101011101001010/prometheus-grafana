import asyncio

import aiohttp


async def _get_response(session, url: str):
    async with session.get(url) as resp:
        if resp.status != 200:
            return None
        return await resp.json()


async def get_response(url: str, headers=None):
    if headers is None:
        headers = {}

    async with aiohttp.ClientSession(headers=headers) as session:
        return await _get_response(session, url)


async def get_responses(urls: list, headers=None) -> list:
    if headers is None:
        headers = {}

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks: list = []

        for url in urls:
            tasks.append(asyncio.ensure_future(_get_response(session, url)))

        results: list = await asyncio.gather(*tasks)
        return results
