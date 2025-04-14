import asyncio
import websockets
import json
import os
from datetime import datetime, timezone
from supabase import create_client, Client

# Supabase setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# AIS Stream API key
AIS_API_KEY = os.environ.get("AIS_API_KEY", "your_ais_stream_api_key")

async def connect_ais_stream():
    """Connect to the AIS Stream WebSocket and process vessel position data."""
    while True:
        try:
            async with websockets.connect("wss://stream.aisstream.io/v0/stream") as websocket:
                print(f"[{datetime.now(timezone.utc)}] Connected to AIS Stream")
                
                # Subscribe to global shipping data
                # We're not filtering by specific vessels, so we get worldwide data
                subscribe_message = {
                    "APIKey": AIS_API_KEY,
                    "BoundingBoxes": [[[-90, -180], [90, 180]]],  # Worldwide coverage
                    "FilterMessageTypes": ["PositionReport"]
                }
                
                subscribe_message_json = json.dumps(subscribe_message)
                await websocket.send(subscribe_message_json)
                
                # Process messages as they arrive
                async for message_json in websocket:
                    try:
                        message = json.loads(message_json)
                        message_type = message.get("MessageType")
                        
                        if message_type == "PositionReport":
                            await process_position_report(message)
                            
                    except Exception as e:
                        print(f"Error processing message: {e}")
        
        except Exception as e:
            print(f"WebSocket connection error: {e}")
            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

async def process_position_report(message):
    """Process an AIS position report and store it in the database."""
    try:
        ais_message = message['Message']['PositionReport']
        
        # Extract vessel data
        mmsi = ais_message.get('UserID')
        vessel_name = await get_vessel_name(mmsi)
        latitude = ais_message.get('Latitude')
        longitude = ais_message.get('Longitude')
        speed = ais_message.get('SOG')  # Speed Over Ground
        course = ais_message.get('COG')  # Course Over Ground
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Print for logging
        print(f"[{timestamp}] Vessel: {vessel_name or mmsi} Position: {latitude}, {longitude} Speed: {speed} Course: {course}")
        
        # Store in database
        vessel_data = {
            "mmsi": mmsi,
            "vessel_name": vessel_name,
            "lat": latitude,
            "lon": longitude,
            "speed": speed,
            "course": course,
            "timestamp": timestamp
        }
        
        response = supabase.table("vessel_positions").insert(vessel_data).execute()
        
        # Check if we need to make a delay prediction
        if speed and speed < 3.0:  # Potential delay if ship is moving slowly
            await trigger_delay_prediction(vessel_data)
    
    except Exception as e:
        print(f"Error processing position report: {e}")

async def get_vessel_name(mmsi):
    """Get vessel name from MMSI number (using existing database or external API)."""
    try:
        # Check if we already have the vessel name in our database
        response = supabase.table("vessel_metadata").select("vessel_name").eq("mmsi", mmsi).execute()
        
        if response.data and response.data[0].get("vessel_name"):
            return response.data[0].get("vessel_name")
        
        # If not, we could query an external API for vessel info
        # For now, return None and let the system use MMSI as identifier
        return None
    
    except Exception as e:
        print(f"Error getting vessel name: {e}")
        return None

async def trigger_delay_prediction(vessel_data):
    """Trigger a delay prediction for a vessel that appears to be delayed."""
    try:
        # Add to prediction queue
        queue_data = {
            "mmsi": vessel_data["mmsi"],
            "vessel_name": vessel_data["vessel_name"],
            "position_data": json.dumps(vessel_data),
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("prediction_queue").insert(queue_data).execute()
        
    except Exception as e:
        print(f"Error triggering delay prediction: {e}")

if __name__ == "__main__":
    asyncio.run(connect_ais_stream())
