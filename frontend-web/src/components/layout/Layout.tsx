import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { setAdminToken } from '../../api/axiosInstance';

export const Layout: React.FC = () => {
  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <div>
            <h1 style={{ fontSize: '1.8rem', margin: 0 }}>개요</h1>
            <p style={{ color: 'var(--text-muted)', margin: 0 }}>모빌리티 안전을 실시간으로 모니터링합니다.</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ background: 'var(--bg-card)', padding: '0.5rem 1rem', borderRadius: '20px', border: 'var(--glass-border)', fontSize: '0.875rem' }}>
              <span style={{ color: 'var(--accent-success)', marginRight: '0.5rem' }}>●</span> 시스템 정상
            </div>
            <button
              onClick={() => { setAdminToken(null); window.location.reload(); }}
              style={{
                background: 'var(--bg-card)', border: 'var(--glass-border)',
                borderRadius: '8px', padding: '0.4rem 0.875rem',
                color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.8rem',
              }}
            >
              로그아웃
            </button>
            <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
              A
            </div>
          </div>
        </header>
        <div className="animate-fade-in" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Outlet />
        </div>
      </main>
    </div>
  );
};
