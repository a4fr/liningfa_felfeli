import requests
import os
from Config import WPAPI
from pprint import pprint
import logging


def upload_image(image_path, login_data):
    api_endpoint = WPAPI.media_api_endpoint
    data = open(image_path, 'rb').read()
    filename = os.path.basename(image_path)
    res = requests.post(
        url=api_endpoint,
        data=data,
        headers={
            'Content-Type': 'image/jpg',
            'Content-Disposition': 'attachment; filename=%s' % filename},
        auth=(login_data['username'], login_data['password'])
    )
    response = res.json()
    media_id = response.get('id')
    image_url = response.get('guid').get("rendered")
    return {
        'id': media_id,
        'url': image_url
    }


def delete_image(image_id, login_data):
    api_endpoint =WPAPI.media_api_endpoint + str(image_id)
    logging.info('Deletting %s...' % api_endpoint)
    res = requests.delete(
        url=api_endpoint,
        data={'force': True},
        auth=(login_data['username'], login_data['password'])
    )
    response = res.json()
    return response.get('deleted')


if __name__ == '__main__':
    login_data = {
        'username': WPAPI.username,
        'password': WPAPI.password,
    }
    print(upload_image('1.jpeg', login_data))
    image_id = input('Enter Image ID to delete: ')
    if image_id.strip() != '':
        print(delete_image(image_id, login_data))
