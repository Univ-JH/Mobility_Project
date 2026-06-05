export const STATE_COLORS: Record<string, string> = {
  RUNNING_NORMAL: 'var(--accent-success)',
  RUNNING_LIMITED: '#eab308',
  AUTO_BRAKING: '#f97316',
  EMERGENCY: 'var(--accent-critical)',
  IDLE: 'var(--text-muted)',
  READY: 'var(--text-muted)',
};

export const STATE_BG_COLORS: Record<string, string> = {
  RUNNING_NORMAL: 'rgba(16, 185, 129, 0.13)',
  RUNNING_LIMITED: 'rgba(234, 179, 8, 0.13)',
  AUTO_BRAKING: 'rgba(249, 115, 22, 0.13)',
  EMERGENCY: 'rgba(239, 68, 68, 0.13)',
  IDLE: 'rgba(139, 155, 180, 0.13)',
  READY: 'rgba(139, 155, 180, 0.13)',
};
