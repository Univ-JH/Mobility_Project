import React, { useState } from 'react';
import { Download } from 'lucide-react';
import { useEventLogs } from '../hooks/queries/useAdminQueries';
import { format } from 'date-fns';
import { adminApi } from '../api/adminApi';

export const EventLogs: React.FC = () => {
  const [page, setPage] = useState(1);
  const size = 15;
  const { data, isLoading } = useEventLogs(page, size);

  const handleExport = async () => {
    try {
      const response = await adminApi.exportLogs();
      const url = window.URL.createObjectURL(new Blob([response as any]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'events_export.csv');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (e) {
      console.error("Export failed", e);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch(severity) {
      case 'critical': return 'var(--accent-critical)';
      case 'high': return '#f59e0b'; // amber
      case 'medium': return '#fbbf24'; // yellow
      default: return 'var(--accent-primary)';
    }
  };

  return (
    <div className="glass-panel" style={{ flex: 1, padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.2rem', margin: 0 }}>System Event Logs</h2>
        <button className="btn-primary" onClick={handleExport} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Download size={16} /> Export CSV
        </button>
      </div>

      <div style={{ flex: 1, overflow: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '1rem', fontWeight: 500 }}>Time</th>
              <th style={{ padding: '1rem', fontWeight: 500 }}>Device ID</th>
              <th style={{ padding: '1rem', fontWeight: 500 }}>Event Type</th>
              <th style={{ padding: '1rem', fontWeight: 500 }}>Severity</th>
              <th style={{ padding: '1rem', fontWeight: 500 }}>Reason</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={5} style={{ padding: '2rem', textAlign: 'center' }}>Loading logs...</td></tr>
            ) : data?.items.length === 0 ? (
              <tr><td colSpan={5} style={{ padding: '2rem', textAlign: 'center' }}>No events found.</td></tr>
            ) : (
              data?.items.map(log => (
                <tr key={log.eventId} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>
                    {format(new Date(log.eventAt), 'yyyy-MM-dd HH:mm:ss')}
                  </td>
                  <td style={{ padding: '1rem' }}>{log.deviceId}</td>
                  <td style={{ padding: '1rem' }}>{log.eventType}</td>
                  <td style={{ padding: '1rem' }}>
                    <span style={{ 
                      padding: '0.25rem 0.75rem', 
                      borderRadius: '12px', 
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      background: `rgba(${getSeverityColor(log.severity).replace('#', '')}, 0.2)`, // Needs hex to rgb logic in real app, simplified here
                      color: getSeverityColor(log.severity),
                      border: `1px solid ${getSeverityColor(log.severity)}`
                    }}>
                      {log.severity.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{log.reason}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          Showing page {data?.page || 1} of {Math.ceil((data?.totalCount || 0) / size)} (Total: {data?.totalCount || 0})
        </span>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button 
            disabled={page === 1} 
            onClick={() => setPage(p => Math.max(1, p - 1))}
            style={{ background: 'var(--bg-dark)', border: 'var(--glass-border)', color: 'white', padding: '0.5rem 1rem', borderRadius: '4px', cursor: page === 1 ? 'not-allowed' : 'pointer' }}
          >
            Prev
          </button>
          <button 
            disabled={!data || data.items.length < size} 
            onClick={() => setPage(p => p + 1)}
            style={{ background: 'var(--bg-dark)', border: 'var(--glass-border)', color: 'white', padding: '0.5rem 1rem', borderRadius: '4px', cursor: (!data || data.items.length < size) ? 'not-allowed' : 'pointer' }}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
};
