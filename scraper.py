import csv
import os
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup

class AmazonProductScraper:
    def __init__(self, headless):
        self.driver = self._init_driver(headless)
        self.base_url = 'https://www.amazon.in'

    def _init_driver(self, headless):
        options = Options()
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        options.add_argument('--log-level=OFF')
        options.add_argument('--disable-gpu')
        if headless:
           options.add_argument('--headless')
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    def get_product_urls(self, search_query, max_products=500):
        """Get the URLs of the products from the search results page."""
        product_urls = []
        search_url = f"{self.base_url}/s?k={search_query.replace(' ', '+')}"
        self.driver.get(search_url)

        while len(product_urls) < max_products:
            WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-main-slot.s-result-list.s-search-results.sg-row")))
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            results = soup.find_all('div', {'data-component-type': 's-search-result'})

            for result in results:
                if len(product_urls) >= max_products:
                    break
                if result.find('a', {'class': 'a-link-normal'}):
                    product_urls.append(self.base_url + result.find('a', {'class': 'a-link-normal'})['href'])

            # navigate to the next page
            next_page = self.driver.find_elements(By.CSS_SELECTOR, 'a.s-pagination-item.s-pagination-next')
            if next_page and len(product_urls) < max_products:
                next_page[0].click()
                time.sleep(random.uniform(1, 3)) 
            else:
                break

        return product_urls


    def scrape_product_page(self, url):
        """Scrape the product details from the product page."""
        product_data = {
            'product_name': 'N/A',
            'manufacturer_name': 'N/A',  
            'product_description': 'N/A',
            'product_details': 'N/A'
        }
        
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "productTitle"))) 
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # extract product name
            product_name_element = soup.find("span", {'id': 'productTitle'})
            if product_name_element:
                product_data['product_name'] = product_name_element.text.strip()
            
            # the manufacturer is part of the technical details section
            manufacturer_info = soup.find('table', {'id': 'productDetails_techSpec_section_1'})
            if manufacturer_info:
                for row in manufacturer_info.find_all('tr'):
                    header = row.find('th')
                    header_text = header.text.strip()
                    if header_text == 'Manufacturer': 
                        value_cell = row.find('td')
                        manufacturer = value_cell.text.strip() 
                        if value_cell:
                            product_data['manufacturer_name'] = manufacturer
                            break  # Break after finding manufacturer
            
            # product description
            product_description_elements = self.driver.find_elements(By.ID, 'productDescription')
            if product_description_elements:
                product_data['product_description'] = product_description_elements[0].text
            
            # product details
            product_details_div = soup.find('div', id='detailBulletsWrapper_feature_div')
            product_data['product_details'] = {li.find('span').get('class')[0]: ' '.join([span.text.stip() for span in li.find_all('span')]) for li in product_details_div.find_all('li')}
        except TimeoutException:
            print(f'Timeout Exception: Page took too long to load or element not found on {url}.')
        except NoSuchElementException:
            print(f'Element not found on {url}.')
        except Exception as e:
            print(f'An error occurred while scraping {url}: {e}')
        
        return product_data

    
    def scrape_products(self, search_query, max_products=500):
        """Scrape the products from the search results page."""
        product_urls = self.get_product_urls(search_query, max_products)
        products_data = []

        for url in product_urls:
            data = self.scrape_product_page(url)
            products_data.append(data)
            time.sleep(random.uniform(1, 3)) 

        self.driver.quit()
        return products_data

    def save_to_csv(self, products_data, filename='amazon_product.csv'):
        """Save the scraped data to a CSV file."""
        mode = 'a' if os.path.exists(filename) else 'w'
        with open(filename, mode, newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if file.tell() == 0:
                writer.writerow(['Product Name', 'Manufacturer', 'Product Details', 'Description'])
            for product in products_data:
                writer.writerow([product['product_name'], product['manufacturer_name'], product['product_details'], product['product_description']])

# Usage
if __name__ == "__main__":
    search_queries = ["Anime Figures"] # add more
    scraper = AmazonProductScraper(headless=True) 

    for query in search_queries:
        print(f"Starting scrape for: {query}")
        products_data = scraper.scrape_products(query, max_products=2)
        scraper.save_to_csv(products_data)
        print(f"Finished scrape for: {query}, total products scraped: {len(products_data)}")
        scraper.driver.delete_all_cookies()
        time.sleep(random.uniform(5, 10))  # delay between queries

        scraper.driver.refresh()

    scraper.driver.quit()
    print("Scraping session completed.")

    