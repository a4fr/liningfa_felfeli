class WPAPI:
    username = 'admin'
    password = '72XH w2Z4 d9cH POAt jbHH dlkK'
    media_api_endpoint = 'https://liningfa.felfeli-lab.ir/wp-json/wp/v2/media'


class Logging:
    format = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'


class DB:
    name = 'felfeli.db'


class DownloadUploadManager:
    saving_path_dir = 'images/'
    max_worker = 4


class Scraper:
    user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36'


class Async:
    num_semaphore_variations = 1