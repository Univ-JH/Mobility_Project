import React, { useState, useEffect } from 'react';
import { adminApi } from '../api/adminApi';
import { Settings, Save, AlertCircle } from 'lucide-react';

export const Policies: React.FC = () => {
  const [policy, setPolicy] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [fetchError, setFetchError] = useState(false);

  useEffect(() => {
    const fetchPolicy = async () => {
      try {
        const res = await adminApi.getActivePolicy();
        setPolicy(res.data);
        setFetchError(false);
      } catch (err) {
        console.error('Failed to fetch policy', err);
        setFetchError(true);
      } finally {
        setLoading(false);
      }
    };
    fetchPolicy();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await adminApi.updatePolicy({
        name: policy.name || 'Admin Update',
        helmetRequired: policy.helmetRequired,
        maxSpeedKph: policy.maxSpeedKph,
        sidewalkBrakeLevel: policy.sidewalkBrakeLevel
      });
      setPolicy(res.data);
      alert('정책이 성공적으로 업데이트되었습니다.');
    } catch (err) {
      console.error(err);
      alert('정책 업데이트에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>로딩 중...</div>;

  if (fetchError) return (
    <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <span style={{ color: 'var(--accent-critical)', fontWeight: 600 }}>⚠ 정책 데이터를 불러올 수 없습니다</span>
      <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>서버 상태를 확인하거나 페이지를 새로고침하세요.</span>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <Settings size={28} color="var(--accent-primary)" />
        <h1 style={{ fontSize: '1.75rem', margin: 0 }}>안전 정책</h1>
      </div>

      <div className="glass-panel" style={{ padding: '2rem', maxWidth: '600px' }}>
        <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={20} color="var(--accent-secondary)" />
          활성 정책 설정
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>정책 이름</label>
            <input
              type="text"
              value={policy?.name || ''}
              onChange={e => setPolicy({...policy, name: e.target.value})}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--glass-border)', background: 'var(--bg-main)', color: 'var(--text-main)' }}
            />
          </div>

          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={policy?.helmetRequired || false}
                onChange={e => setPolicy({...policy, helmetRequired: e.target.checked})}
                style={{ width: '18px', height: '18px' }}
              />
              주행 시 헬멧 착용 필수
            </label>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>헬멧을 벗으면 디바이스가 잠깁니다.</p>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>최대 속도 제한 (km/h)</label>
            <input
              type="number"
              value={policy?.maxSpeedKph || 25}
              onChange={e => setPolicy({...policy, maxSpeedKph: parseFloat(e.target.value)})}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--glass-border)', background: 'var(--bg-main)', color: 'var(--text-main)' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>인도 자동 제동 레벨 (1-3)</label>
            <input
              type="number"
              min="1" max="3"
              value={policy?.sidewalkBrakeLevel || 2}
              onChange={e => setPolicy({...policy, sidewalkBrakeLevel: parseInt(e.target.value)})}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--glass-border)', background: 'var(--bg-main)', color: 'var(--text-main)' }}
            />
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              marginTop: '1rem', padding: '1rem', borderRadius: '8px', border: 'none',
              background: 'var(--accent-primary)', color: 'white', fontWeight: 600,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', cursor: 'pointer'
            }}
          >
            <Save size={20} />
            {saving ? '저장 중...' : '저장 및 정책 배포'}
          </button>
        </div>
      </div>
    </div>
  );
};
