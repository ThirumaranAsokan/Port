// Install dependencies:
// npm install @supabase/supabase-js react-router-dom mapbox-gl

import { createClient } from '@supabase/supabase-js'
import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'

// Initialize Supabase client
const supabaseUrl = 'YOUR_SUPABASE_URL'
const supabaseKey = 'YOUR_SUPABASE_ANON_KEY'
const supabase = createClient(supabaseUrl, supabaseKey)

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/vessels" element={<VesselList />} />
        <Route path="/brexit" element={<BrexitDocuments />} />
      </Routes>
    </BrowserRouter>
  )
}

function Dashboard() {
  const [delayedVessels, setDelayedVessels] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Fetch initial data
    fetchDelayPredictions()
    
    // Subscribe to real-time updates
    const subscription = supabase
      .channel('delay_predictions_changes')
      .on('postgres_changes', 
        { event: 'INSERT', schema: 'public', table: 'delay_predictions' }, 
        handleNewPrediction)
      .subscribe()
    
    return () => {
      subscription.unsubscribe()
    }
  }, [])
  
  const fetchDelayPredictions = async () => {
    setLoading(true)
    
    // Get latest predictions for each vessel
    const { data, error } = await supabase
      .from('delay_predictions')
      .select('*')
      .order('created_at', { ascending: false })
      
    if (error) {
      console.error('Error fetching predictions:', error)
    } else {
      // Group by vessel name and take the latest
      const latestByVessel = {}
      data.forEach(prediction => {
        if (!latestByVessel[prediction.vessel_name] || 
            new Date(prediction.created_at) > new Date(latestByVessel[prediction.vessel_name].created_at)) {
          latestByVessel[prediction.vessel_name] = prediction
        }
      })
      
      setDelayedVessels(Object.values(latestByVessel))
    }
    
    setLoading(false)
  }
  
  const handleNewPrediction = (payload) => {
    const newPrediction = payload.new
    
    setDelayedVessels(prevVessels => {
      // Remove old prediction for this vessel if it exists
      const filtered = prevVessels.filter(v => v.vessel_name !== newPrediction.vessel_name)
      // Add the new prediction
      return [...filtered, newPrediction]
    })
  }
  
  if (loading) return <div>Loading...</div>
  
  return (
    <div className="dashboard">
      <h1>PortGuard AI Dashboard</h1>
      
      <div className="delay-summary">
        <h2>Current Vessel Delays</h2>
        {delayedVessels.length === 0 ? (
          <p>No delays detected</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Vessel</th>
                <th>Delay (min)</th>
                <th>Confidence</th>
                <th>Analysis</th>
              </tr>
            </thead>
            <tbody>
              {delayedVessels.map(vessel => (
                <tr key={vessel.id} className={vessel.predicted_delay_minutes > 30 ? 'severe-delay' : ''}>
                  <td>{vessel.vessel_name}</td>
                  <td>{vessel.predicted_delay_minutes}</td>
                  <td>{Math.round(vessel.confidence_score * 100)}%</td>
                  <td>{vessel.reasoning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// Additional components for VesselList and BrexitDocuments...
