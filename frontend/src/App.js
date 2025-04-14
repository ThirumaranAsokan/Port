import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import VesselMap from './pages/VesselMap';
import BrexitDocs from './pages/BrexitDocs';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <div className="logo">
            <h1>PortGuard AI</h1>
          </div>
          <nav className="main-nav">
            <ul>
              <li>
                <Link to="/">Dashboard</Link>
              </li>
              <li>
                <Link to="/vessel-map">Global Vessel Map</Link>
              </li>
              <li>
                <Link to="/brexit-docs">Brexit Documents</Link>
              </li>
            </ul>
          </nav>
        </header>

        <main className="app-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/vessel-map" element={<VesselMap />} />
            <Route path="/brexit-docs" element={<BrexitDocs />} />
          </Routes>
        </main>

        <footer className="app-footer">
          <p>&copy; {new Date().getFullYear()} PortGuard AI - Real-time Vessel Tracking & Brexit Documentation</p>
        </footer>
      </div>
    </Router>
  );
}

export default App;

