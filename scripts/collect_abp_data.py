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

ABP_BASE_URL = "https://www.southamptonvts.co.uk/Live_Information/Shipping_Movements_and_Cruise_Ship_Schedule/"
ABP_VESSELS_ALONGSIDE_URL = ABP_BASE_URL + "Vessels_Alongside/"
ABP_PLANNED_MOVEMENTS_URL = ABP_BASE_URL + "Planned_Movements/"
ABP_VESSELS_UNDERWAY_URL = ABP_BASE_URL + "Vessels_Underway/"
ABP_SHIPS_AT_ANCHOR_URL = ABP_BASE_URL + "Ships_at_Anchor/"

def fetch_and_parse_table_data(url, status, arrival_time_column_index=None, berth_column_index=None):
    """Fetches and parses table data from a given ABP URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        table = soup.find('table', class_='xmlTable')
        if not table or not table.find('tbody'):
            table = soup.find('table')
            if not table or not table.find('tbody'):
                print(f"Error: Could not find the main vessel data table with a tbody on {url}")
                return []

        tbody = table.find('tbody')
        rows = tbody.find_all('tr')[1:]  # Skip the header row

        vessels_data = []

        for row in rows:
            columns = row.find_all('td')
            if columns:
                ship_name = columns[0].text.strip()
                arrival_time_str = columns[arrival_time_column_index].text.strip() if arrival_time_column_index is not None and len(columns) > arrival_time_column_index else None
                berth = columns[berth_column_index].text.strip() if berth_column_index is not None and len(columns) > berth_column_index else None

                eta = None
                if arrival_time_str:
                    try:
                        arrival_parts = arrival_time_str.split('\n')
                        if len(arrival_parts) == 2:
                            date_str = arrival_parts[0].strip()
                            time_str = arrival_parts[1].strip()
                            arrival_datetime_str = f"{date_str} {time_str}"
                            current_year = datetime.now(tz=datetime.timezone.utc).year
                            try:
                                eta = datetime.strptime(f"{arrival_datetime_str} {current_year}", '%d-%b %H:%M %Y').isoformat()
                            except ValueError:
                                try:
                                    eta = datetime.strptime(f"{date_str} {time_str} {current_year}", '%d %b %H:%M %Y').isoformat()
                                except ValueError:
                                    print(f"Warning: Could not parse arrival time for {ship_name} on {url}: {arrival_time_str}")
                        else:
                            print(f"Warning: Unexpected arrival time format for {ship_name} on {url}: {arrival_time_str}")
                    except ValueError as e:
                        print(f"Error parsing arrival time for {ship_name} on {url}: {e} - Original string: {arrival_time_str}")

                vessels_data.append({
                    "vessel_name": ship_name,
                    "eta": eta,
                    "berth": berth,
                    "status": status
                })

        return vessels_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from {url}: {e}")
        return []
    except Exception as e:
        print(f"Error parsing data from {url}: {e}")
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
                "created_at": datetime.now(tz=datetime.timezone.utc).isoformat() # Add timestamp
            }
            response = supabase.table("abp_vessel_data").insert(insert_data).execute()
            if response.error:
                print(f"Error inserting data for {item.get('vessel_name')}: {response.error}")
            elif response.count > 0:
                print(f"Successfully inserted data for: {item.get('vessel_name')}")
            else:
                print(f"Failed to insert data for: {item.get('vessel_name')}")
        except Exception as e:
            print(f"Error during Supabase insertion for {item.get('vessel_name')}: {e}")

def clear_existing_abp_data():
    """Clears existing ABP data from the table before adding new data."""
    try:
        response = supabase.table("abp_vessel_data").delete().neq("id", 0).execute() # Delete where id is not equal to 0
        if response.error:
            print(f"Error clearing existing ABP data: {response.error}")
        else:
            print(f"Successfully cleared {response.count} existing ABP records.")
    except Exception as e:
        print(f"Error clearing existing ABP data: {e}")

if __name__ == "__main__":
    clear_existing_abp_data() # Clear old data before fetching new

    # Vessels Alongside - Arrival Time at index 4, Berth at index 5 (Based on previous info)
    alongside_vessels = fetch_and_parse_table_data(
        ABP_VESSELS_ALONGSIDE_URL, "Alongside", arrival_time_column_index=4, berth_column_index=5
    )
    store_abp_data(alongside_vessels)

    # Planned Movements - PLEASE INSPECT WEBSITE FOR CORRECT INDICES
    planned_movements = fetch_and_parse_table_data(
        ABP_PLANNED_MOVEMENTS_URL, "Planned", arrival_time_column_index=4, berth_column_index=6 # Tentative - PLEASE VERIFY
    )
    store_abp_data(planned_movements)

    # Vessels Underway - PLEASE INSPECT WEBSITE FOR CORRECT INDICES
    underway_vessels = fetch_and_parse_table_data(
        ABP_VESSELS_UNDERWAY_URL, "Underway", arrival_time_column_index=3, berth_column_index=5 # Tentative - PLEASE VERIFY
    )
    store_abp_data(underway_vessels)

    # Ships at Anchor - PLEASE INSPECT WEBSITE FOR CORRECT INDICES
    anchor_vessels = fetch_and_parse_table_data(
        ABP_SHIPS_AT_ANCHOR_URL, "At Anchor", arrival_time_column_index=3, berth_column_index=4 # Tentative - PLEASE VERIFY
    )
    store_abp_data(anchor_vessels)

    print("ABP data collection complete.")
