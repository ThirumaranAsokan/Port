import React, { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';

// Initialize Supabase client
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseKey = process.env.REACT_APP_SUPABASE_ANON_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

function DelayPredictions({ vessels }) {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPredictions() {
      setLoading(true);
      
      // Get MMSIs of vessels we want predictions for
      const mmsiList = vessels.map(v => v.mmsi);
      
      if (mmsiList.length === 0) {
        setPredictions([]);
        setLoading(false);
        return;
      }
      
      // Fetch the latest prediction for each vessel
      const { data, error } = await supabase
        .from('delay_predictions')
        .select('*')
        .in('mmsi', mmsiList)
        .order('created_at', { ascending: false });
      
      if (error) {
        console.error('Error fetching predictions:', error);
        setPredictions([]);
      } else {
        // Get only the most recent prediction for each vessel
        const latestPredictions = {};
        data.forEach(pred => {
          if (!latestPredictions[pred.mmsi] || 
              new Date(pred.created_at) > new Date(latestPredictions[pred.mmsi].created_at)) {
            latestPredictions[pred.mmsi] = pred;
          }
        });
        
        setPredictions(Object.values(latestPredictions));
      }
      
      setLoading(false);
    }
    
    fetchPredictions();
    
    // Set up subscription for real-time updates to delay predictions
    const subscription = supabase
      .from('delay_predictions')
      .on('INSERT', payload => {
        setPredictions(current => {
          // Check if we already have a prediction for this vessel
          const existingIndex = current.findIndex(p => p.mmsi === payload.new.mmsi);
          
          // If exists and new one is more recent, update it
          if (existingIndex >= 0) {
            if (new Date(payload.new.created_at) > new Date(current[existingIndex].created_at)) {
              const updated = [...current];
              updated[existingIndex] = payload.new;
              return updated;
            }
            return current;
          } else {
            // Add new prediction
            return [...current, payload.new];
          }
        });
      })
      .subscribe();
    
    return () => {
      supabase.removeSubscription(subscription);
    };
  }, [vessels]);

  // Determine CSS class based on confidence score
  const getConfidenceClass = (score) => {
    if (score >= 0.75) return 'high-confidence';
    if (score >= 0.4) return 'medium-confidence';
    return 'low-confidence';
  };

  return (
    <div className="delay-predictions-container">
      <h2>Delay Predictions</h2>
      
      {loading ? (
        <div className="loading">Loading predictions...</div>
      ) : predictions.length > 0 ? (
        <div className="predictions-list">
          {predictions
            .sort((a, b) => b.predicted_delay_minutes - a.predicted_delay_minutes)
            .map(prediction => (
              <div key={prediction.id} className="prediction-card">
                <div className="prediction-header">
                  <h3>{prediction.vessel_name || `Vessel MMSI: ${prediction.mmsi}`}</h3>
                  <span className={`confidence-badge ${getConfidenceClass(prediction.confidence_score)}`}>
                    {Math.round(prediction.confidence_score * 100)}% Confidence
                  </span>
                </div>
                
                <div className="prediction-details">
                  <div className="delay-time">
                    <span className="delay-label">Predicted Delay:</span>
                    <span className="delay-value">
                      {prediction.predicted_delay_minutes > 60 
                        ? `${Math.floor(prediction.predicted_delay_minutes / 60)}h ${prediction.predicted_delay_minutes % 60}m` 
                        : `${prediction.predicted_delay_minutes}m`}
                    </span>
                  </div>
                  
                  <div className="prediction-reasoning">
                    <p>{prediction.reasoning}</p>
                  </div>
                  
                  <div className="prediction-time">
                    <small>Prediction made: {new Date(prediction.created_at).toLocaleString()}</small>
                  </div>
                </div>
              </div>
            ))}
        </div>
      ) : (
        <div className="no-predictions">
          No delay predictions available for the current vessels
        </div>
      )}
    </div>
  );
}

export default DelayPredictions;