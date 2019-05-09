import sys
import concurrent.futures
import arrow
import sqlite3
from pprint import pprint
import logging
import time
import requests
from bs4 import BeautifulSoup
import re
import pickle
import os
import json
import Config


def get_html(url: str) -> str:
    """ HTML link ro khoroji mide
    """
    headers = {
        'User-Agent': Config.Scraper.user_agent,
    }
    logging.debug('User-Agent: ' + headers['User-Agent'])
    r = requests.get(url.strip(), headers=headers)
    r.encoding = 'utf8'
    logging.info('[Status Code: %s]' % r.status_code)
    if r.status_code != 200:
        raise Exception('Error in get HTML!')
    return r.text


def get_json(url, data) -> dict:
    """ json link ro khorooji mide
    """
    headers = {
        # 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36',
    }
    # logging.debug('User-Agent: ' + headers['User-Agent'])
    logging.debug('url: ' + url)
    logging.debug('data: ' + repr(data))
    r = requests.post(url.strip(), data=data, headers=headers)
    r.encoding = 'utf8'
    logging.info('[Status Code: %s]' % r.status_code)
    if r.status_code != 200:
        raise Exception('Error in get Json!')
    return r.json()


def get_soup(url: str) -> BeautifulSoup:
    """ link ro migire html oon ro dar miare va tabdil be Soup mikone
    """
    html = get_html(url)
    soup = BeautifulSoup(html, 'lxml')
    return soup


def get_products(category_url):
    """ List tamam mahsoolat ye daste be hamrah moshakhasat avalie vase daryaft data
    :param category_url: url marboot be category lining.com
    :return: list: [
            product = {
            'name': None,
            'price': None,
            'thumbnail_img': None,
            'url': None,
            'id': Str
            'bundles_url': list(),
        }
    ]
    """
    soup = get_soup(category_url)

    products = list()
    for item in soup.find_all('div', {'class': 'selItem'}):
        product = dict()

        sel_main_pic = item.find('div', {'class': 'selMainPic'})
        product['url'] = sel_main_pic.find('a').get('href').replace('?procmp=listproduct', '')
        product['id'] = re.findall('store.lining.com/shop/goods-(\w+).html\w*', product['url'])[0]
        product['thumbnail'] = sel_main_pic.find('img').get('src')
        logging.debug('Parsing Product %s...' % product['id'])

        product['name'] = item.find('div', {'class': 'hgoodsName'}).text.strip()
        product['price'] = float(item.find('div', {'class': 'hprice price'}).text.strip().replace('￥', ''))

        # list bundle ro dar miare
        bundles = list()
        for bundle in item.find_all('div', {'class': 'slaveItem'}):
            bundles.append(bundle.get('url'))
            # print(bundle)
        product['bundles_url'] = bundles

        products.append(product)
    return products


