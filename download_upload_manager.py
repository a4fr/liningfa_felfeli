import os
import requests
import time


def worker_download_image(image_url: str) -> bytes:
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


if __name__ == '__main__':
    url = input('Enter URL: ')
    image = worker_download_image(url)
    save_image_binary(image, 'image.jpg')
    print('Done!')
