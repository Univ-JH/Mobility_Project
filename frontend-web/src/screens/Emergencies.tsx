import React, { useState, useEffect } from 'react';
import { adminApi } from '../api/adminApi';
import { AlertOctagon, CheckCircle, ShieldAlert } from 'lucide-react';

export const Emergencies: React.FC = () => {
  const [emergencies, setEmergencies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchEmergencies = async () => {
    try {
      const res = await adminApi.getActiveEmergencies();
      setEmergencies(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmergencies();
    const interval = setInterval(fetchEmergencies, 5000); // Polling for new emergencies
    return () => clearInterval(interval);
  }, []);

  const handleAck = async (caseId: string) => {
    try {
      await adminApi.ackEmergency(caseId);
      fetchEmergencies();
    } catch (err) {
      alert('응급 알림 확인에 실패했습니다.');
    }
  };

  const handleResolve = async (caseId: string) => {
    const note = prompt('해결 내용을 입력하세요 (예: 사용자 연락 완료, 오작동 확인):');
    if (note === null) return;
    
    try {
      await adminApi.resolveEmergency(caseId, {
        resolutionType: 'OPERATOR_RESOLVED',
        note: note || '운영자 처리 완료'
      });
      fetchEmergencies();
    } catch (err) {
      alert('응급 알림 처리에 실패했습니다.');
    }
  };

  if (loading) return <div>응급 알림 로딩 중...</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <AlertOctagon size={28} color="var(--accent-critical)" />
        <h1 style={{ fontSize: '1.75rem', margin: 0 }}>활성 응급 알림</h1>
      </div>

      {emergencies.length === 0 ? (
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          <ShieldAlert size={48} style={{ opacity: 0.5, marginBottom: '1rem' }} />
          <h3>현재 발생한 응급 알림이 없습니다.</h3>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1rem' }}>
          {emergencies.map(em => (
            <div key={em.caseId} className="glass-panel" style={{ padding: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderLeft: `4px solid ${em.status === 'OPEN' ? 'var(--accent-critical)' : 'var(--accent-secondary)'}` }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
                  <span style={{ 
                    padding: '0.25rem 0.75rem', borderRadius: '12px', fontSize: '0.8rem', fontWeight: 'bold',
                    background: em.status === 'OPEN' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                    color: em.status === 'OPEN' ? 'var(--accent-critical)' : 'var(--accent-secondary)'
                  }}>
                    {em.status}
                  </span>
                  <span style={{ fontWeight: 600 }}>디바이스: {em.deviceId}</span>
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  발생 시각: {new Date(em.openedAt).toLocaleString('ko-KR')}
                </div>
              </div>
              
              <div style={{ display: 'flex', gap: '1rem' }}>
                {em.status === 'OPEN' && (
                  <button 
                    onClick={() => handleAck(em.caseId)}
                    style={{ padding: '0.75rem 1.5rem', borderRadius: '8px', border: '1px solid var(--accent-secondary)', background: 'transparent', color: 'var(--accent-secondary)', cursor: 'pointer', fontWeight: 600 }}
                  >
                    ACKNOWLEDGE
                  </button>
                )}
                <button 
                  onClick={() => handleResolve(em.caseId)}
                  style={{ padding: '0.75rem 1.5rem', borderRadius: '8px', border: 'none', background: 'var(--accent-success)', color: '#fff', cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                >
                  <CheckCircle size={18} />
                  RESOLVE
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