def get_product_details(product_url: str) -> dict:
    """ Estekhraj data haye safhe mahsool """
    def get_available_sizes(postID, sizeStr, product_mainID):
        """
        List size haye mojood va tamoom shode ro ba API mide
        POST: https://store.lining.com/ajax/goods_details.htm
        """
        api_url = 'https://store.lining.com/ajax/goods_details.html'
        data = {
            'postID': postID,
            'sizeStr': sizeStr,
            'product_mainID': product_mainID
        }
        r = get_json(api_url, data=data)
        onsale_sizes = r['data']['onSale']
        logging.debug('Onsale Sizes: ' + repr(onsale_sizes))
        return onsale_sizes

    def get_pid_from_url(url):
        """ ID mahsool ro az URL darmiare """
        return re.findall(r'store.lining.com/shop/goods-(\w+).html\w*', url)[0]

    def translate_keyword(keyword):
        """ tarjome key marboot be desctioption """
        define = {
            '运动类型': 'Sport Type',
            '性别': 'Sex',
            '颜色': 'Color',
            '鞋透气指数': 'Shoes breathability index',
            '鞋软硬指数': 'Shoe soft and hard index',
        }
        if keyword in define:
            return define[keyword]
        else:
            return keyword
    ###########################################################

    details = dict()
    soup = get_soup(product_url)

    # product ID
    pid = get_pid_from_url(product_url)
    logging.debug('PID: ' + pid)
    details['pid'] = pid

    # product name
    name = soup.find('h1', {'id': 'product_name'}).text.strip()
    logging.debug('Name: ' + name)
    details['name'] = name

    # part number
    sku = soup.find('span', {'id': 'partNumber'}).find('span', {'class': 'v'}).text.strip()
    part_number = sku[0:sku.find('-')]
    logging.debug('Part Number: ' + part_number)
    details['sku'] = sku
    details['part_number'] = part_number

    # price
    price = soup.find('span', {'id': 'listPrice'}).find('span', {'class': 'v'}).text.strip().replace('￥', '')
    price_offer = soup.find('span', {'id': 'offerPrice'}).find('span', {'class': 'v'}).text.strip().replace('￥', '')
    logging.debug('Price: %s    [offer]-> %s' % (price, price_offer))
    details['price'] = price
    details['price_offer'] = price_offer

    # all sizes
    all_sizes = list()
    for tag in soup.find('div', {'id': 'sizelist'}).find_all('div', 'size-layer'):
        tag = tag.find('input')
        # all_size -> [(id, size, status), ...]
        all_sizes.append(
            (
                tag.get('id').replace('size_list_', ''),
                tag.get('value'),
                None,
            )
        )
    available_sizes = get_available_sizes(
        postID=pid,
        product_mainID=part_number,
        # first element of all_sizes list
        # all_size -> [(id, size, status), ...]
        sizeStr=','.join([s[0] for s in all_sizes]),
    )
    # update all sizes status
    for i in range(len(all_sizes)):
        if all_sizes[i][1] in available_sizes:
            all_sizes[i] = (
                all_sizes[i][0],
                all_sizes[i][1],
                'onsale',
            )
        else:
            all_sizes[i] = (
                all_sizes[i][0],
                all_sizes[i][1],
                'stockout',
            )
    logging.debug('All Sizes: %s' % repr(all_sizes))
    details['all_sizes'] = all_sizes

    # description images
    description_images = list()
    desc = soup.find('div', {'id': 'PD_desc_picture'})
    for img in desc.find_all('img'):
        img = img.get('orginalsrc')
        logging.debug('description_images[]: ' + img)
        description_images.append(img)
    details['description_images'] = description_images

    # description key/value
    description = dict()
    for li in soup.find('ul', {'id': 'p_spec'}).find_all('li'):
        key = li.find('span', {'class': 't'}).text.replace(':', '').strip()
        key = translate_keyword(key)
        value = li.find('span', {'class': 'v'}).text.strip()
        description[key] = value
        logging.debug('%s -> %s' % (key, value))
    details['description'] = description

    # slider images
    slider_images = list()
    for li in soup.find('div', {'class': 'box'}).find_all('li'):
        img = li.find('img').get('big')
        logging.debug('slider_images[]: ' + img)
        slider_images.append(img)
    details['slider_images'] = slider_images

    # related products
    related_products_id = list()
    for li in soup.find('div', {'id': 'f_litimg'}).find_all('li'):
        url = li.find('a').get('href')
        url = 'store.lining.com' + url
        pid = get_pid_from_url(url)
        logging.debug('related_products_id[]: %s -> %s' % (pid, url))
        related_products_id.append(pid)
    details['related_products_id'] = related_products_id

    return details


def saved_product_details_on_db(lining_pid, details: dict, db_name='felfeli.db'):
    """ Detail ro migire va tooye database zakhire mikone
    :param lining_pid: id mahsool tooye lining.com
    :param details: dict
    :param db_name: esm database
    :return akharin data zakhire shode rooye db lining_pid
    """
    logging.debug('Creating Connection with "%s" DataBase...' % db_name)
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(""" SELECT * FROM details WHERE lining_pid=? """, (lining_pid,))
    data = c.fetchone()

    details_json = json.dumps(details)
    datetime_now = str(arrow.now('Asia/Tehran'))
    if data:
        # update row
        row_id = data[0]
        c.execute(""" UPDATE details SET json=?, last_update=? WHERE id=? """, (details_json, datetime_now, row_id))
        conn.commit()
    else:
        # create row
        c.execute(""" INSERT INTO details (lining_pid, json, last_update) VALUES (?, ?, ?) """, (lining_pid, details_json, datetime_now))
        conn.commit()

    c.execute(""" SELECT * FROM details WHERE lining_pid=? """, (lining_pid,))
    data = c.fetchone()
    conn.close()
    return data


