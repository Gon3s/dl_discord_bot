import os

import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


class AllDebrid:

    def __init__(self):
        self.api_key = os.getenv('ALLDEBRID_API_KEY')

    def debrid_link(self, url):
        r = requests.get(
            f'https://api.alldebrid.com/v4/link/unlock?agent=AlldebridBot&apikey={self.api_key}&link={url}'
        )

        if r.status_code != 200:
            assert False, r.status_code

        json = r.json()

        if json['status'] == 'error':
            assert False, json['error']['message']

        return json['data']
