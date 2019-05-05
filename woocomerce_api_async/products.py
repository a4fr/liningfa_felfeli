__title__ = "woocommerce_api_aync"
__version__ = "0.1.0"
__author__ = "Ali Najafi @ Felfeli Lab"
__license__ = "MIT"

from woocomerce_api_async.woocomerce import API as WC_API
from pprint import pprint
import asyncio


async def add_variation(wcapi: WC_API, pid, attribute, regular_price, sale_price):
    data = {
        "regular_price": regular_price,
        "sale_price": sale_price,
        "attributes": list(),
    }
    data["attributes"].append(attribute)
    return await wcapi.post("products/%s/variations" % pid, data)


async def get_all_variations(wcapi: WC_API, pid):
    return await wcapi.get("products/%s/variations" % pid)


async def delete_variation(wcapi: WC_API, pid, vid):
    return await wcapi.delete("products/%s/variations/%s" % (pid, vid))


async def delete_product(wcapi: WC_API, pid, forced=True):
    return await wcapi.delete("products/%s?force=%s" % (pid, str(forced).lower()))


if __name__ == '__main__':
    wcapi = WC_API(
        url="https://liningfa.felfeli-lab.ir",
        consumer_key="ck_4665c75a6fadda6680bde8cb95681f94cb38b12a",
        consumer_secret="cs_83a9e7154f4cc33a76de6f5d567b0082a33fd128",
        wp_api=True,
        version="wc/v3"
    )
    print('Done!')
