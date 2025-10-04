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


# Rutgers dining locations with their location numbers
# These locations share the same menu portal structure
DINING_LOCATIONS_GROUP1 = {
    'Neilson Dining Hall': '05',
    'Livingston Dining Commons': '02',
    'The Atrium @ SEBS': '04',
}

# Busch and Brower use a different page structure (handle separately)
# 'Busch Dining Hall': '01',
# 'Brower Commons': '03',

MEAL_PERIODS = ['Breakfast', 'Lunch', 'Dinner', 'Late Knight']


def setup_driver():
    """Initialize and configure the Selenium WebDriver"""
    options = webdriver.ChromeOptions()
    # Run in headless mode for better performance
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    # Use webdriver-manager to automatically handle ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def get_week_dates():
    """Get list of dates for the next 7 days"""
    dates = []
    today = datetime.now()
    
    for i in range(7):
        date = today + timedelta(days=i)
        dates.append(date)
    
    return dates


def build_menu_url(location_name, location_num, date):
    """Build the menu URL for a specific location and date"""
    date_str = date.strftime('%-m/%-d/%Y')
    base_url = "https://menuportal23.dining.rutgers.edu/FoodPronet/pickmenu.aspx"
    
    params = {
        'sName': 'Rutgers University Dining',
        'dtdate': date_str,
        'locationNum': location_num,
        'locationName': location_name,
        'mealName': '',
        'naFlag': '1'
    }
    
    # Build URL manually to match the format
    url = f"{base_url}?sName={params['sName']}&dtdate={params['dtdate']}&locationNum={params['locationNum']}&locationName={params['locationName']}&mealName=&naFlag=1"
    url = url.replace(' ', '+')
    
    return url


