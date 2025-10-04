"""
Busch Dining Hall Menu Scraper
Scrapes 2 days of menus using Selenium (nutrislice.com has dynamic JavaScript content)
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


LOCATION_NAME = 'Busch Dining Hall'
BASE_URL = 'https://rutgers.nutrislice.com/menu/busch-dining-hall'
MEAL_PERIODS = ['Breakfast', 'Lunch', 'Dinner']  # Late Knight if weekday


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


def click_view_menus(driver):
    """Click the 'View Menus' button on splash screen"""
    try:
        view_menus_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'View Menus')]"))
        )
        view_menus_btn.click()
        time.sleep(5)  # Wait for menu page to load
        return True
    except:
        return False


def scrape_meal_menu(driver, meal_period, date):
    """Scrape menu items for a specific meal period"""
    menu_items = []
    
    try:
        # Click on the meal period
        meal_link = driver.find_element(By.XPATH, f"//a[contains(@class, 'menu-item')]//strong[contains(text(), '{meal_period}')]")
        meal_link.click()
        time.sleep(5)  # Wait for meal menu to load
        
        # Parse the page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find all categories (h3 tags)
        categories = soup.find_all('h3')
        
        for category_elem in categories:
            category_name = category_elem.get_text(strip=True)
            
            # Skip if empty
            if not category_name:
                continue
            
            # Try to expand this category by clicking it
            try:
                category_link = driver.find_element(By.XPATH, f"//h3//a[contains(text(), '{category_name}')]")
                driver.execute_script("arguments[0].scrollIntoView(true);", category_link)
                time.sleep(0.5)
                category_link.click()
                time.sleep(5)  # Wait for category to expand and items to load
                
                # Re-parse after expansion
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Find food items within this category
                # Look for elements that contain food names (usually in specific divs/spans)
                # The exact selector may need adjustment based on actual HTML structure
                food_elements = soup.find_all('div', class_=lambda x: x and 'food' in str(x).lower())
                
                # If that doesn't work, try finding all text elements and filter
                if not food_elements:
                    # Get all elements after the category header
                    # This is a fallback - we'll extract any reasonable looking food items
                    pass
                
            except Exception as e:
                # Category might already be expanded or not clickable
                pass
        
        # After expanding all categories, parse all visible food items
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Try to find food items - this needs to be adjusted based on actual HTML
        # For now, look for common patterns
        current_category = 'General'
        
        # Find all h3 (categories) and process content after each
        all_h3 = soup.find_all('h3')
        
        for h3 in all_h3:
            category_name = h3.get_text(strip=True)
            if category_name:
                current_category = category_name
                
                # Find the parent container and look for food items
                parent = h3.find_parent(['div', 'section'])
                if parent:
                    # Look for any text that might be food items
                    # This is a simplified approach - may need refinement
                    food_names = parent.find_all('span', class_=lambda x: x and 'name' in str(x).lower())
                    
                    for food_span in food_names:
                        item_name = food_span.get_text(strip=True)
                        if item_name and len(item_name) > 2:
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
    """Main function to scrape menus for Busch Dining Hall"""
    print("="*80)
    print(f"BUSCH DINING HALL MENU SCRAPER (Selenium)")
    print("="*80)
    
    all_data = []
    dates = get_dates(2)
    
    print(f"\nScraping {len(dates)} days: {dates[0].strftime('%m/%d')} - {dates[-1].strftime('%m/%d/%Y')}")
    
    driver = setup_driver()
    
    try:
        # Load the page
        print(f"\nLoading {BASE_URL}...")
        driver.get(BASE_URL)
        time.sleep(3)
        
        # Click View Menus button
        print("Clicking 'View Menus' button...")
        if not click_view_menus(driver):
            print("! Failed to click View Menus button")
            return all_data
        
        print("✓ Menu page loaded")
        
        # For each date (Nutrislice shows current week by default)
        # Note: We'll scrape today and tomorrow which should be visible
        for i, date in enumerate(dates):
            print(f"\n{'─'*80}")
            print(f"DATE: {date.strftime('%A, %B %d, %Y')}")
            print(f"{'─'*80}")
            
            # Click on the date if it's not the first one
            if i > 0:
                try:
                    # Try to find and click the next date
                    # The date selector format may vary
                    date_str = date.strftime('%a, %b %-d, %Y')
                    date_link = driver.find_element(By.XPATH, f"//li[contains(text(), '{date.strftime('%b %-d')}')]")
                    date_link.click()
                    time.sleep(5)
                except:
                    print(f"  ! Could not select date {date_str}, using current view")
            
            # Scrape each meal period
            meals_to_scrape = MEAL_PERIODS.copy()
            if date.weekday() >= 5:  # Weekend
                pass  # Nutrislice shows different meals on weekends
            
            for meal_period in meals_to_scrape:
                print(f"  • Scraping {meal_period}...", end=' ')
                
                meal_items = scrape_meal_menu(driver, meal_period, date)
                
                if meal_items:
                    all_data.extend(meal_items)
                    print(f"✓ Found {len(meal_items)} items")
                else:
                    print("✗ No items found")
                
                # Go back to menu list for next meal
                try:
                    driver.get(BASE_URL)
                    time.sleep(3)
                    click_view_menus(driver)
                except:
                    pass
        
    finally:
        driver.quit()
    
    print(f"\n{'='*80}")
    print(f"SCRAPING COMPLETE")
    print(f"{'='*80}")
    print(f"Total menu items collected: {len(all_data)}")
    
    return all_data


def save_to_csv(menu_data, filename='exported_csvs/busch_menus.csv'):
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
    print("\n🍽️  Starting Busch Dining Hall Menu Scraper...\n")
    
    menu_data = scrape_all_menus()
    
    if menu_data:
        save_to_csv(menu_data)
    
    print("\n✨ All done! Check the CSV file for results.\n")
