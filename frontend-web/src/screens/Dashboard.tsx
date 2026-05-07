import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, Activity, Users, Battery, 
  MapPin, Download, RefreshCcw, AlertTriangle 
} from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import './Dashboard.css';

// Mock Data for Prototype
const MOCK_STATS = {
  activeDevices: 142,
  emergenciesToday: 3,
  helmetCompliance: 94,
  avgBattery: 78
};

const MOCK_EVENTS = [
  { id: 'EV-001', device: 'PI-Alpha', type: 'EMERGENCY', reason: 'Crash Detected', time: '10:42 AM', severity: 'high' },
  { id: 'EV-002', device: 'PI-Beta', type: 'WARNING', reason: 'Sidewalk Riding', time: '10:15 AM', severity: 'medium' },
  { id: 'EV-003', device: 'PI-Gamma', type: 'WARNING', reason: 'No Helmet', time: '09:30 AM', severity: 'medium' },
  { id: 'EV-004', device: 'PI-Delta', type: 'INFO', reason: 'Device Paired', time: '09:00 AM', severity: 'low' },
];

const MOCK_CHART_DATA = [
  { time: '06:00', alerts: 2 },
  { time: '08:00', alerts: 12 },
  { time: '10:00', alerts: 8 },
  { time: '12:00', alerts: 15 },
  { time: '14:00', alerts: 5 },
  { time: '16:00', alerts: 18 },
  { time: '18:00', alerts: 20 },
];

const MOCK_PIE_DATA = [
  { name: 'Road', value: 85 },
  { name: 'Sidewalk', value: 15 },
];
const COLORS = ['#10b981', '#ef4444'];

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate API fetch from AWS/MongoDB
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header">
        <h1 className="dashboard-title">
          <ShieldAlert size={32} color="#3b82f6" />
          Safe Mobility Admin
        </h1>
        <div className="header-actions">
          <button className="btn">
            <RefreshCcw size={16} /> Refresh
          </button>
          <button className="btn btn-primary">
            <Download size={16} /> Export Logs
          </button>
        </div>
      </header>

      {/* Stats Overview */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue"><Users /></div>
          <div className="stat-content">
            <h3>Active Devices</h3>
            <p className="stat-value">{MOCK_STATS.activeDevices}</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red"><AlertTriangle /></div>
          <div className="stat-content">
            <h3>Emergencies Today</h3>
            <p className="stat-value">{MOCK_STATS.emergenciesToday}</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green"><Activity /></div>
          <div className="stat-content">
            <h3>Helmet Compliance</h3>
            <p className="stat-value">{MOCK_STATS.helmetCompliance}%</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon yellow"><Battery /></div>
          <div className="stat-content">
            <h3>Avg Battery</h3>
            <p className="stat-value">{MOCK_STATS.avgBattery}%</p>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="main-grid">
        {/* Left Col: Map */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Live Device Tracking (Map Prototype)</h2>
          </div>
          <div className="map-placeholder">
            <div style={{ opacity: loading ? 1 : 0.2, transition: 'opacity 0.5s' }}>
              Loading Map Data...
            </div>
            {!loading && (
              <>
                <MapPin className="map-pin" size={32} style={{ top: '40%', left: '30%' }} />
                <MapPin className="map-pin" size={24} style={{ top: '60%', left: '70%', color: '#10b981' }} />
                <MapPin className="map-pin" size={24} style={{ top: '20%', left: '50%', color: '#f59e0b' }} />
                <div style={{ position: 'absolute', bottom: 20, fontSize: '0.875rem' }}>
                  AWS Location Services / Maps API Integration Ready
                </div>
              </>
            )}
          </div>
        </div>

        {/* Right Col: Charts */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Alerts Timeline</h2>
            </div>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={MOCK_CHART_DATA}>
                  <defs>
                    <linearGradient id="colorAlerts" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="time" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                    itemStyle={{ color: '#f8fafc' }}
                  />
                  <Area type="monotone" dataKey="alerts" stroke="#ef4444" fillOpacity={1} fill="url(#colorAlerts)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Riding Environment</h2>
            </div>
            <div className="chart-container" style={{ height: '200px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={MOCK_PIE_DATA}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {MOCK_PIE_DATA.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }} />
                  <Legend verticalAlign="bottom" height={36} iconType="circle"/>
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom: Table */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Recent Device Logs</h2>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Event ID</th>
                <th>Device</th>
                <th>Type</th>
                <th>Reason</th>
                <th>Time</th>
                <th>Severity</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_EVENTS.map(event => (
                <tr key={event.id}>
                  <td>{event.id}</td>
                  <td>{event.device}</td>
                  <td style={{ fontWeight: 500 }}>{event.type}</td>
                  <td>{event.reason}</td>
                  <td>{event.time}</td>
                  <td>
                    <span className={`badge badge-${event.severity}`}>
                      {event.severity.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