def scrape_meal_menu(driver, meal_period, location_name, date):
    """Scrape menu items for a specific meal period"""
    menu_items = []
    
    try:
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Check if this is the active meal already (first meal on page load)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        active_tab = soup.find('div', class_='tab active')
        current_meal = active_tab.get_text(strip=True) if active_tab else None
        
        # If not the active meal, click the tab link
        if current_meal != meal_period:
            try:
                # Find the tab link with the meal name
                meal_link_xpath = f"//div[@class='tab']//a[contains(text(), '{meal_period}')]"
                meal_button = driver.find_element(By.XPATH, meal_link_xpath)
                driver.execute_script("arguments[0].scrollIntoView(true);", meal_button)
                time.sleep(0.5)
                meal_button.click()
                time.sleep(3)  # Wait for content to load
                
                # Re-parse the page after click
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
            except (NoSuchElementException, TimeoutException):
                print(f"  ! Could not find {meal_period} tab")
                return menu_items
        
        # Parse menu items using the Rutgers dining menu structure
        # Categories are in <h3> tags
        # Items are in <label> tags within fieldsets in col-1 divs
        
        current_category = 'General'
        
        # Find the menu box container
        menu_box = soup.find('div', class_='menuBox')
        
        if menu_box:
            # Iterate through all children to maintain order
            for element in menu_box.find_all(['h3', 'fieldset']):
                if element.name == 'h3':
                    # This is a category header
                    category_text = element.get_text(strip=True)
                    # Clean up category text (remove -- markers)
                    category_text = category_text.replace('--', '').strip()
                    if category_text:
                        current_category = category_text
                
                elif element.name == 'fieldset':
                    # This is a menu item
                    # Find the label in col-1
                    col1 = element.find('div', class_='col-1')
                    if col1:
                        label = col1.find('label')
                        if label:
                            item_name = label.get_text(strip=True)
                            if item_name and len(item_name) > 0:
                                menu_items.append({
                                    'location': location_name,
                                    'date': date.strftime('%Y-%m-%d'),
                                    'day_of_week': date.strftime('%A'),
                                    'meal_period': meal_period,
                                    'category': current_category,
                                    'item': item_name
                                })
        
    except Exception as e:
        print(f"  ! Error scraping {meal_period} at {location_name}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return menu_items


def scrape_dining_hall_menu(driver, location_name, location_num, date):
    """Scrape all meal periods for a specific dining hall and date"""
    print(f"\n  → {location_name} - {date.strftime('%A, %B %d, %Y')}")
    
    all_menu_items = []
    url = build_menu_url(location_name, location_num, date)
    
    try:
        driver.get(url)
        time.sleep(3)  # Wait for initial page load
        
        # Determine which meals to scrape based on day of week
        meals_to_scrape = MEAL_PERIODS.copy()
        
        # Late Knight is typically only on weekdays (Monday-Friday)
        if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            if 'Late Knight' in meals_to_scrape:
                meals_to_scrape.remove('Late Knight')
        
        # Scrape each meal period
        for meal_period in meals_to_scrape:
            print(f"    • Scraping {meal_period}...", end=' ')
            
            # Go back to the main URL before each meal to reset state
            if meal_period != meals_to_scrape[0]:
                driver.get(url)
                time.sleep(2)
            
            meal_items = scrape_meal_menu(driver, meal_period, location_name, date)
            
            if meal_items:
                all_menu_items.extend(meal_items)
                print(f"✓ Found {len(meal_items)} items")
            else:
                print("✗ No items found")
        
    except Exception as e:
        print(f"  ! Error accessing {location_name}: {str(e)}")
    
    return all_menu_items


def fetch_all_menus():
    """Main function to scrape menus from all dining locations for the next week"""
    print("="*80)
    print("RUTGERS DINING HALL MENU SCRAPER (GROUP 1)")
    print("Locations: Neilson, Livingston, The Atrium @ SEBS")
    print("="*80)
    
    all_data = []
    dates = get_week_dates()
    
    print(f"\nScraping menus for {len(dates)} days ({dates[0].strftime('%m/%d')} - {dates[-1].strftime('%m/%d/%Y')})")
    print(f"Locations: {len(DINING_LOCATIONS_GROUP1)}")
    
    driver = setup_driver()
    
    try:
        for date in dates:
            print(f"\n{'─'*80}")
            print(f"DATE: {date.strftime('%A, %B %d, %Y')}")
            print(f"{'─'*80}")
            
            for location_name, location_num in DINING_LOCATIONS_GROUP1.items():
                menu_data = scrape_dining_hall_menu(driver, location_name, location_num, date)
                all_data.extend(menu_data)
                time.sleep(1)  # Be polite to the server
        
    finally:
        driver.quit()
    
    print(f"\n{'='*80}")
    print(f"SCRAPING COMPLETE")
    print(f"{'='*80}")
    print(f"Total menu items collected: {len(all_data)}")
    
    return all_data


def save_to_csv(menu_data, filename='../exported_csvs/dining_menus.csv'):
    """Save menu data to CSV file"""
    
    if not menu_data:
        print("\n! No menu data to save!")
        return
    
    print(f"\n{'='*80}")
    print("SAVING TO CSV")
    print(f"{'='*80}\n")
    
    # Ensure the directory exists
    import os
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['location', 'date', 'day_of_week', 'meal_period', 'category', 'item']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in menu_data:
            writer.writerow(row)
    
    print(f"✓ Successfully saved {len(menu_data)} menu items to {filename}")
    
    # Print summary statistics
    print(f"\nSummary:")
    print(f"  - Total items: {len(menu_data)}")
    
    locations = set(row['location'] for row in menu_data)
    print(f"  - Dining halls: {len(locations)}")
    for location in sorted(locations):
        count = sum(1 for row in menu_data if row['location'] == location)
        print(f"    • {location}: {count} items")
    
    dates = set(row['date'] for row in menu_data)
    print(f"  - Dates covered: {len(dates)}")
    
    meals = set(row['meal_period'] for row in menu_data)
    print(f"  - Meal periods: {', '.join(sorted(meals))}")


if __name__ == "__main__":
    print("\n🍽️  Starting Rutgers Dining Menu Scraper (Group 1)...\n")
    
    menu_data = fetch_all_menus()
    
    if menu_data:
        save_to_csv(menu_data, filename='../exported_csvs/dining_menus_group1.csv')
    
    print("\n✨ All done! Check the CSV file for results.\n")
