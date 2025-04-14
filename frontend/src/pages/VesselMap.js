import React, { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';
import MapView from '../components/MapView';

// Initialize Supabase client
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseKey = process.env.REACT_APP_SUPABASE_ANON_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

function VesselMap() {
  const [vessels, setVessels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mapRegion, setMapRegion] = useState({
    center: [0.127, 51.5], // Default center (London)
    zoom: 5
  });

  useEffect(() => {
    async function fetchGlobalVessels() {
      setLoading(true);
      
      // Get the most recent positions for all vessels
      const { data, error } = await supabase
        .from('vessel_positions')
        .select(`
          *,
          vessel_metadata(vessel_name, vessel_type, flag, destination)
        `)
        .order('timestamp', { ascending: false })
        .limit(500); // Get more vessels for the global map
      
      if (error) {
        console.error('Error fetching global vessels:', error);
      } else {
        // Filter to get only the most recent position for each vessel
        const uniqueVessels = {};
        data.forEach(vessel => {
          if (!uniqueVessels[vessel.mmsi] || 
              new Date(vessel.timestamp) > new Date(uniqueVessels[vessel.mmsi].timestamp)) {
            uniqueVessels[vessel.mmsi] = vessel;
          }
        });
        
        setVessels(Object.values(uniqueVessels));
      }
      
      setLoading(false);
    }
    
    fetchGlobalVessels();
    
    // Set up real-time subscription for new vessel positions
    const subscription = supabase
      .from('vessel_positions')
      .on('INSERT', payload => {
        setVessels(current => {
          // Update vessel if it exists, otherwise add it
          const existingIndex = current.findIndex(v => v.mmsi === payload.new.mmsi);
          
          if (existingIndex >= 0) {
            if (new Date(payload.new.timestamp) > new Date(current[existingIndex].timestamp)) {
              const updated = [...current];
              updated[existingIndex] = payload.new;
              return updated;
            }
            return current;
          } else {
            return [...current, payload.new];
          }
        });
      })
      .subscribe();
    
    return () => {
      supabase.removeSubscription(subscription);
    };
  }, []);

  const handleRegionChange = (newRegion) => {
    setMapRegion(newRegion);
  };

  const handleVesselClick = (vessel) => {
    // Center map on vessel when clicked
    if (vessel.lat && vessel.lon) {
      setMapRegion({
        center: [vessel.lon, vessel.lat],
        zoom: 10
      });
    }
  };

  return (
    <div className="vessel-map-page">
      <h1>Global Vessel Tracker</h1>
      
      <div className="map-stats">
        <div className="stat-box">
          <h3>Active Vessels</h3>
          <p className="stat-value">{vessels.length}</p>
        </div>
        <div className="stat-box">
          <h3>Moving Vessels</h3>
          <p className="stat-value">{vessels.filter(v => v.speed > 3).length}</p>
        </div>
        <div className="stat-box">
          <h3>Anchored</h3>
          <p className="stat-value">{vessels.filter(v => v.speed <= 1).length}</p>
        </div>
      </div>
      
      <div className="global-map-container">
        {loading ? (
          <div className="loading-map">Loading global vessel data...</div>
        ) : (
          <MapView 
            vessels={vessels} 
            initialViewport={mapRegion}
            onRegionChange={handleRegionChange}
            onVesselClick={handleVesselClick}
            fullScreen={true}
          />
        )}
      </div>
      
      <div className="map-legend">
        <h3>Vessel Status</h3>
        <div className="legend-items">
          <div className="legend-item">
            <div className="color-dot" style={{ backgroundColor: '#ff0000' }}></div>
            <span>Stationary (0-1 knots)</span>
          </div>
          <div className="legend-item">
            <div className="color-dot" style={{ backgroundColor: '#ff7700' }}></div>
            <span>Slow (1-3 knots)</span>
          </div>
          <div className="legend-item">
            <div className="color-dot" style={{ backgroundColor: '#ffff00' }}></div>
            <span>Medium (3-10 knots)</span>
          </div>
          <div className="legend-item">
            <div className="color-dot" style={{ backgroundColor: '#00ff00' }}></div>
            <span>Fast ({'>'}10 knots)</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default VesselMap;