def get_product_details_concurrently(products: list, max_worker=4, save_in_db=True,  db_name='felfeli.db') -> dict:
    """ besoorat concurrent ejra mikone
    :param products: list: [
        {'pid':..., 'url':...},
        {'pid':..., 'url':...},
        {'pid':..., 'url':...},
    ]
    :return dict: {
        pid: result,
        pid: result,
        pid: result,
    }
    """
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_worker) as executor:
        workers = dict()
        for p in products:
            logging.debug('Submitting product#%s...' % p['pid'])
            workers[p['pid']] = executor.submit(get_product_details, p['url'])

    # gereftan khoroji
    results = dict()
    for pid, worker in workers.items():
        logging.info('Watting for product#%s...' % pid)
        result = worker.result()
        results[pid] = result
        if save_in_db:
            # save detail in db
            saved_product_details_on_db(
                lining_pid=pid,
                details=result,
                db_name=db_name
            )

            # save images of description and slider in db
            add_images_url_in_db(
                result['description_images'] + result['slider_images'],
                db_name=db_name,
            )
    logging.info('%s products processed saved!' % len(results))
    return results


def add_images_url_in_db(urls: list, db_name='felfeli.db'):
    """ ye list az URL migire va oonaro tooye db.images zakhire mikone
    :param urls: list url haye ax
    :param db_name: str
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    datetime_now = str(arrow.now('Asia/Tehran'))
    for url in urls:
        # check is exist
        logging.debug('Searching for "%s" in DB...' % url)
        c.execute(""" SELECT id FROM images WHERE lining_url=? """, (url,))
        row = c.fetchone()

        # add to db if not exist
        if not row:
            logging.info('Adding "%s" to DB...' % url)
            c.execute(""" INSERT INTO images (lining_url, last_update) VALUES (?, ?) """, (url, datetime_now))
            conn.commit()
    conn.close()


def get_product_details_with_lining_pid(lining_pid):
    p_url = 'https://store.lining.com/shop/goods-%s.html' % lining_pid
    details = get_product_details(p_url)
    saved_product_details_on_db(lining_pid=lining_pid, details=details)


def get_all_pages_of_category(category_url):
    """
        URL Category ro migire va safhe roo analyse mikone
        :param category_url: link daste
        """

    def extract_number(text):
        """ Return number of pages """
        # logging.debug('Paging text: ' + text.strip())
        nums = re.findall('共(\d+)页', text)
        # logging.debug('nums=' + repr(nums))
        if len(nums) == 0:
            raise Exception('There is no number!')
        return int(nums[0])

    ###############################################

    soup = get_soup(category_url)
    num_pages = extract_number(soup.find('span', {'class': 'paging'}).text)
    current_page = int(soup.find('span', {'class': 'selpage'}).text)
    logging.debug('This category has %s page(s)' % num_pages)
    logging.debug('You are in page %s' % current_page)

    all_pages_url = list()
    splited_url = category_url.split(',')
    part_one = ','.join(splited_url[0:2])
    part_two = ','.join(splited_url[3:])
    url_pattern = part_one + ',%s,' + part_two
    for p_number in range(1, num_pages + 1):
        page_url = url_pattern % p_number
        all_pages_url.append(page_url)
    return all_pages_url


def test_get_all_pages_of_category():
    category_url = 'https://store.lining.com/shop/goodsCate-sale,desc,1,15s15_122,15_122,15_122_m,15_122s15_122_10,15_122_10-0-0-15_122_10,15_122_10-0s0-0-0-min,max-0.html'
    logging.info('Getting all pages of category...')
    all_pages = get_all_pages_of_category(category_url)
    for i in range(len(all_pages)):
        logging.info('page[%s] %s' % (i+1, all_pages[i]))


def get_products_of_category(category_url):
    category_url = 'https://store.lining.com/shop/goodsCate-sale,desc,1,15s15_122,15_122,15_122_m,15_122s15_122_10,15_122_10-0-0-15_122_10,15_122_10-0s0-0-0-min,max-0.html'
    logging.info('Getting all pages of category...')
    products = get_products(category_url)
    pprint(products)


def test_get_product_detail():
    p_url = 'https://store.lining.com/shop/goods-529859.html'
    details = get_product_details(p_url)
    pprint(details)


def test_saved_product_details_on_db():
    lining_pid = 529859
    details = {
        'all_sizes': [('529865', '39', 'onsale'),
               ('529870', '39.5', 'onsale'),
               ('529860', '40', 'onsale'),
               ('529861', '41', 'onsale'),
               ('529862', '41.5', 'onsale'),
               ('529863', '42', 'onsale'),
               ('529869', '43', 'onsale'),
               ('529859', '43.5', 'onsale'),
               ('529866', '44', 'onsale'),
               ('529867', '45', 'onsale'),
               ('529868', '45.5', 'stockout'),
               ('529864', '46', 'stockout')],
 'description': {'Color': '夜空蓝/海豚蓝',
                 'Sex': '男',
                 'Shoe soft and hard index': '柔软',
                 'Shoes breathability index': '较透气/适中',
                 'Sport Type': '羽毛球',
                 '展示面料': 'PU(油墨印刷)+纺织品',
                 '鞋底': '橡胶+EVA'},
 'description_images': ['https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/detail_439675_1.jpg',
                        'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/detail_439675_2.jpg',
                        'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/detail_439675_3.jpg',
                        'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/detail_439675_4.jpg',
                        'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/detail_439675_5.jpg',
                        'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/detail_439675_6.jpg',
                        'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/detail_439675_7.jpg',
                        'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/detail_439675_8.jpg',
                        'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/detail_439675_9.jpg',
                        'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/detail_439675_10.jpg',
                        'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/detail_439675_11.jpg',
                        'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/detail_439675_12.jpg'],
 'name': '羽毛球系列男子羽毛球训练鞋',
 'part_number': 'AYTN035',
 'pid': '529859',
 'price': '499.00',
 'price_offer': '349.00',
 'related_products_id': ['506532', '529728', '506523', '533027', '533808'],
 'sku': 'AYTN035-1',
 'slider_images': ['https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/max_display_439675_1.jpg',
                   'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/max_display_439675_2.jpg',
                   'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/max_display_439675_3.jpg',
                   'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/max_display_439675_4.jpg',
                   'https://cdns.lining.com/postsystem/docroot/images/goods/201812/439675/max_display_439675_5.jpg']}
    data = saved_product_details_on_db(lining_pid, details)
    pprint(data)


def test_get_products_detail_concurrently():
    products = [
        {'pid': '533969',
         'url': 'https://store.lining.com/shop/goods-533969.html'},
        {'pid': '324521',
         'url': 'https://store.lining.com/shop/goods-324521.html'},
        {'pid': '529859',
         'url': 'https://store.lining.com/shop/goods-529859.html'},
        {'pid': '533957',
         'url': 'https://store.lining.com/shop/goods-533957.html'},
        # {'pid': '438658',
        #  'url': 'https://store.lining.com/shop/goods-438658.html'},
    ]
    results = get_product_details_concurrently(products, max_worker=Config.DownloadUploadManager.max_worker)
    pprint(results)


def test_get_products_detail_concurrently_in_category(max_num=20):
    category_url = 'https://store.lining.com/shop/goodsCate-sale,desc,1,15s15_122,15_122,15_122_m,15_122s15_122_10,15_122_10-0-0-15_122_10,15_122_10-0s0-0-0-min,max-0.html'
    logging.info('Getting products URL...')
    products = get_products(category_url)
    if len(products) > max_num:
        products = products[:max_num]
    get_product_details_concurrently(
        products=[{'pid': p['id'], 'url': p['url']} for p in products],
        max_worker=Config.DownloadUploadManager.max_worker,
        db_name=Config.DB.name,
        save_in_db=True,
    )


def test_add_images_url_in_db():
    urls = [
        'https://cdns.lining.com/postsystem/docroot/images/goods/201712/348478/detail_348478_4.jpg',
        'https://cdns.lining.com/postsystem/docroot/images/goods/201712/348478/detail_348478_4.jpg',
        'https://cdns.lining.com/postsystem/docroot/images/goods/201806/405090/detail_405090_2.jpg',
        'https://cdns.lining.com/postsystem/docroot/images/goods/201806/405090/detail_405090_2.jpg',
    ]
    add_images_url_in_db(urls, db_name=Config.DB.name)


if __name__ == '__main__':
    time_start = time.time()
    logging.basicConfig(
        level=logging.DEBUG,
        format=Config.Logging.format
    )
    if len(sys.argv) >= 2:
        if sys.argv[1] == 'help':
            print("""database_manager.py [command]
        help                                    Show this help
        get_product_details_with_lining_pid     ...
    """)
        if sys.argv[1] == 'get_product_details_with_lining_pid':
            pid = input('Enter lining_pid: ')
            get_product_details_with_lining_pid(pid)
    else:
        # test_get_products_of_category()
        # test_get_product_detail()
        # test_saved_product_details_on_db()
        # test_get_products_detail_concurrently()
        # test_get_products_detail_concurrently_in_category(max_num=2000)
        test_get_all_pages_of_category()
        # test_add_images_url_in_db()
    print('Done! %.2f' % (time.time() - time_start))
