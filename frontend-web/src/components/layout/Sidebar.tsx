import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Map, List, ShieldAlert } from 'lucide-react';

export const Sidebar: React.FC = () => {
  return (
    <div style={{ width: '250px', background: 'var(--bg-card)', borderRight: 'var(--glass-border)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '2rem 1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <ShieldAlert color="var(--accent-primary)" size={28} />
        <h2 style={{ fontSize: '1.25rem', margin: 0, fontWeight: 700 }}>SafeMobility</h2>
      </div>
      
      <nav style={{ display: 'flex', flexDirection: 'column', padding: '0 1rem', gap: '0.5rem' }}>
        <NavLink 
          to="/" 
          style={({ isActive }) => ({
            display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', 
            borderRadius: '8px', textDecoration: 'none',
            background: isActive ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
            color: isActive ? 'var(--accent-primary)' : 'var(--text-muted)',
            fontWeight: isActive ? 600 : 400,
            transition: 'all 0.2s'
          })}
        >
          <LayoutDashboard size={20} />
          <span>대시보드</span>
        </NavLink>
        
        <NavLink 
          to="/map" 
          style={({ isActive }) => ({
            display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', 
            borderRadius: '8px', textDecoration: 'none',
            background: isActive ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
            color: isActive ? 'var(--accent-primary)' : 'var(--text-muted)',
            fontWeight: isActive ? 600 : 400,
            transition: 'all 0.2s'
          })}
        >
          <Map size={20} />
          <span>실시간 지도</span>
        </NavLink>
        
        <NavLink 
          to="/logs" 
          style={({ isActive }) => ({
            display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', 
            borderRadius: '8px', textDecoration: 'none',
            background: isActive ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
            color: isActive ? 'var(--accent-primary)' : 'var(--text-muted)',
            fontWeight: isActive ? 600 : 400,
            transition: 'all 0.2s'
          })}
        >
          <List size={20} />
          <span>이벤트 로그</span>
        </NavLink>
        <NavLink 
          to="/policies" 
          style={({ isActive }) => ({
            display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', 
            borderRadius: '8px', textDecoration: 'none',
            background: isActive ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
            color: isActive ? 'var(--accent-primary)' : 'var(--text-muted)',
            fontWeight: isActive ? 600 : 400,
            transition: 'all 0.2s'
          })}
        >
          <ShieldAlert size={20} />
          <span>정책 설정</span>
        </NavLink>

        <NavLink 
          to="/emergencies" 
          style={({ isActive }) => ({
            display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', 
            borderRadius: '8px', textDecoration: 'none',
            background: isActive ? 'rgba(239, 68, 68, 0.1)' : 'transparent',
            color: isActive ? 'var(--accent-critical)' : 'var(--text-muted)',
            fontWeight: isActive ? 600 : 400,
            transition: 'all 0.2s'
          })}
        >
          <ShieldAlert size={20} />
          <span>응급 알림</span>
        </NavLink>
      </nav>
    </div>
  );
};
