import requests
from bs4 import BeautifulSoup  # We might still use this for initial page info
import pandas as pd
import time
import os
from supabase import create_client, Client
import xml.etree.ElementTree as ET  # For parsing XML


def fetch_abp_data():
    URL = "https://www.southamptonvts.co.uk/Live_Information/Shipping_Movements_and_Cruise_Ship_Schedule/Vessels_Alongside/"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(URL, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")  # Use response.content for bytes
    except requests.exceptions.RequestException as e:
        print(f"Error fetching ABP page: {e}")
        return None

    #  ---  FIND THE XML URL  ---
    #  The XML URL is directly available in the script tag
    xml_url = "https://www.southamptonvts.co.uk/content/files/assets/sotberthed.xml"
    #  ---  FIND THE XML URL  ---

    try:
        xml_response = requests.get(xml_url, headers=headers, timeout=10)
        xml_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching XML data: {e}")
        return None

    try:
        root = ET.fromstring(xml_response.text)
        #  ---  PARSE THE XML  ---
        #  This part will depend on the structure of the XML.
        #  You'll need to examine the XML to determine the correct tags and attributes to extract.
        data = []
        for vessel in root.findall(".//Vessel"):  # Adjust the tag name as needed
            vessel_data = {
                "Name": vessel.find("Name").text if vessel.find("Name") is not None else None,
                "Location": vessel.find("Location").text if vessel.find("Location") is not None else None,
                "ATB": vessel.find("ATB").text if vessel.find("ATB") is not None else None,
                "ATA": vessel.find("ATA").text if vessel.find("ATA") is not None else None,
                "AFD": vessel.find("AFD").text if vessel.find("AFD") is not None else None,
                "ADP": vessel.find("ADP").text if vessel.find("ADP") is not None else None,
                "ETB": vessel.find("ETB").text if vessel.find("ETB") is not None else None,
                "ETD": vessel.find("ETD").text if vessel.find("ETD") is not None else None,

                #  Add more fields as needed
            }
            data.append(vessel_data)
        #  ---  PARSE THE XML  ---

        if data:
            df = pd.DataFrame(data)
            return df
        else:
            print("No data extracted from XML.")
            return None

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
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
        push_to_supabase(df)
    else:
        print("No data fetched.")


if __name__ == "__main__":
    main()
