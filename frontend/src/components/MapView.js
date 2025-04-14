import React, { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

// Set your Mapbox token here
mapboxgl.accessToken = process.env.REACT_APP_MAPBOX_TOKEN || 'your_mapbox_token';

function MapView({ vessels }) {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const markers = useRef({});

  useEffect(() => {
    // Initialize map if it doesn't exist yet
    if (!map.current) {
      map.current = new mapboxgl.Map({
        container: mapContainer.current,
        style: 'mapbox://styles/mapbox/navigation-night-v1', // Good style for maritime
        center: [0.127, 51.5], // Default center (London)
        zoom: 5
      });

      // Add navigation controls
      map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');
      
      // Add scale control
      map.current.addControl(new mapboxgl.ScaleControl());

      // Add fullscreen control
      map.current.addControl(new mapboxgl.FullscreenControl());
    }
    
    // Wait for map to load before adding vessels
    if (!map.current.loaded()) {
      map.current.on('load', () => updateVesselMarkers());
    } else {
      updateVesselMarkers();
    }
  }, []);

  // Update markers when vessels data changes
  useEffect(() => {
    if (map.current && map.current.loaded()) {
      updateVesselMarkers();
    }
  }, [vessels]);

  const updateVesselMarkers = () => {
    const currentMarkerIds = new Set();
    
    // Add or update markers for each vessel
    vessels.forEach(vessel => {
      const id = vessel.mmsi.toString();
      currentMarkerIds.add(id);
      
      // Skip if no valid coordinates
      if (!vessel.lat || !vessel.lon) return;
      
      // Get vessel color based on speed
      const color = getVesselColor(vessel.speed);
      
      // Create or update marker
      if (!markers.current[id]) {
        // Create marker element
        const el = document.createElement('div');
        el.className = 'vessel-marker';
        el.style.backgroundColor = color;
        el.style.width = '10px';
        el.style.height = '10px';
        el.style.borderRadius = '50%';
        el.style.border = '2px solid white';
        
        // Create popup
        const popup = new mapboxgl.Popup({ offset: 25 })
          .setHTML(`
            <div class="vessel-popup">
              <h3>${vessel.vessel_metadata?.vessel_name || 'Unknown Vessel'}</h3>
              <p>MMSI: ${vessel.mmsi}</p>
              <p>Speed: ${vessel.speed.toFixed(1)} knots</p>
              <p>Course: ${vessel.course?.toFixed(0) || 'Unknown'}°</p>
              <p>Destination: ${vessel.vessel_metadata?.destination || 'Unknown'}</p>
              <p>Last Update: ${new Date(vessel.timestamp).toLocaleString()}</p>
            </div>
          `);
        
        // Add marker to map
        markers.current[id] = new mapboxgl.Marker(el)
          .setLngLat([vessel.lon, vessel.lat])
          .setPopup(popup)
          .addTo(map.current);
      } else {
        // Update existing marker
        markers.current[id].setLngLat([vessel.lon, vessel.lat]);
        
        // Update popup content
        const popup = markers.current[id].getPopup();
        popup.setHTML(`
          <div class="vessel-popup">
            <h3>${vessel.vessel_metadata?.vessel_name || 'Unknown Vessel'}</h3>
            <p>MMSI: ${vessel.mmsi}</p>
            <p>Speed: ${vessel.speed.toFixed(1)} knots</p>
            <p>Course: ${vessel.course?.toFixed(0) || 'Unknown'}°</p>
            <p>Destination: ${vessel.vessel_metadata?.destination || 'Unknown'}</p>
            <p>Last Update: ${new Date(vessel.timestamp).toLocaleString()}</p>
          </div>
        `);
        
        // Update marker color
        const el = markers.current[id].getElement();
        el.style.backgroundColor = color;
      }
    });
    
    // Remove markers for vessels no longer in the dataset
    Object.keys(markers.current).forEach(id => {
      if (!currentMarkerIds.has(id)) {
        markers.current[id].remove();
        delete markers.current[id];
      }
    });
  };
  
  const getVesselColor = (speed) => {
    // Color coding by speed
    if (speed < 1) return '#ff0000'; // Red for stationary
    if (speed < 3) return '#ff7700'; // Orange for slow
    if (speed < 10) return '#ffff00'; // Yellow for medium
    return '#00ff00'; // Green for fast
  };

  return <div ref={mapContainer} className="map-view" style={{ width: '100%', height: '500px' }} />;
}

export default MapView;