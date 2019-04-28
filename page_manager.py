from woocomerce_api.woocomerce import API as WC_API
from woocomerce_api import products as wc_product
from pprint import pprint
import json
import Config
import logging
import sqlite3
import time


def get_product_details_from_db(lining_pid, db_name='felfeli.db') -> dict:
    """ details marboot be lining_pid ro az database dar miare
    :param lining_pid:
    :param db_name:
    :return: dict: details
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(""" SELECT json FROM details WHERE lining_pid=? """, (lining_pid,))
    row = c.fetchone()
    conn.close()
    details = row[0]
    details = json.loads(details)
    # logging.debug('details[%s] -> %s' % (lining_pid, details))
    return details


def get_liningfa_urls_from_db(lining_urls: list, db_name='felfeli.db'):
    """ ye list az lining_url migire va list liningfa_url tahvil mide
    :param lining_urls: list: [url, url]
    :return: dict: {lining_url: liningfa_url, ...}
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(""" SELECT lining_url, liningfa_url FROM images WHERE lining_url IN ('{0}') """.format("', '".join(lining_urls)))
    rows = c.fetchall()
    conn.close()
    #pprint(rows)

    # create dict
    images = dict()
    for row in rows:
        liningfa_url = row[1]
        if not liningfa_url:
            liningfa_url = None
        images[row[0]] = liningfa_url
    # check is all lining_urls was in images dict
    for url in lining_urls:
        if not (url in images):
            images[url] = None

    return images


def create_product_page_on_website(lining_pid, wcapi, categories=None):
    """ barasas data ha'i ke az website lining.com gereftim safhe mahsool ro tooyte website
    misaze. in data ha ba lining_pid toode table[details] mojoode
    :param lining_pid:
    :param wcapi: WCAPI: driver vaser api woocommerce
    :param categories: list: moghakas kardan daste mahsool dar woocaommerce
    :return: liningfa_pid
    """
    # get detaIls from db
    details = get_product_details_from_db(lining_pid, db_name=Config.DB.name)

    # create product on website
    # * check mikone aya ax haye mahsool upload shodan yana
    images = get_liningfa_urls_from_db(details['slider_images'] + details['description_images'])
    all_images_uploaded = True
    for lining_url, liningfa_url in images.items():
        if not liningfa_url:
            logging.debug('A few images not uploaded! like: %s' % lining_url)
            all_images_uploaded = False
    if not all_images_uploaded:
        logging.info('LiningPoduct[%s] can\'t create, first upload all images!' % lining_pid)
        return None

    # save woocommerce id and update last_update
    # prepair data for create product
    onsale_sizes = [size[1] for size in details['all_sizes'] if size[2] == 'onsale']
    data = {
        'name': 'کفش کتانی لینینگ مدل ' + details['sku'],
        'sku': details['sku'],
        'type': 'variable',
        'status': 'publish',
        'description': '\n'.join(
            ['<p style="text-align: center;"><img src="%s"/></p>' % images[src] for src in details['description_images']]),
        'short_description': '',
        'images': [{'src': images[url]} for url in details['slider_images']],
        'stock_status': 'instock',
        "attributes": [
            {
                "name": "سایز",
                "position": 0,
                "visible": True,
                "variation": True,
                "options": onsale_sizes
            }
        ],
        'tags': [
            {
                'id': 83,
            },
            {
                'id': 84,
            },
            {
                'id': 85,
            },
            {
                'id': 86,
            },
        ]
    }
    # add category to product id defined
    if categories:
        data['categories'] = categories

    # add or update product
    r = wcapi.post('products', data)
    response = r.json()
    # logging.debug('response: ' + repr(response))
    if r.status_code == 400:
        logging.info('Product already exists. [ID: %s]' % response['data']['resource_id'])
        r = wcapi.put('products/%s' % response['data']['resource_id'], data)
    product = r.json()
    # logging.debug('Product: ' + repr(product))
    logging.debug('Permalink[%s]: %s' % (product['id'], product['permalink']))

    # delete all variations
    logging.info('Delete All Variations...')
    variations = wc_product.get_all_variations(wcapi, product['id'])
    # logging.debug('All Variations: %s' % repr(variations))
    for v in variations:
        wc_product.delete_variation(wcapi, product['id'], v['id'])

    # add variations
    for size in onsale_sizes:
        attribute = {
            'name': 'سایز',
            'option': size
        }
        logging.info('Adding Variation (size=%s)...' % size)
        wc_product.add_variation(
            wcapi,
            product['id'],
            attribute,
            details['price_offer'],
            details['price'],
        )

        return product['id']


def test_create_product_page_on_website():
    pid = 561792
    wcapi = WC_API(
        url="https://liningfa.felfeli-lab.ir",
        consumer_key="ck_4665c75a6fadda6680bde8cb95681f94cb38b12a",
        consumer_secret="cs_83a9e7154f4cc33a76de6f5d567b0082a33fd128",
        wp_api=True,
        version="wc/v3",
        timeout=20,
    )
    categories = [
        {
            "id": 98
        },
        {
            "id": 95
        },
        {
            "id": 93
        },
    ]
    create_product_page_on_website(pid, wcapi=wcapi, categories=categories)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format=Config.Logging.format
    )
    time_start = time.time()
    test_create_product_page_on_website()
    print('Done! (%.1fs)' % (time.time()-time_start))
