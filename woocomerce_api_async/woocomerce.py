# -*- coding: utf-8 -*-

"""
WooCommerce API Class
"""

__title__ = "woocommerce_api_aync"
__version__ = "0.1.0"
__author__ = "Ali Najafi @ Felfeli Lab"
__license__ = "MIT"

from requests import request
import asyncio
import aiohttp
from json import dumps as jsonencode
from time import time
from woocomerce_api_async.woocommerce_oauth import OAuth

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode


class Response:
    """ Simple Driver between requests and aiohttp
    now response has status_code and json() method
    """
    def __init__(self, status_code, json):
        self.status_code = status_code
        self._json = json

    def json(self):
        return self._json

    def __str__(self):
        return 'status_code: %s | json(): %s...' % (self.status_code, repr(self._json)[:100])


class API(object):
    """ API Class """

    def __init__(self, url, consumer_key, consumer_secret, **kwargs):
        self.url = url
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.wp_api = kwargs.get("wp_api", True)
        self.version = kwargs.get("version", "wc/v3")
        self.is_ssl = self.__is_ssl()
        self.timeout = kwargs.get("timeout", 5)
        self.verify_ssl = kwargs.get("verify_ssl", True)
        self.query_string_auth = kwargs.get("query_string_auth", False)

    def __is_ssl(self):
        """ Check if url use HTTPS """
        return self.url.startswith("https")

    def __get_url(self, endpoint):
        """ Get URL for requests """
        url = self.url
        api = "wc-api"

        if url.endswith("/") is False:
            url = "%s/" % url

        if self.wp_api:
            api = "wp-json"

        return "%s%s/%s/%s" % (url, api, self.version, endpoint)

    def __get_oauth_url(self, url, method, **kwargs):
        """ Generate oAuth1.0a URL """
        oauth = OAuth(
            url=url,
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            version=self.version,
            method=method,
            oauth_timestamp=kwargs.get("oauth_timestamp", int(time()))
        )

        return oauth.get_oauth_url()

    async def __request(self, method, endpoint, data, params=None, **kwargs):
        """ Do requests """
        if params is None:
            params = {}
        url = self.__get_url(endpoint)
        auth = None
        headers = {
            "user-agent": "WooCommerce API Client-Python/%s" % __version__,
            "accept": "application/json"
        }

        if self.is_ssl is True and self.query_string_auth is False:
            # change to aiohttp.BasicAuth
            # auth = (self.consumer_key, self.consumer_secret)
            auth = aiohttp.BasicAuth(self.consumer_key, self.consumer_secret)
        elif self.is_ssl is True and self.query_string_auth is True:
            params.update({
                "consumer_key": self.consumer_key,
                "consumer_secret": self.consumer_secret
            })
        else:
            encoded_params = urlencode(params)
            url = "%s?%s" % (url, encoded_params)
            url = self.__get_oauth_url(url, method, **kwargs)

        if data is not None:
            data = jsonencode(data, ensure_ascii=False).encode('utf-8')
            headers["content-type"] = "application/json;charset=utf-8"

        # Change to async
        # return request(
        #     method=method,
        #     url=url,
        #     verify=self.verify_ssl,
        #     auth=auth,
        #     params=params,
        #     data=data,
        #     timeout=self.timeout,
        #     headers=headers,
        #     **kwargs
        # )
        async with aiohttp.ClientSession() as session:
            async with await session.request(
                method=method,
                url=url,
                verify_ssl=self.verify_ssl,
                auth=auth,
                params=params,
                data=data,
                timeout=self.timeout,
                headers=headers,
                **kwargs
            ) as resp:
                json = await resp.json()
                status_code = resp.status
        # print(text)
        return Response(status_code, json)

    async def get(self, endpoint, **kwargs):
        """ Get requests """
        return await self.__request("GET", endpoint, None, **kwargs)

    async def post(self, endpoint, data, **kwargs):
        """ POST requests """
        return await self.__request("POST", endpoint, data, **kwargs)

    async def put(self, endpoint, data, **kwargs):
        """ PUT requests """
        return await self.__request("PUT", endpoint, data, **kwargs)

    async def delete(self, endpoint, **kwargs):
        """ DELETE requests """
        return await self.__request("DELETE", endpoint, None, **kwargs)

    async def options(self, endpoint, **kwargs):
        """ OPTIONS requests """
        return await self.__request("OPTIONS", endpoint, None, **kwargs)

