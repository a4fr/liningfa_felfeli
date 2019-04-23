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


def test_get_products_of_category():
    category_url = 'https://store.lining.com/shop/goodsCate-sale,desc,1,15s15_122,15_122,15_122_m,15_122s15_122_10,15_122_10-0-0-15_122_10,15_122_10-0s0-0-0-min,max-0.html'
    logging.info('Getting products URL...')
    products = get_products(category_url)
    pprint(products)


def test_get_product_detail():
    p_url = 'https://store.lining.com/shop/goods-529859.html'
    details = get_product_details(p_url)
    pprint(details)


if __name__ == '__main__':
    time_start = time.time()
    logging.basicConfig(
        level=logging.INFO,
        format=Config.Logging.format
    )
    # test_get_products_of_category()
    test_get_product_detail()
    print('Done! %.2f' % (time.time() - time_start))
