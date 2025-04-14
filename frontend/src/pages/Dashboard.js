import React, { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';
import VesselTable from '../components/VesselTable';
import MapView from '../components/MapView';
import DelayPredictions from '../components/DelayPredictions';
import PortFilter from '../components/PortFilter';

// Initialize Supabase client
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseKey = process.env.REACT_APP_SUPABASE_ANON_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

function Dashboard() {
  const [vessels, setVessels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    port: 'all',
    region: 'all',
    status: 'all',
    searchTerm: ''
  });
  
  // Available ports and regions for filtering
  const ports = [
    { id: 'all', name: 'All Ports' },
    { id: 'GBDOV', name: 'Dover' },
    { id: 'GBPME', name: 'Portsmouth' },
    { id: 'FRCQF', name: 'Calais' },
    { id: 'FRBOL', name: 'Boulogne' },
    { id: 'BEDUN', name: 'Dunkirk' },
    { id: 'NLRTM', name: 'Rotterdam' },
    { id: 'BEANR', name: 'Antwerp' }
  ];
  
  const regions = [
    { id: 'all', name: 'All Regions' },
    { id: 'uk', name: 'United Kingdom' },
    { id: 'france', name: 'France' },
    { id: 'netherlands', name: 'Netherlands' },
    { id: 'belgium', name: 'Belgium' }
  ];
  
  const statuses = [
    { id: 'all', name: 'All Statuses' },
    { id: 'moving', name: 'Moving' },
    { id: 'anchored', name: 'Anchored' },
    { id: 'delayed', name: 'Delayed' },
    { id: 'port', name: 'In Port' }
  ];

  useEffect(() => {
    async function fetchVessels() {
      setLoading(true);
      
      // Build query based on filters
      let query = supabase
        .from('vessel_positions')
        .select(`
          *,
          vessel_metadata(vessel_name, vessel_type, flag, destination)
        `)
        .order('timestamp', { ascending: false })
        .limit(100);
      
      // Apply port filter if selected
      if (filters.port !== 'all') {
        // We assume vessel_metadata has a destination field with port code
        query = query.eq('vessel_metadata.destination', filters.port);
      }
      
      // Apply region filter if selected
      if (filters.region !== 'all') {
        // This would require a region field in your metadata or a way to map ports to regions
        // For simplicity, we're assuming the region info is stored somewhere
        query = query.eq('vessel_metadata.region', filters.region);
      }
      
      // Apply status filter
      if (filters.status !== 'all') {
        switch (filters.status) {
          case 'moving':
            query = query.gt('speed', 3);
            break;
          case 'anchored':
            query = query.lte('speed', 1);
            break;
          case 'delayed':
            // Join with delay_predictions table to find delayed vessels
            // This is a simplified approach - would need more complex query in real app
            query = query.eq('has_delay', true);
            break;
          case 'port':
            // Vessels in port would typically have specific status codes
            query = query.eq('in_port', true);
            break;
          default:
            break;
        }
      }
      
      // Apply search term if provided
      if (filters.searchTerm) {
        query = query.ilike('vessel_metadata.vessel_name', `%${filters.searchTerm}%`);
      }
      
      const { data, error } = await query;
      
      if (error) {
        console.error('Error fetching vessels:', error);
      } else {
        setVessels(data || []);
      }
      
      setLoading(false);
    }
    
    fetchVessels();
    
    // Set up real-time subscription for vessel position updates
    const subscription = supabase
      .from('vessel_positions')
      .on('INSERT', payload => {
        // Add the new vessel to our state if it passes filters
        // In a real app, you'd check filters here too
        setVessels(current => {
          // Check if vessel already exists in our list
          const existingIndex = current.findIndex(v => v.mmsi === payload.new.mmsi);
          
          // If exists, update it, otherwise add to the list
          if (existingIndex >= 0) {
            const updated = [...current];
            updated[existingIndex] = payload.new;
            return updated;
          } else {
            return [payload.new, ...current].slice(0, 100);
          }
        });
      })
      .subscribe();
    
    // Clean up subscription when component unmounts
    return () => {
      supabase.removeSubscription(subscription);
    };
  }, [filters]);

  const handleFilterChange = (type, value) => {
    setFilters(prev => ({ ...prev, [type]: value }));
  };

  return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">PortGuard AI - Global Vessel Dashboard</h1>
      
      <div className="filters-container">
        <PortFilter 
          ports={ports}
          regions={regions}
          statuses={statuses}
          filters={filters}
          onFilterChange={handleFilterChange}
        />
      </div>
      
      <div className="map-container">
        <MapView vessels={vessels} />
      </div>
      
      <div className="data-container">
        <div className="vessels-table">
          <VesselTable vessels={vessels} loading={loading} />
        </div>
        
        <div className="delay-predictions">
          <DelayPredictions vessels={vessels.filter(v => v.speed < 3)} />
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
