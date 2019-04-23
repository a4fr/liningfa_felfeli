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


def test_get_products_of_category():
    category_url = 'https://store.lining.com/shop/goodsCate-sale,desc,1,15s15_122,15_122,15_122_m,15_122s15_122_10,15_122_10-0-0-15_122_10,15_122_10-0s0-0-0-min,max-0.html'
    logging.info('Getting products URL...')
    products = get_products(category_url)
    pprint(products)


if __name__ == '__main__':
    time_start = time.time()
    logging.basicConfig(
        level=logging.INFO,
        format=Config.Logging.format
    )
    test_get_products_of_category()
    print('Done! %.2f' % (time.time() - time_start))
