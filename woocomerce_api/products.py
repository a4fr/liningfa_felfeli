from woocomerce_api.woocomerce import API as WC_API
from pprint import pprint


def update_product(wcapi: WC_API):
    # update product
    data = {
        'sku': 'LNL4487',
        'price': '750000',
        'regular_price': '730000',
        'sale_price': '',
    }
    return wcapi.put("products/1077", data).json()


def add_variation(wcapi: WC_API, pid, attribute, regular_price, sale_price):
    data = {
        "regular_price": regular_price,
        "sale_price": sale_price,
        "attributes": list(),
    }
    data["attributes"].append(attribute)
    return wcapi.post("products/%s/variations" % pid, data).json()


def get_all_variations(wcapi: WC_API, pid):
    return wcapi.get("products/%s/variations" % pid).json()


def delete_variation(wcapi: WC_API, pid, vid):
    return wcapi.delete("products/%s/variations/%s" % (pid, vid)).json()


def delete_product(wcapi: WC_API, pid, forced=True):
    return wcapi.delete("products/%s?force=%s" % (pid, str(forced).lower())).json()


if __name__ == '__main__':
    wcapi = WC_API(
        url="https://liningfa.felfeli-lab.ir",
        consumer_key="ck_4665c75a6fadda6680bde8cb95681f94cb38b12a",
        consumer_secret="cs_83a9e7154f4cc33a76de6f5d567b0082a33fd128",
        wp_api=True,
        version="wc/v3"
    )
    print('Done!')
