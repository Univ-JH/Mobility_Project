import React, { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { axiosInstance, setAdminToken } from '../api/axiosInstance';

interface Props {
  onLogin: () => void;
}

export const AdminLogin: React.FC<Props> = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await axiosInstance.post<any, { data: { accessToken: string; role: string } }>(
        '/auth/login',
        { email, password },
      );
      if (res.data.role !== 'admin') {
        setError('관리자 계정이 아닙니다.');
        return;
      }
      setAdminToken(res.data.accessToken);
      onLogin();
    } catch {
      setError('이메일 또는 비밀번호가 올바르지 않습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-main)',
    }}>
      <div style={{
        width: '100%', maxWidth: '400px', padding: '2.5rem',
        background: 'var(--bg-card)',
        border: 'var(--glass-border)',
        borderRadius: '16px',
        boxShadow: 'var(--glass-shadow)',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '2rem', gap: '0.75rem' }}>
          <ShieldCheck size={48} color="var(--accent-info)" />
          <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>관리자 로그인</h1>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.875rem' }}>Safe Mobility 관제 시스템</p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <input
            type="email"
            placeholder="이메일"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            style={{
              background: 'rgba(255,255,255,0.05)', border: 'var(--glass-border)',
              borderRadius: '8px', padding: '0.75rem 1rem',
              color: 'var(--text-main)', fontSize: '0.95rem', outline: 'none',
            }}
          />
          <input
            type="password"
            placeholder="비밀번호"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            style={{
              background: 'rgba(255,255,255,0.05)', border: 'var(--glass-border)',
              borderRadius: '8px', padding: '0.75rem 1rem',
              color: 'var(--text-main)', fontSize: '0.95rem', outline: 'none',
            }}
          />
          {error && (
            <p style={{ margin: 0, color: 'var(--accent-critical)', fontSize: '0.85rem', textAlign: 'center' }}>
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={loading}
            style={{
              background: 'var(--accent-info)', color: '#fff', border: 'none',
              borderRadius: '8px', padding: '0.875rem', fontWeight: 700,
              fontSize: '1rem', cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? '로그인 중...' : '로그인'}
          </button>
        </form>
      </div>
    </div>
  );
};
