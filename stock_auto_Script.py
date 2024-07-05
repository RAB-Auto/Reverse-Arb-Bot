

from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time 
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime





# func to check if a split ratio represents a reverse split
def is_reverse_split(ratio):
    parts = ratio.split(':')
    return int(parts[0]) > int(parts[1])

# func to check if the date is in the future the future launch
def is_future_date(date_str):
    split_date = datetime.strptime(date_str, '%Y-%m-%d')
    return split_date > datetime.now()
def hegdgeFollowStocks(driver,current_date):
    html_content = driver.page_source  
    soup = BeautifulSoup(html_content, 'html.parser')

    table = soup.find('table', id='latest_splits')
    rows = table.find('tbody').find_all('tr')

    data = []

    for row in rows:
        try:
            stock = row.find_all('td')[0].get_text(strip=True)
            exchange = row.find_all('td')[1].get_text(strip=True)
            company_name = row.find_all('td')[2].get_text(strip=True)
            split_ratio = row.find_all('td')[3].get_text(strip=True)
            ex_date = row.find_all('td')[4].get_text(strip=True)
            ann_date = row.find_all('td')[5].get_text(strip=True)
            
            # Filter based on criteria
            if exchange == 'NASDAQ' and is_reverse_split(split_ratio) and is_future_date(ex_date):
                row_dict = {
                        'stock': stock,
                    'exchange': exchange,
                    'company_name': company_name,
                    'split_ratio': split_ratio,
                    'ex_date': ex_date,
                    'ann_date': ann_date
                }
                data.append(row_dict)
        except Exception as e:continue

    # dataframe
    df = pd.DataFrame(data)

    # df to csv
    output_file = f'upcoming_reverse_splits{current_date}.csv'
    df.to_csv(output_file, index=False)
    return df





def Validate_Stock(driver,stock_name):
    driver.get('https://www.stocktitan.net/')

    try:
        search_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "bi.bi-search"))
        )
        #search_btn[0].click()
    except Exception as e:
        print(f"An error occurred: {e}")
    time.sleep(5)

    try:
        search = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/header/div/div[3]/form/div/div/input"))
        )
        search.click()

    except Exception as e:
        print(f"An error occurred: {e}")
    search.send_keys(stock_name)
    search_btn[2].click()
    try:
        blog = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "symbol-link"))
        )
        blog.click()

    except Exception as e:
        print(f"An error occurred: {e}")
    page_text = driver.find_element(By.TAG_NAME, 'body').text
    keywords = ['round', 'rounding', 'cash in lieu', 'rounding up', 'additional shares']

    if any(keyword in page_text for keyword in keywords):
        return True
    else:return False



if __name__=="__main__":
    #driver create 
    driver=Driver(headed=True)
    driver.get("https://hedgefollow.com/upcoming-stock-splits.php")
    current_date = datetime.now().strftime('%d%b').lower()
    # getting the stock dataframe
    df=hegdgeFollowStocks(driver,current_date)
    
    print(f'Successfully Got the stocks from Hedgefollow site now validating...')
    valid_stock=[]
    # iterate over the stocks and use stock symbol to validate from the site
    for i,row_stock in df.iterrows():
        if Validate_Stock(driver,row_stock['stock']):
            valid_stock.append(row_stock)
    if valid_stock:
        print(f'Validated Generated csv')
    
    valid_stock_df=pd.DataFrame(valid_stock)
    valid_stock_df.to_csv(f'valid_stock{current_date}.csv',index=False)
    driver.quit()






