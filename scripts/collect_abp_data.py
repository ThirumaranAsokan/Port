import requests
from bs4 import BeautifulSoup
import pandas as pd
from supabase import create_client, Client
import os
from datetime import datetime

# --- Supabase Setup ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

ABP_VESSELS_ALONGSIDE_URL = "https://www.southamptonvts.co.uk/Live_Information/Shipping_Movements_and_Cruise_Ship_Schedule/Vessels_Alongside/"

def fetch_vessels_alongside_data():
    """Fetches and parses the 'Vessels Alongside' data from the ABP Southampton website."""
    try:
        response = requests.get(ABP_VESSELS_ALONGSIDE_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the main table containing the vessel data
        table = soup.find('table')
        if not table:
            print("Error: Could not find the vessel data table.")
            return []

        # Extract all rows from the table (skipping the header row)
        rows = table.find_all('tr')[1:]
        vessels_data = []

        for row in rows:
            columns = row.find_all('td')
            if len(columns) >= 12:  # Ensure we have enough columns
                ship_name = columns[0].text.strip()
                arrival_time_str = columns[3].text.strip()
                berth = columns[5].text.strip()

                # Attempt to parse the arrival time string into a datetime object
                try:
                    # The date and time are on separate lines, let's combine them
                    arrival_parts = arrival_time_str.split('\n')
                    if len(arrival_parts) == 2:
                        date_str = arrival_parts[0].strip()
                        time_str = arrival_parts[1].strip()
                        arrival_datetime_str = f"{date_str} {time_str}"
                        # Assuming the year is the current year (you might need to adjust this)
                        current_year = datetime.now().year
                        eta = datetime.strptime(f"{arrival_datetime_str} {current_year}", '%d-%b %H:%M %Y').isoformat()
                    else:
                        eta = None
                        print(f"Warning: Could not parse arrival time for {ship_name}: {arrival_time_str}")
                except ValueError as e:
                    eta = None
                    print(f"Error parsing arrival time for {ship_name}: {e} - Original string: {arrival_time_str}")

                vessels_data.append({
                    "vessel_name": ship_name,
                    "eta": eta,
                    "berth": berth,
                    "status": "Alongside"
                })

        return vessels_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return []
    except Exception as e:
        print(f"Error parsing data: {e}")
        return []

def store_abp_data(data):
    """Stores the processed ABP data in the Supabase database."""
    if not data:
        print("No ABP data to store.")
        return

    for item in data:
        try:
            insert_data = {
                "vessel_name": item.get("vessel_name"),
                "eta": item.get("eta"),
                "berth": item.get("berth"),
                "status": item.get("status"),
            }
            data, count = supabase.table("abp_vessel_data").insert(insert_data).execute()
            if count > 0:
                print(f"Successfully inserted data for: {item.get('vessel_name')}")
            else:
                print(f"Failed to insert data for: {item.get('vessel_name')}")
        except Exception as e:
            print(f"Error inserting data for {item.get('vessel_name')}: {e}")

if __name__ == "__main__":
    abp_data = fetch_vessels_alongside_data()
    if abp_data:
        store_abp_data(abp_data)
