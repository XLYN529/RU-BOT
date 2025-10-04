"""
Test script to inspect Busch Dining Hall page structure (nutrislice.com)
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


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


def inspect_page():
    """Inspect the Busch Dining Hall page structure"""
    print("="*80)
    print("INSPECTING BUSCH DINING HALL PAGE (nutrislice.com)")
    print("="*80)
    
    url = "https://rutgers.nutrislice.com/menu/busch-dining-hall"
    
    driver = setup_driver()
    
    try:
        print(f"\nLoading: {url}")
        driver.get(url)
        
        # Wait for the splash screen to load
        print("Waiting for page to load...")
        time.sleep(3)
        
        # Click the "View Menus" button on the splash screen
        try:
            view_menus_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'View Menus')]"))
            )
            print("✓ Found 'View Menus' button, clicking...")
            view_menus_btn.click()
            time.sleep(5)  # Wait for menu content to load after clicking
            print("✓ Menu page loaded")
        except Exception as e:
            print(f"! Could not click 'View Menus' button: {str(e)}")
        
        print(f"Page title: {driver.title}\n")
        
        # Click on "Breakfast" to see menu structure
        print("Clicking on Breakfast menu...")
        try:
            breakfast_link = driver.find_element(By.XPATH, "//a[contains(@class, 'menu-item')]//strong[contains(text(), 'Breakfast')]")
            breakfast_link.click()
            time.sleep(5)
            print("✓ Breakfast menu loaded")
        except Exception as e:
            print(f"! Could not click Breakfast: {str(e)}")
        
        # Try to expand a category to see items
        print("Expanding 'BAGEL NUTRITION' category...")
        try:
            category = driver.find_element(By.XPATH, "//h3//a[contains(text(), 'BAGEL NUTRITION')]")
            category.click()
            time.sleep(3)
            print("✓ Category expanded")
        except Exception as e:
            print(f"! Could not expand category: {str(e)}")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        print("\n" + "="*80)
        print("LOOKING FOR MENU ITEMS AND CATEGORIES")
        print("="*80)
        
        # Look for h3, h4 tags (likely categories)
        for tag in ['h3', 'h4', 'h5']:
            headings = soup.find_all(tag)
            if headings:
                print(f"\n{tag.upper()} tags ({len(headings)}):")
                for h in headings[:20]:
                    text = h.get_text(strip=True)
                    if text:
                        print(f"  - {text}")
        
        # Look for food items - try to find elements with food names
        print("\n" + "="*80)
        print("LOOKING FOR ACTUAL FOOD ITEMS")
        print("="*80)
        
        # Try different selectors for food items
        food_items = soup.find_all('div', class_=lambda x: x and 'food' in str(x).lower())
        print(f"\nFound {len(food_items)} elements with 'food' in class")
        
        # Look for li elements that might contain food items
        list_items = soup.find_all('li')
        print(f"Found {len(list_items)} list items total")
        
        # Print first few list items to see structure
        for i, li in enumerate(list_items[:10]):
            text = li.get_text(strip=True)
            if text and len(text) < 200:
                print(f"  {i+1}. {text[:100]}")
        
        print("\n" + "="*80)
        print("LOOKING FOR MENU CONTENT STRUCTURE")
        print("="*80)
        
        # Look for common menu container classes
        divs_with_class = soup.find_all('div', class_=True)
        unique_classes = set()
        for div in divs_with_class:
            classes = div.get('class', [])
            for cls in classes:
                if any(word in cls.lower() for word in ['menu', 'item', 'food', 'dish', 'meal', 'category']):
                    unique_classes.add(cls)
        
        print(f"\nPotential menu-related classes found:")
        for cls in sorted(unique_classes)[:20]:
            print(f"  - {cls}")
        
        # Look for headings that might be categories
        print("\n" + "="*80)
        print("LOOKING FOR CATEGORY HEADINGS")
        print("="*80)
        
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5']:
            headings = soup.find_all(tag)
            if headings:
                print(f"\n{tag.upper()} tags ({len(headings)}):")
                for h in headings[:10]:
                    text = h.get_text(strip=True)
                    if text and len(text) < 100:
                        print(f"  - {text}")
        
        # Save HTML for inspection
        with open('debug_busch_page.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("\n✓ Saved page HTML to 'debug_busch_page.html' for inspection")
        
        # Try to find specific nutrislice elements
        print("\n" + "="*80)
        print("NUTRISLICE-SPECIFIC ELEMENTS")
        print("="*80)
        
        # Look for data attributes
        elements_with_data = soup.find_all(attrs={'data-menu-item-id': True})
        print(f"\nElements with data-menu-item-id: {len(elements_with_data)}")
        
        elements_with_data2 = soup.find_all(attrs={'data-cy': True})
        print(f"Elements with data-cy: {len(elements_with_data2)}")
        if elements_with_data2:
            for elem in elements_with_data2[:10]:
                print(f"  - data-cy=\"{elem.get('data-cy')}\"")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()
        print("\n" + "="*80)
        print("INSPECTION COMPLETE")
        print("="*80)


if __name__ == "__main__":
    inspect_page()
