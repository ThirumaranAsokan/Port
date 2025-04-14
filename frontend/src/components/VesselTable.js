import React, { useState } from 'react';

function VesselTable({ vessels, loading }) {
  const [sortField, setSortField] = useState('timestamp');
  const [sortDirection, setSortDirection] = useState('desc');
  const [page, setPage] = useState(1);
  const rowsPerPage = 10;
  
  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };
  
  const sortedVessels = [...vessels].sort((a, b) => {
    // Handle nested fields (from vessel_metadata)
    const fieldA = sortField.includes('.') 
      ? a[sortField.split('.')[0]][sortField.split('.')[1]]
      : a[sortField];
      
    const fieldB = sortField.includes('.')
      ? b[sortField.split('.')[0]][sortField.split('.')[1]]
      : b[sortField];
    
    // Handle string/number comparison
    if (typeof fieldA === 'string' && typeof fieldB === 'string') {
      return sortDirection === 'asc' 
        ? fieldA.localeCompare(fieldB) 
        : fieldB.localeCompare(fieldA);
    } else {
      return sortDirection === 'asc' 
        ? fieldA - fieldB 
        : fieldB - fieldA;
    }
  });
  
  // Calculate pagination
  const totalPages = Math.ceil(sortedVessels.length / rowsPerPage);
  const paginatedVessels = sortedVessels.slice(
    (page - 1) * rowsPerPage,
    page * rowsPerPage
  );
  
  // Helper for status display
  const getStatusLabel = (vessel) => {
    if (vessel.speed > 3) return 'Moving';
    if (vessel.speed <= 1) return 'Stationary';
    return 'Slow';
  };
  
  const getStatusClass = (vessel) => {
    if (vessel.speed > 3) return 'status-moving';
    if (vessel.speed <= 1) return 'status-stationary';
    return 'status-slow';
  };
  
  return (
    <div className="vessel-table-container">
      <h2>Vessel Positions</h2>
      
      {loading ? (
        <div className="loading">Loading vessel data...</div>
      ) : (
        <>
          <table className="vessel-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('vessel_metadata.vessel_name')}>
                  Vessel Name {sortField === 'vessel_metadata.vessel_name' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('mmsi')}>
                  MMSI {sortField === 'mmsi' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('lat')}>
                  Latitude {sortField === 'lat' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('lon')}>
                  Longitude {sortField === 'lon' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('speed')}>
                  Speed (knots) {sortField === 'speed' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('vessel_metadata.destination')}>
                  Destination {sortField === 'vessel_metadata.destination' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th>Status</th>
                <th onClick={() => handleSort('timestamp')}>
                  Last Updated {sortField === 'timestamp' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
              </tr>
            </thead>
            <tbody>
              {paginatedVessels.length > 0 ? (
                paginatedVessels.map(vessel => (
                  <tr key={`${vessel.mmsi}-${vessel.timestamp}`}>
                    <td>{vessel.vessel_metadata?.vessel_name || 'Unknown'}</td>
                    <td>{vessel.mmsi}</td>
                    <td>{vessel.lat.toFixed(4)}</td>
                    <td>{vessel.lon.toFixed(4)}</td>
                    <td>{vessel.speed.toFixed(1)}</td>
                    <td>{vessel.vessel_metadata?.destination || 'Unknown'}</td>
                    <td className={getStatusClass(vessel)}>{getStatusLabel(vessel)}</td>
                    <td>{new Date(vessel.timestamp).toLocaleString()}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="8" className="no-data">No vessels found matching your criteria</td>
                </tr>
              )}
            </tbody>
          </table>
          
          {totalPages > 1 && (
            <div className="pagination">
              <button 
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </button>
              
              <span className="page-info">
                Page {page} of {totalPages}
              </span>
              
              <button 
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default VesselTable;