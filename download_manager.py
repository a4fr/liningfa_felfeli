import Config
import logging
import os
import requests
import time
import concurrent.futures
import sqlite3
from pprint import pprint
import arrow


def download_image_worker(image_url: str) -> bytes:
    """ image ro download mikone va binary ro return mikone
    :param image_url: str
    :return: binary
    """
    time_start = time.time()
    r = requests.get(image_url.strip())
    dl_time = time.time() - time_start
    if r.status_code == 200:
        dl_size = len(r.content)
        return r.content
    else:
        raise Exception('Download Error!')


def save_image_binary(image_binary: bytes, path: str) -> bool:
    """ image ro be soorat binary migira va zakhire mikone
    :param image_binary: bytes
    :param path: str: addressi ke image zakhire mishe
    :return: Boolean
    """
    with open(path, 'wb') as file:
        file.write(image_binary)
    return True


def download_and_save_image_worker(image_url: str, path: str):
    """ worker vase download va save image
    :param image_url: str
    :param path: str
    :return:
    """
    image_bin = download_image_worker(image_url)
    save_image_binary(image_bin, path)


def extract_filename_from_url(url: str) -> str:
    """
    https://cdns.lining.com/postsystem/docroot/images/goods/201808/424806/detail_424806_1.jpg
    (To) -> detail_424806_1.jpg
    """
    # logging.debug('URL: %s' % url)
    url = url.strip()
    return url[url.rfind('/')+1:]


def normalize_saving_path_dir(dir_path: str) -> str:
    """ path bayad besoorat path/to/dir/ basge
    akaresh bayad / dashte bashe
    """
    if dir_path[-1] != '/':
        dir_path += '/'
    return dir_path


def download_images_concurrently(image_urls: list, saving_path_dir='images/', max_worker=4):
    """ ye list az url migire va besoorat movazi download mikard
    :param image_urls: list url ha
    :param saving_path_dir: pooshe'i ke image ha toosh zakhire mishe mesl /home/user/felfeli/images/
    :param max_worker: max tedad worker tooye ThreadingPool ProcessingPool
    :return:
    """

    # directory saving_path_dir ro missaze
    try:
        logging.debug('Creating directory "%s"...' % saving_path_dir)
        os.mkdir(saving_path_dir)
    except FileExistsError:
        logging.debug('Directory "%s" was already exist!' % saving_path_dir)
        pass

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_worker) as executor:
        workers = dict()
        for url in image_urls:
            filename = extract_filename_from_url(url)
            path = normalize_saving_path_dir(saving_path_dir) + filename
            if not os.path.exists(path) or \
                    (os.path.exists(path) and not os.path.getsize(path)):
                logging.debug('%s -> %s' % (path, url))
                worker = executor.submit(download_and_save_image_worker, url, path)
                workers[filename] = worker
            else:
                logging.info('File "%s" already exist!' % path)

        for filename, worker in workers.items():
            logging.info('Waiting for %s...' % filename)
            worker.result()


def download_all_images_in_db(db_name: str='felfeli.db'):
    """ Tamam URL ha ro az db darmiare va download mikone
    :param db_name: esm datanbase
    """
    # list url ha'i ke bayad download shavand
    logging.debug('Creating Connection with "%s" DataBase...' % db_name)
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(""" SELECT id, lining_url, last_update FROM images WHERE liningfa_url is null or liningfa_url is '' """)
    images = c.fetchall()

    # download url ha
    urls = [image[1] for image in images]
    download_images_concurrently(urls, max_worker=4)

    # berooz resani field last_update
    datetime_now = str(arrow.now('Asia/Tehran'))
    c.executemany(""" UPDATE images SET last_update=? WHERE id=? """, [(datetime_now, image[0]) for image in images])
    logging.info('Updating last_update[%s] field...' % datetime_now)
    conn.commit()

    # close DB connection
    logging.debug('Closing "%s" database...' % db_name)
    conn.close()


def test_download_all_images_in_db():
    download_all_images_in_db(db_name=Config.DB.name)


def test_download_and_save_image():
    url = 'http://xiaomi-fa.com/store/wp-content/uploads/2019/04/IMG_20190416_190029-880x640.jpg'
    image = download_image_worker(url)
    save_image_binary(image, 'image.jpg')


def test_download_images_concurrently():
    urls = [
        'http://xiaomi-fa.com/store/wp-content/uploads/2019/04/IMG_20190416_190029-880x640.jpg',
        'http://xiaomi-fa.com/store/wp-content/uploads/2019/04/IMG_20190416_190129-880x695.jpg',
        'http://xiaomi-fa.com/store/wp-content/uploads/2019/04/IMG_20190416_190109-1-880x823.jpg',
        'http://xiaomi-fa.com/store/wp-content/uploads/2019/04/IMG_20190416_190056-880x629.jpg',
        'http://xiaomi-fa.com/store/wp-content/uploads/2019/04/IMG_20190416_194537-664x880.jpg',
        'http://xiaomi-fa.com/store/wp-content/uploads/2019/04/IMG_20190416_190040-817x880.jpg',
        'http://xiaomi-fa.com/store/wp-content/uploads/2019/04/Screenshot_2019-04-16-19-46-56-194_com.android.chrome-797x880.jpg',
        'http://xiaomi-fa.com/store/wp-content/uploads/2019/04/IMG_20190416_194524-622x880.jpg',
    ]
    download_images_concurrently(urls[:], 'images', max_worker=4)


if __name__ == '__main__':
    time_start = time.time()
    logging.basicConfig(
        level=logging.DEBUG,
        format=Config.Logging.format
    )
    test_download_all_images_in_db()
    print('Done! %.2f' % (time.time() - time_start))
