import os
import time
import logging
import Config
import concurrent.futures
import download_manager
import wp_api


def upload_image_worker(image_path: str):
    """ image_path ro migira va ax ro upload mikone rooye website
    dar nahayat address rooye website ro barmigardoone
    :param image_path: str
    :return: str: liningfa_url: url upload shode rooye website
    """
    logging_data = {
        'username': Config.WPAPI.username,
        'password': Config.WPAPI.password,
    }
    res = wp_api.upload_image(image_path, logging_data)
    liningfa_url = res['url']
    return liningfa_url


def upload_images_concurrently(image_paths: list, saving_path_dir='images/', max_worker=4):
    """ ye list az url migire va besoorat movazi upload mikard
    :param image_urls: list url ha
    :param saving_path_dir: pooshe'i ke image ha toosh zakhire mishe mesl /home/user/felfeli/images/
    :param max_worker: max tedad worker tooye ThreadingPool ProcessingPool
    :return:
    """

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_worker) as executor:
        workers = dict()
        for path in image_paths:
            if os.path.exists(path) and os.path.getsize(path):
                logging.info('Uploading %s...' % path)
                filename = download_manager.extract_filename_from_url(url)
                worker = executor.submit(upload_image_worker, path, path)
                workers[filename] = worker
            else:
                logging.info('File "%s" not exist!' % path)

        for filename, worker in workers.items():
            logging.info('Waiting for %s...' % filename)
            worker.result()


if __name__ == '__main__':
    time_start = time.time()
    logging.basicConfig(
        level=logging.DEBUG,
        format=Config.Logging.format
    )
    images_url = [
        'https://cdns.lining.com/postsystem/docroot/images/goods/201903/465050/detail_465050_2.jpg',
        'https://cdns.lining.com/postsystem/docroot/images/goods/201903/465050/detail_465050_3.jpg',
        'https://cdns.lining.com/postsystem/docroot/images/goods/201903/465050/detail_465050_6.jpg',
        'https://cdns.lining.com/postsystem/docroot/images/goods/201903/465050/detail_465050_9.jpg',
    ]
    for url in images_url:
        filename = download_manager.extract_filename_from_url(url)
        path = download_manager.normalize_saving_path_dir('images/') + filename
        print(path)
        print(upload_image_worker(path))
    print('Done! %.2f' % (time.time() - time_start))