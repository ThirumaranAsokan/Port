import React from 'react';

function PortFilter({ ports, regions, statuses, filters, onFilterChange }) {
  return (
    <div className="filter-container">
      <div className="filter-group">
        <label htmlFor="port-filter">Port:</label>
        <select 
          id="port-filter" 
          value={filters.port}
          onChange={(e) => onFilterChange('port', e.target.value)}
        >
          {ports.map(port => (
            <option key={port.id} value={port.id}>{port.name}</option>
          ))}
        </select>
      </div>
      
      <div className="filter-group">
        <label htmlFor="region-filter">Region:</label>
        <select 
          id="region-filter" 
          value={filters.region}
          onChange={(e) => onFilterChange('region', e.target.value)}
        >
          {regions.map(region => (
            <option key={region.id} value={region.id}>{region.name}</option>
          ))}
        </select>
      </div>
      
      <div className="filter-group">
        <label htmlFor="status-filter">Vessel Status:</label>
        <select 
          id="status-filter" 
          value={filters.status}
          onChange={(e) => onFilterChange('status', e.target.value)}
        >
          {statuses.map(status => (
            <option key={status.id} value={status.id}>{status.name}</option>
          ))}
        </select>
      </div>
      
      <div className="filter-group">
        <label htmlFor="search-filter">Search Vessel:</label>
        <input
          id="search-filter"
          type="text"
          placeholder="Vessel name or MMSI"
          value={filters.searchTerm}
          onChange={(e) => onFilterChange('searchTerm', e.target.value)}
        />
      </div>
    </div>
  );
}

export default PortFilter;