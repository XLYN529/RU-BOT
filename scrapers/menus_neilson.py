"""
Neilson Dining Hall Menu Scraper
Scrapes 2 days of menus for all meal periods
"""
import time
import csv
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


LOCATION_NAME = 'Neilson Dining Hall'
LOCATION_NUM = '05'
BASE_URL = 'https://menuportal23.dining.rutgers.edu/FoodPronet/pickmenu.aspx'
MEAL_PERIODS = ['Breakfast', 'Lunch', 'Dinner', 'Late Knight']


def setup_driver():
    """Initialize and configure the Selenium WebDriver"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def get_dates(num_days=2):
    """Get list of dates starting from today"""
    dates = []
    today = datetime.now()
    
    for i in range(num_days):
        date = today + timedelta(days=i)
        dates.append(date)
    
    return dates


def build_menu_url(date):
    """Build the menu URL for a specific date"""
    date_str = date.strftime('%-m/%-d/%Y')
    url = f"{BASE_URL}?sName=Rutgers+University+Dining&locationNum={LOCATION_NUM}&locationName={LOCATION_NAME.replace(' ', '+')}&naFlag=1"
    return url


def scrape_meal_menu(driver, meal_period, date):
    """Scrape menu items for a specific meal period"""
    menu_items = []
    
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        active_tab = soup.find('div', class_='tab active')
        current_meal = active_tab.get_text(strip=True) if active_tab else None
        
        if current_meal != meal_period:
            try:
                meal_link_xpath = f"//div[@class='tab']//a[contains(text(), '{meal_period}')]"
                meal_button = driver.find_element(By.XPATH, meal_link_xpath)
                driver.execute_script("arguments[0].scrollIntoView(true);", meal_button)
                time.sleep(0.5)
                meal_button.click()
                time.sleep(3)
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
            except (NoSuchElementException, TimeoutException):
                print(f"  ! Could not find {meal_period} tab")
                return menu_items
        
        current_category = 'General'
        menu_box = soup.find('div', class_='menuBox')
        
        if menu_box:
            for element in menu_box.find_all(['h3', 'fieldset']):
                if element.name == 'h3':
                    category_text = element.get_text(strip=True)
                    category_text = category_text.replace('--', '').strip()
                    if category_text:
                        current_category = category_text
                
                elif element.name == 'fieldset':
                    col1 = element.find('div', class_='col-1')
                    if col1:
                        label = col1.find('label')
                        if label:
                            item_name = label.get_text(strip=True)
                            if item_name and len(item_name) > 0:
                                menu_items.append({
                                    'location': LOCATION_NAME,
                                    'date': date.strftime('%Y-%m-%d'),
                                    'day_of_week': date.strftime('%A'),
                                    'meal_period': meal_period,
                                    'category': current_category,
                                    'item': item_name
                                })
        
    except Exception as e:
        print(f"  ! Error scraping {meal_period}: {str(e)}")
    
    return menu_items


def scrape_all_menus():
    """Main function to scrape menus for Neilson Dining Hall"""
    print("="*80)
    print(f"NEILSON DINING HALL MENU SCRAPER")
    print("="*80)
    
    all_data = []
    dates = get_dates(2)
    
    print(f"\nScraping {len(dates)} days: {dates[0].strftime('%m/%d')} - {dates[-1].strftime('%m/%d/%Y')}")
    
    driver = setup_driver()
    
    try:
        for date in dates:
            print(f"\n{'─'*80}")
            print(f"DATE: {date.strftime('%A, %B %d, %Y')}")
            print(f"{'─'*80}")
            
            url = build_menu_url(date)
            driver.get(url)
            time.sleep(3)
            
            # Determine which meals to scrape based on day of week
            meals_to_scrape = MEAL_PERIODS.copy()
            if date.weekday() >= 5:  # Weekend - no Late Knight
                if 'Late Knight' in meals_to_scrape:
                    meals_to_scrape.remove('Late Knight')
            
            for meal_period in meals_to_scrape:
                print(f"  • Scraping {meal_period}...", end=' ')
                
                if meal_period != meals_to_scrape[0]:
                    driver.get(url)
                    time.sleep(2)
                
                meal_items = scrape_meal_menu(driver, meal_period, date)
                
                if meal_items:
                    all_data.extend(meal_items)
                    print(f"✓ Found {len(meal_items)} items")
                else:
                    print("✗ No items found")
        
    finally:
        driver.quit()
    
    print(f"\n{'='*80}")
    print(f"SCRAPING COMPLETE")
    print(f"{'='*80}")
    print(f"Total menu items collected: {len(all_data)}")
    
    return all_data


def save_to_csv(menu_data, filename='exported_csvs/neilson_menus.csv'):
    """Save menu data to CSV file"""
    
    if not menu_data:
        print("\n! No menu data to save!")
        return
    
    print(f"\n{'='*80}")
    print("SAVING TO CSV")
    print(f"{'='*80}\n")
    
    import os
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['location', 'date', 'day_of_week', 'meal_period', 'category', 'item']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in menu_data:
            writer.writerow(row)
    
    print(f"✓ Successfully saved {len(menu_data)} menu items to {filename}")
    
    dates = set(row['date'] for row in menu_data)
    print(f"\nSummary:")
    print(f"  - Total items: {len(menu_data)}")
    print(f"  - Dates covered: {len(dates)}")
    
    meals = set(row['meal_period'] for row in menu_data)
    print(f"  - Meal periods: {', '.join(sorted(meals))}")


if __name__ == "__main__":
    print("\n🍽️  Starting Neilson Dining Hall Menu Scraper...\n")
    
    menu_data = scrape_all_menus()
    
    if menu_data:
        save_to_csv(menu_data)
    
    print("\n✨ All done! Check the CSV file for results.\n")
