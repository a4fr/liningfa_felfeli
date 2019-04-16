import logging
import os
import requests
import time
import concurrent.futures


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
    logging.debug('URL: %s' % url)
    url = url.strip()
    return url[url.rfind('/')+1:]


def download_image_concurrently(image_urls: list, saving_path_dir='images/', max_worker=4):
    """ ye list az url migire va besoorat movazi download mikard
    :param image_urls: list url ha
    :param saving_path_dir: pooshe'i ke image ha toosh zakhire mishe mesl /home/user/felfeli/images/
    :param max_worker: max tedad worker tooye ThreadingPool ProcessingPool
    :return:
    """
    ##############################################################
    def normalize_saving_path_dir(dir_path: str) -> str:
        """ path bayad besoorat path/to/dir/ basge
        akaresh bayad / dashte bashe
        """
        if dir_path[-1] != '/':
            dir_path += '/'
        return dir_path
    ##############################################################

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
            logging.debug('%s -> %s' % (path, url))
            worker = executor.submit(download_and_save_image_worker, url, path)
            workers[filename] = worker

        for filename, worker in workers.items():
            logging.info('Waiting for %s...' % filename)
            worker.result()


if __name__ == '__main__':
    time_start = time.time()
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
    )
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
    # image = download_image_worker(url)
    # save_image_binary(image, 'image.jpg')
    download_image_concurrently(urls[:], 'images', max_worker=4)
    print('Done! %.2f' % (time.time() - time_start))
