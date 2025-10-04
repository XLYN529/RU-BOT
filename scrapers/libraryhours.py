import requests
from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def load_existing_libraries(csv_file='rutgers_library_locations.csv'):
    """
    Load library names from the existing CSV file
    """
    libraries = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                libraries.append(row['name'].strip())
        return libraries
    except FileNotFoundError:
        print(f"CSV file {csv_file} not found")
        return []

def scrape_library_hours():
    """
    Scrape library hours from Rutgers Libraries website using Selenium
    Only for libraries that exist in our locations CSV
    """
    url = "https://www.libraries.rutgers.edu/visit-study/library-hours"
    
    # Load existing libraries from CSV
    existing_libraries = load_existing_libraries()
    if not existing_libraries:
        print("No existing libraries found in CSV file")
        return []
    
    print(f"Looking for hours for these libraries: {existing_libraries}")
    
    # Set up Chrome options for headless browsing
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = None
    try:
        # Initialize Chrome driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        # Wait for the page to load
        print("Waiting for page to load...")
        time.sleep(5)
        
        # Wait for the table to be present
        wait = WebDriverWait(driver, 10)
        
        # Look for the table with library hours
        try:
            # Try to find tbody first
            tbody = wait.until(EC.presence_of_element_located((By.TAG_NAME, "tbody")))
            print("Found tbody element")
        except:
            print("No tbody found, looking for table rows directly...")
            # If no tbody, look for tr elements directly
            rows = driver.find_elements(By.CSS_SELECTOR, "tr")
            if not rows:
                print("No table rows found")
                return []
        else:
            # Find all rows in the tbody
            rows = tbody.find_elements(By.TAG_NAME, "tr")
        
        print(f"Found {len(rows)} table rows")
        
        library_hours = []
        
        # Days of the week mapping (hrs-dt-0 = Sunday, hrs-dt-1 = Monday, etc.)
        days_of_week = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        
        for row in rows:
            try:
                # Get library name from the first cell with class 'hrs-loc'
                name_cell = row.find_element(By.CSS_SELECTOR, "td.hrs-loc")
                link = name_cell.find_element(By.TAG_NAME, "a")
                library_name = link.text.strip()
                
                # Check if this library is in our existing libraries list
                # Handle name variations (e.g., "Robert Wood Johnson (RWJ) Library" vs "Robert Wood Johnson (RWJ) Library - Health Sciences")
                library_found = False
                for existing_lib in existing_libraries:
                    # Check if the scraped name matches or is contained in existing name
                    if (library_name == existing_lib or 
                        library_name in existing_lib or 
                        existing_lib in library_name):
                        library_found = True
                        # Use the existing library name for consistency
                        library_name = existing_lib
                        break
                
                if not library_found:
                    continue
                
                print(f"Found hours for: {library_name}")
                
                # Get all hour cells (td elements with wysiwyg class)
                # Look for both visible and hidden cells
                hour_cells = row.find_elements(By.CSS_SELECTOR, "td.wysiwyg")
                
                # Extract hours for each day
                library_data = {
                    'library_name': library_name,
                    'hours': {}
                }
                
                # Map hours to days (hrs-dt-0 through hrs-dt-6 represent Sunday through Saturday)
                for i, cell in enumerate(hour_cells):
                    if i < len(days_of_week):
                        day = days_of_week[i]
                        hours_text = cell.text.strip()
                        library_data['hours'][day] = hours_text
                
                # Also try to get the specific day cells by their class names
                # Use JavaScript to get the text content of hidden elements
                for i in range(7):  # 0-6 for Sunday-Saturday
                    try:
                        day_cell = row.find_element(By.CSS_SELECTOR, f"td.hrs-dt-{i}")
                        day = days_of_week[i]
                        # Use JavaScript to get text content even if element is hidden
                        hours_text = driver.execute_script("return arguments[0].textContent;", day_cell).strip()
                        if hours_text:  # Only update if we found text
                            library_data['hours'][day] = hours_text
                    except:
                        continue
                
                library_hours.append(library_data)
                
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        
        return library_hours
        
    except Exception as e:
        print(f"Error with Selenium: {e}")
        return []
    finally:
        if driver:
            driver.quit()

def export_hours_to_csv(library_hours, filename='rutgers_library_hours.csv'):
    """
    Export library hours to CSV file
    """
    if not library_hours:
        print("No library hours data to export")
        return
    
    # Create fieldnames for CSV
    fieldnames = ['library_name', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for library in library_hours:
            row = {'library_name': library['library_name']}
            row.update(library['hours'])
            writer.writerow(row)
    
    print(f"Library hours exported to {filename}")
    print(f"Total libraries with hours: {len(library_hours)}")

def main():
    """
    Main function to scrape and export library hours
    """
    print("Scraping Rutgers Library hours...")
    library_hours = scrape_library_hours()
    
    if library_hours:
        print(f"Found hours for {len(library_hours)} libraries:")
        for lib in library_hours:
            print(f"- {lib['library_name']}")
        
        # Export to CSV
        export_hours_to_csv(library_hours)
    else:
        print("No library hours found")

if __name__ == "__main__":
    main()