import os

import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


class AllDebrid:

    def __init__(self):
        self.api_key = os.getenv('ALLDEBRID_API_KEY')
        
    def redirect_link(self, url):
        r = requests.get(
            f'https://api.alldebrid.com/v4/link/redirector?agent=AlldebridBot&apikey={self.api_key}&link={url}'
        )
        
        if r.status_code != 200:
            assert False, r.status_code
            
        json = r.json()
        
        if json['status'] == 'error':
            assert False, json['error']['message']    
        
        return json['data']['links'][0]
      

    def debrid_link(self, url):
        print(f'Original link {url}')
        if 'dl-protect' in url:
            print('Redirect link')
            try:
                url = self.redirect_link(url)
            except AssertionError as e:
                assert False, 'Error redirect link'
                
        print(f'Debrid link {url}')
      
        r = requests.get(
            f'https://api.alldebrid.com/v4/link/unlock?agent=AlldebridBot&apikey={self.api_key}&link={url}'
        )

        if r.status_code != 200:
            assert False, r.status_code

        json = r.json()

        if json['status'] == 'error':
            assert False, json['error']['message']

        return json['data']
      
if __name__ == '__main__':
    alldebrid_client = AllDebrid()
    print(alldebrid_client.redirect_link('https://dl-protect.link/5807cb1b?fn=U2Vjb25kIHRvdXIgW1dFQi1ETCA3MjBwXSASRU5DSA%3D%3D&rl=a2'))