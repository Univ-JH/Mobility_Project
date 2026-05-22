import React from 'react';
import { Activity, AlertTriangle, Battery, ShieldCheck } from 'lucide-react';
import { useDashboardStats, useAlertsTimeline, useEnvironmentStats } from '../hooks/queries/useAdminQueries';
import { StatCard } from '../components/common/StatCard';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

export const Dashboard: React.FC = () => {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: timeline } = useAlertsTimeline();
  const { data: envStats } = useEnvironmentStats();

  if (statsLoading) return <div>Loading dashboard data...</div>;

  const pieData = envStats ? [
    { name: 'Sidewalk', value: envStats.sidewalkRatio },
    { name: 'Road', value: envStats.roadRatio }
  ] : [];
  
  const PIE_COLORS = ['#ef4444', '#10b981']; // Red for sidewalk (danger), Green for road

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Top Stats Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem' }}>
        <StatCard 
          title="Active Devices" 
          value={stats?.activeDevices || 0} 
          icon={<Activity size={20} color="var(--accent-primary)" />} 
          trend="+12% today" isPositive={true}
        />
        <StatCard 
          title="Emergencies Today" 
          value={stats?.emergenciesToday || 0} 
          icon={<AlertTriangle size={20} color="var(--accent-critical)" />} 
        />
        <StatCard 
          title="Helmet Compliance" 
          value={`${(stats?.helmetCompliance || 0).toFixed(1)}%`} 
          icon={<ShieldCheck size={20} color="var(--accent-secondary)" />} 
        />
        <StatCard 
          title="Avg Battery" 
          value={`${(stats?.avgBattery || 0).toFixed(1)}%`} 
          icon={<Battery size={20} color="var(--accent-success)" />} 
        />
      </div>

      {/* Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', height: '400px' }}>
        {/* Timeline Chart */}
        <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginBottom: '1.5rem', fontSize: '1.1rem' }}>Alerts Timeline (24h)</h3>
          <div style={{ flex: 1, minHeight: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeline || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-primary)" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="var(--accent-primary)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-card)', border: 'var(--glass-border)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--text-main)' }}
                />
                <Area type="monotone" dataKey="count" stroke="var(--accent-primary)" fillOpacity={1} fill="url(#colorCount)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Environment Chart */}
        <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginBottom: '1.5rem', fontSize: '1.1rem' }}>Surface Environment</h3>
          <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData} innerRadius={60} outerRadius={90} paddingAngle={5}
                  dataKey="value" stroke="none"
                >
                  {pieData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: 'var(--bg-card)', border: 'var(--glass-border)', borderRadius: '8px' }} />
              </PieChart>
            </ResponsiveContainer>
            {/* Center Text */}
            <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
              <span style={{ display: 'block', fontSize: '1.5rem', fontWeight: 'bold' }}>
                {envStats ? (envStats.sidewalkRatio).toFixed(0) : 0}%
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--accent-critical)' }}>Sidewalk</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
