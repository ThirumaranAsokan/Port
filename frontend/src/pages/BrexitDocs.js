import React, { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';

// Initialize Supabase client
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseKey = process.env.REACT_APP_SUPABASE_ANON_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

function BrexitDocs() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  
  useEffect(() => {
    async function fetchDocuments() {
      setLoading(true);
      
      let query = supabase
        .from('brexit_documents')
        .select('*')
        .order('created_at', { ascending: false });
      
      if (searchTerm) {
        query = query.or(`summary.ilike.%${searchTerm}%,document_name.ilike.%${searchTerm}%`);
      }
      
      const { data, error } = await query;
      
      if (error) {
        console.error('Error fetching Brexit documents:', error);
      } else {
        setDocuments(data || []);
      }
      
      setLoading(false);
    }
    
    fetchDocuments();
    
    // Set up real-time subscription for new documents
    const subscription = supabase
      .from('brexit_documents')
      .on('INSERT', payload => {
        setDocuments(current => [payload.new, ...current]);
      })
      .subscribe();
    
    return () => {
      supabase.removeSubscription(subscription);
    };
  }, [searchTerm]);

  // Filter documents
  const filteredDocs = documents.filter(doc => {
    if (filter === 'all') return true;
    return doc.document_type === filter;
  });

  const handleDocClick = (doc) => {
    setSelectedDoc(doc);
  };

  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    // Show upload progress or notification
    alert(`File "${file.name}" selected. In a real app, this would upload to the server for processing.`);
    
    // In a real app, you would upload the file to a server endpoint
    // For demo purposes, we're just showing a message
  };

  return (
    <div className="brexit-docs-page">
      <h1>Brexit Documentation Center</h1>
      
      <div className="docs-tools">
        <div className="search-filter">
          <input
            type="text"
            placeholder="Search documents..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="doc-search"
          />
          
          <select 
            value={filter} 
            onChange={(e) => setFilter(e.target.value)}
            className="doc-filter"
          >
            <option value="all">All Documents</option>
            <option value="pdf">PDF Documents</option>
            <option value="jpg">Images</option>
            <option value="txt">Text Files</option>
          </select>
        </div>
        
        <div className="upload-container">
          <label htmlFor="doc-upload" className="upload-btn">
            Upload New Document
          </label>
          <input 
            type="file" 
            id="doc-upload" 
            style={{ display: 'none' }} 
            accept=".pdf,.jpg,.jpeg,.png,.txt"
            onChange={handleUpload}
          />
        </div>
      </div>
      
      <div className="docs-content">
        <div className="docs-list">
          <h2>Available Documents ({filteredDocs.length})</h2>
          
          {loading ? (
            <div className="loading">Loading documents...</div>
          ) : filteredDocs.length > 0 ? (
            <ul className="doc-items">
              {filteredDocs.map(doc => (
                <li 
                  key={doc.id} 
                  className={`doc-item ${selectedDoc?.id === doc.id ? 'selected' : ''}`}
                  onClick={() => handleDocClick(doc)}
                >
                  <div className="doc-icon">
                    {doc.document_type === 'pdf' && '📄'}
                    {doc.document_type === 'jpg' && '🖼️'}
                    {doc.document_type === 'txt' && '📝'}
                    {!['pdf', 'jpg', 'txt'].includes(doc.document_type) && '📁'}
                  </div>
                  <div className="doc-info">
                    <h3>{doc.document_name}</h3>
                    <p className="doc-date">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="no-docs">
              No documents found matching your criteria
            </div>
          )}
        </div>
        
        <div className="doc-details">
          {selectedDoc ? (
            <div className="doc-analysis">
              <h2>{selectedDoc.document_name}</h2>
              
              <div className="doc-section">
                <h3>Summary</h3>
                <p>{selectedDoc.summary}</p>
              </div>
              
              <div className="doc-section">
                <h3>Action Items</h3>
                <div className="action-items">
                  {selectedDoc.action_items.split('\n').map((item, index) => (
                    <div key={index} className="action-item">
                      <span className="action-bullet">•</span>
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="doc-section">
                <h3>Important Deadlines</h3>
                <p>{selectedDoc.deadlines || 'No specific deadlines mentioned'}</p>
              </div>
              
              <div className="doc-section">
                <h3>Port Requirements</h3>
                <p>{selectedDoc.port_requirements || 'No specific port requirements mentioned'}</p>
              </div>
              
              <div className="doc-meta">
                <p>Document Type: {selectedDoc.document_type.toUpperCase()}</p>
                <p>Processed: {new Date(selectedDoc.created_at).toLocaleString()}</p>
              </div>
            </div>
          ) : (
            <div className="no-selection">
              <div className="placeholder-message">
                <h3>Select a document to view analysis</h3>
                <p>PortGuard AI automatically analyzes Brexit documents for key information</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default BrexitDocs;