import arrow
from pprint import pprint
import sqlite3
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


def upload_images_concurrently(images: dict, saving_path_dir='images/',max_worker=4,
                               hook_function=None, hook_function_input=dict()):
    """ ye list az url migire va besoorat movazi upload mikard
    :param images: dict: shamele list url ha
    :param saving_path_dir: pooshe'i ke image ha toosh zakhire mishe mesl /home/user/felfeli/images/
    :param max_worker: max tedad worker tooye ThreadingPool ProcessingPool
    :param hook_function: function: result har worker ro be oon ersal mikone
    :param hook_function_input: dict: input vase hook_function
    :return:
    """

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_worker) as executor:
        workers = dict()
        for image in images:
            path = image['path']
            if os.path.exists(path) and os.path.getsize(path):
                logging.info('Uploading %s...' % path)
                filename = download_manager.extract_filename_from_url(path)
                worker = executor.submit(upload_image_worker, path)
                workers[filename] = {
                    'worker': worker,
                    'image_id': image['id']
                }
            else:
                logging.info('File "%s" not exist!' % path)

        for filename, data in workers.items():
            logging.info('Waiting for %s...' % filename)
            result = data['worker'].result()
            if hook_function:
                hook_function_input['liningfa_url'] = result
                hook_function_input['image_id'] = data['image_id']
                hook_function(hook_function_input)


def upload_all_images_in_db(db_name: str='felfeli.db'):
    """ Tamam URL ha ro az db darmiare va download mikone
    :param db_name: esm datanbase
    """
    # list url ha'i ke uoload nashode ro dar miare
    logging.debug('Creating Connection with "%s" DataBase...' % db_name)
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(""" SELECT id, lining_url, last_update FROM images WHERE liningfa_url is null or liningfa_url is '' """)
    db_images = c.fetchall()
    # pprint(db_images)

    # upload mikone
    images = []
    for image in db_images:
        filename = download_manager.extract_filename_from_url(image[1])
        path = download_manager.normalize_saving_path_dir('images/') + filename
        images.append({'id': image[0], 'path': path})
    upload_images_concurrently(
        images=images,
        saving_path_dir=Config.DownloadUploadManager.saving_path_dir,
        max_worker=Config.DownloadUploadManager.max_worker,
        hook_function=update_liningfa_url_in_db,
        hook_function_input={
            'db_cursor': c,
            'db_connection': conn
        },
    )

    # berooz resani field last_update
    datetime_now = str(arrow.now('Asia/Tehran'))
    c.executemany(""" UPDATE images SET last_update=? WHERE id=? """, [(datetime_now, image[0]) for image in db_images])
    logging.info('Updating last_update[%s] field...' % datetime_now)
    conn.commit()

    # close DB connection
    logging.debug('Closing "%s" database...' % db_name)
    conn.close()


def update_liningfa_url_in_db(func_input):
    """ liningfa_url ro tooye database update mikone
    :param func_input: dict :
        {
            cursor: db cursor,
            data: data'i ke gharare zakhire kone
            id: id marboot be lining_url
        }
    :return:
    """
    # pprint(func_input)
    c = func_input['db_cursor']
    conn = func_input['db_connection']
    c.execute(
        """ UPDATE images SET liningfa_url=? WHERE id=? """,
        (func_input['liningfa_url'], func_input['image_id']),
    )
    conn.commit()



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
    # for url in images_url:
    #     filename = download_manager.extract_filename_from_url(url)
    #     path = download_manager.normalize_saving_path_dir('images/') + filename
    #     print(path)
    #     print(upload_image_worker(path))
    upload_all_images_in_db()
    print('Done! %.2f' % (time.time() - time_start))
