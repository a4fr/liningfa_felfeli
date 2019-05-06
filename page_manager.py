import concurrent.futures
import asyncio
from woocomerce_api.woocomerce import API as WC_API
from woocomerce_api_async.woocomerce import API as WC_API_ASYNC
from woocomerce_api_async import products as wc_product
from pprint import pprint
import json
import Config
import logging
import sqlite3
import time


def get_product_details_from_db(pid, with_liningfa_pid=False, db_name='felfeli.db') -> dict:
    """ details marboot be lining_pid ro az database dar miare
    :param pid:
    :param with_liningfa_pid: ba in pid details ro peyda mikone
    :param db_name:
    :return: dict: details
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    if with_liningfa_pid:
        c.execute(""" SELECT json FROM details WHERE liningfa_pid=? """, (pid,))
    else:
        c.execute(""" SELECT json FROM details WHERE lining_pid=? """, (pid,))
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


def create_products_page_on_website_concurrently(lining_pids_categories: list, wcapi, max_worker: int = 4):
    """ create page on website concurrently
    :param lining_pids_categories: [{lining_pid:.., categories:...}, ...`]
    :param wcapi: WCAPI
    :param max_worker: int, number of worker
    :return: {lining_pid:liningfa_pid, ...}
    """
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_worker) as executor:
        workers = dict()
        for data in lining_pids_categories:
            lining_pid = data['lining_pid']
            if 'categories' in data:
                categories = data['categories']
            else:
                categories = None

            workers[lining_pid] = executor.submit(create_product_page_on_website, lining_pid, wcapi, categories)
            logging.debug('Adding lining[%s] to queue...' % lining_pid)

        results = dict()
        for lining_pid, worker in workers.items():
            logging.info('Waiting for page of lining[%s] in liningfa...' % lining_pid)
            result = worker.result()
            results[lining_pid] = result


def save_liningfa_pid_in_db(lining_pid_liningfa_pid: list, db_name='felfeli.db'):
    """ ye list migire va liningfa_pid ro be database ezafe mikone
    :param lining_pid_liningfa_pid: [{lining_pid:..., liningfa_pid:...}, {lining_pid:..., liningfa_pid:...}]
    :param db_name: str
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    for d in lining_pid_liningfa_pid:
        logging.debug('Updating %s on database...' % repr(d))
        c.execute(""" UPDATE details SET "liningfa_pid"=? WHERE "lining_pid"=? """, (
            d['liningfa_pid'],
            d['lining_pid'],
        ))
    conn.commit()
    conn.close()


def create_products_page_on_website_async(lining_pids_categories: list, wcapi, max_number_semaphore: int = 100, forced_to_update_page=True):
    """ safahat ro besoorat async misaze
    :param lining_pids_categories: [{lining_pid:.., categories:...}, ...`]
    :param wcapi:
    :param max_number_semaphore: tedad request haye hamzaman
    :param forced_to_update_page: bool: besoorat force age True bashe safhe mojood ro update mikone (bakhsh tozihat)
    :return:
    """

    # Prepair data for send requests to API
    details = dict()
    all_data = dict()
    products = dict()
    for data in lining_pids_categories:
        lining_pid = data['lining_pid']
        categories = data['categories']
        detail = get_product_details_from_db(lining_pid, db_name=Config.DB.name)

        # check mikone aya ax haye mahsool upload shodan yana
        images = get_liningfa_urls_from_db(detail['slider_images'] + detail['description_images'])
        all_images_uploaded = True
        for lining_url, liningfa_url in images.items():
            if not liningfa_url:
                logging.debug('A few images not uploaded! like: %s' % lining_url)
                all_images_uploaded = False
        if not all_images_uploaded:
            logging.info('LiningPoduct[%s] can\'t create, first upload all images!' % lining_pid)
        else:
            #################################################
            # age ok bood be list ezafe mikone ##############
            # async notebook PAHSE-1 ########################
            #################################################
            details[lining_pid] = detail
            #################################################

            # prepair data for create product
            onsale_sizes = [size[1] for size in detail['all_sizes'] if size[2] == 'onsale']
            data = {
                'name': 'کفش کتانی لینینگ مدل ' + detail['sku'],
                'sku': detail['sku'],
                'type': 'variable',
                'status': 'publish',
                'description': '\n'.join(
                    ['<p style="text-align: center;"><img src="%s"/></p>' % images[src] for src in
                     detail['description_images']]),
                'short_description': '',
                'images': [{'src': images[url]} for url in detail['slider_images']],
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

            # add data to all_data
            all_data[lining_pid] = data

    # send request to API
    loop = asyncio.get_event_loop()
    tasks = []
    lining_pids = []
    for lining_pid, data in all_data.items():
        logging.info('Trying to create page for lining_pid[%s] in liningfa...' % lining_pid)
        data = all_data[lining_pid]
        task = asyncio.ensure_future(wcapi.post('products', data))
        tasks.append(task)
        lining_pids.append(lining_pid)
    futures = asyncio.gather(*tasks, return_exceptions=True)
    results = loop.run_until_complete(futures)

    # list of products that exist on liningfa
    # send request to API [for update exists products]
    loop = asyncio.get_event_loop()
    lining_pids_error_400 = list()
    tasks_lining_pids_error_400 = []
    for i in range(len(results)):
        lining_pid = lining_pids[i]
        r = results[i]
        response = r.json()
        if r.status_code == 400:
            logging.info('Product already exists. [ID: %s]' % response['data']['resource_id'])
            if forced_to_update_page:
                data = all_data[lining_pid]
                task = asyncio.ensure_future(wcapi.put('products/%s' % response['data']['resource_id'], data))
                tasks_lining_pids_error_400.append(task)
            else:
                products[lining_pid] = {'id': response['data']['resource_id']}
            lining_pids_error_400.append(lining_pid)
        else:
            products[lining_pid] = response
    futures = asyncio.gather(*tasks_lining_pids_error_400, return_exceptions=True)
    results = loop.run_until_complete(futures)

    # update response of exists products
    for i in range(len(results)):
        lining_pid = lining_pids_error_400[i]
        r = results[i]
        response = r.json()
        products[lining_pid] = response

    # save liningfa_pid on db
    save_liningfa_pid_in_db(
        [{'lining_pid': lining_pid, 'liningfa_pid': p['id']} for lining_pid, p in products.items()]
    )


def update_variations_async(liningfa_pids, wcapi, sem=None):
    """ list liningfa_pid migire, variation ha ro darmiaye va upate mikone
    :param liningfa_pids: list: [pid, pid, ...]
    """
    if not sem:
        sem = asyncio.Semaphore(Config.Async.num_semaphore_variations)
    variations = dict()
    loop = asyncio.get_event_loop()
    tasks = []
    # getting all variations
    for liningfa_pid in liningfa_pids:
        logging.info('Getting variations pid-%s...' % liningfa_pid)
        tasks.append(asyncio.ensure_future(wc_product.get_all_variations(wcapi, liningfa_pid, asyc_semaphore=sem)))
    results = loop.run_until_complete(asyncio.gather(*tasks))

    # deleting all variations
    # and adding new variations
    loop = asyncio.get_event_loop()
    tasks = []
    for i in range(len(liningfa_pids)):
        # delete variations
        liningfa_pid = liningfa_pids[i]
        variations = results[i].json()
        for v in variations:
            logging.info('Deleting variation[%s]...' % v['id'])
            tasks.append(asyncio.ensure_future(
                wc_product.delete_variation(wcapi, liningfa_pid, v['id'], asyc_semaphore=sem)
            ))
        # add variations
        details = get_product_details_from_db(liningfa_pid, with_liningfa_pid=True)
        onsale_sizes = [size[1] for size in details['all_sizes'] if size[2] == 'onsale']
        for size in onsale_sizes:
            attribute = {
                'name': 'سایز',
                'option': size
            }
            logging.info('Adding Variation pid-%s(size=%s)...' % (liningfa_pid, size))
            tasks.append(
                wc_product.add_variation(
                    wcapi,
                    liningfa_pid,
                    attribute,
                    details['price_offer'],
                    details['price'],
                    asyc_semaphore=sem,
                )
            )
    loop.run_until_complete(asyncio.gather(*tasks))


def test_create_products_page_on_website_async():
    wcapi = WC_API_ASYNC(
        url="https://liningfa.felfeli-lab.ir",
        consumer_key="ck_4665c75a6fadda6680bde8cb95681f94cb38b12a",
        consumer_secret="cs_83a9e7154f4cc33a76de6f5d567b0082a33fd128",
        wp_api=True,
        version="wc/v3",
        timeout=30,
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
    lining_pids_categories = [
        {
            'lining_pid': 561792,
            'categories': None
        },
        {
            'lining_pid': 560505,
            'categories': None
        },
        {
            'lining_pid': 561970,
            'categories': categories
        },
        {
            'lining_pid': 559932,
            'categories': categories
        },
        {
            'lining_pid': 561204,
            'categories': categories
        },
    ]
    create_products_page_on_website_async(
        lining_pids_categories,
        wcapi,
        forced_to_update_page=False,
    )



def test_create_products_page_on_website_concurrently():
    wcapi = WC_API(
        url="https://liningfa.felfeli-lab.ir",
        consumer_key="ck_4665c75a6fadda6680bde8cb95681f94cb38b12a",
        consumer_secret="cs_83a9e7154f4cc33a76de6f5d567b0082a33fd128",
        wp_api=True,
        version="wc/v3",
        timeout=30,
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
    lining_pids_categories = [
        {
            'lining_pid': 561792,
            'categories': None
        },
        {
            'lining_pid': 560505,
            'categories': None
        },
        {
            'lining_pid': 561970,
            'categories': categories
        },
        {
            'lining_pid': 559932,
            'categories': categories
        },
        {
            'lining_pid': 561204,
            'categories': categories
        },
    ]
    create_products_page_on_website_concurrently(
        lining_pids_categories,
        wcapi,
        max_worker=1
    )


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
    # test_create_product_page_on_website()
    # test_create_products_page_on_website_concurrently()
    test_create_products_page_on_website_async()
    print('Done! (%.1fs)' % (time.time()-time_start))
