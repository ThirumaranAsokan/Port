import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
from supabase import create_client, Client  # Import Supabase library
from selenium import webdriver
from selenium.webdriver.chrome.options import Options  # Or FirefoxOptions, etc.


def fetch_abp_data():
    URL = "https://www.southamptonvts.co.uk/Live-Information/Shipping-Movements/"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode (no GUI)
    chrome_options.add_argument("--disable-gpu")  # Optional: Disable GPU acceleration
    driver = webdriver.Chrome(options=chrome_options)  # Or webdriver.Firefox() etc.
    
    try:
        driver.get(URL)
        time.sleep(5)  # Wait for the JavaScript to load (adjust as needed)
        html = driver.page_source
    except Exception as e:
        print(f"Error fetching ABP data: {e}")
        driver.quit()
        return None
    
    driver.quit()  # Close the browser
    
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.xmlTable")  # You might need to adjust this selector based on the rendered HTML
    if not table:
        print("Could not find table in ABP page after JavaScript execution")
        return None
    
    # Get headers
    ths = table.find("tr").find_all("th")
    col_names = [th.get_text(strip=True) for th in ths]

    # Get rows
    data = []
    tbody = table.find("tbody")  # It's good practice to look within the tbody if it exists
    if tbody:
        rows = tbody.find_all("tr")[1:]  # Skip the header row
    else:
        rows = table.find_all("tr")[1:]  # If no tbody, start from the second tr

    for tr in rows:
        cols = tr.find_all("td")
        if cols and len(cols) == len(col_names):  # Ensure the number of columns matches headers
            row = [td.get_text(strip=True) for td in cols]
            data.append(row)
        elif cols:
            print(f"Warning: Row with {len(cols)} columns found, expected {len(col_names)}")

    # Create a DataFrame for better handling
    if data and col_names:
        df = pd.DataFrame(data, columns=col_names)
        return df
    else:
        print("No data extracted from the table.")
        return None


def push_to_supabase(df: pd.DataFrame):
    """Pushes the DataFrame to Supabase."""

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print("SUPABASE_URL or SUPABASE_KEY environment variables not set.")
        return

    supabase: Client = create_client(supabase_url, supabase_key)

    for _, row in df.iterrows():
        data = row.to_dict()
        try:
            # Instead of directly checking response.error, let's look for errors in the response data
            response = supabase.table("abp_vessel_data").insert(data).execute()
            if response.data:
                print(f"Inserted row: {data}")
            elif response.error:
                print(f"Error inserting row: {response.error}")
            else:
                print("No data or error received from Supabase")
        except Exception as e:
            print(f"Error connecting to Supabase: {e}")


def main():
    df = fetch_abp_data()
    if df is not None:
        print(df.head())
        push_to_supabase(df)  # Push data to Supabase
    else:
        print("No data fetched.")


if __name__ == "__main__":
    main()
