import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import Driver, SB
from seleniumbase.fixtures.page_actions import is_element_enabled

XPATH_LINK = '//*[@id="protected-container"]/div[2]/div/ul/li/a'
SELECT_PROVIDER = '1fichier'


class Parser:
    def __init__(self, ctx=None, show_logs=False):
        self.ctx = ctx
        self.show_logs = show_logs
        self.log(f"Init Driver")
    
    def show_ctx(self, msg):
        """
        Send message to discord and print it
        :param msg:
        :return:
        """
        self.log(msg)
        if self.ctx:
            self.ctx.send(msg)
    
    def log(self, msg):
        """
        Print message
        :param msg:
        :return:
        """
        if self.show_logs:
            print(msg)
    
    def dl_protect(self, url):
        """
        Download link from dl-protect
        :param url:
        :return:
        """
        
        with SB(uc=True, headless=True) as sb:
            self.log(f"Goto {url}")
            sb.get(url)
            sb.sleep(5)
            
            # try:
            #     if not sb.is_element_enabled('subButton'):
            #         self.log(f"Try new driver")
            #         sb.get_new_driver(undetectable=True)
            #         sb.driver.get(url)
            #         sb.sleep(5)
            #
            #     if not sb.is_element_enabled('subButton'):
            #         self.log(f"Try to find iframe")
            #         if sb.is_element_visible('iframe[src*="challenge"]'):
            #             with sb.frame_switch('iframe[src*="challenge"]'):
            #                 sb.click("span.mark")
            #                 sb.sleep(2)
            # except Exception:
            #     self.ctx.send(f'Error: No link found')
            #     sb.driver.save_screenshot('screen.png')
            #     return None
            #
            # sb.activate_demo_mode()
            
            self.log(f"Clic on subButton")
            element = sb.find_element(By.ID, "subButton")
            sb.execute_script("arguments[0].click();", element)
            
            self.log("Try to find link")
            link = sb.find_element(By.XPATH, XPATH_LINK)
            if link:
                href = link.get_attribute('href')
                self.log(f"Find link {href}")
                sb.driver.close()
                return href
            else:
                sb.driver.close()
                self.log(f"Error no link found")
    
    def download_all_series(self, url):
        """
        Download all episodes of a series from wawacity
        :param url:
        :return:
        """
        driver = Driver(uc=True, headless=True)
        driver.get(url)
        self.log(f"Get {url}")
        
        try:
            wait = WebDriverWait(driver, 10)
            wait.until(presence_of_element_located((By.ID, "main-body")))
        except Exception:
            self.ctx.send(f'Error: No link found')
            driver.save_screenshot('screen.png')
            return []
        
        page_source = driver.page_source
        
        soup = BeautifulSoup(page_source, 'html.parser')
        
        title = soup.find('h1').text.strip().split('»')[1]
        
        self.show_ctx(f"Vous voulez télécharger: {title}")
        
        table = soup.find('table', id="DDLLinks")
        trs = table.find_all('tr', class_='link-row')
        
        urls = []
        
        for tr in trs:
            if tr.find_all('td')[1].text == SELECT_PROVIDER:
                provider_link = tr.find_all('td')[0].find('a').get('href')
                dl_protect_link = self.dl_protect(provider_link)

                if dl_protect_link:
                    urls.append(dl_protect_link)
        return urls


if __name__ == '__main__':
    parser = Parser(show_logs=True)
    
    all_series_urls = parser.download_all_series("https://www.wawacity.fit/?p=serie&id=12739-sex-education-saison4")
    if len(all_series_urls) == 0:
        print("No link found")
    else:
        # list all links into file name result.txt
        with open("result.txt", "w") as f:
            f.write("\n".join(all_series_urls))
        