import React from 'react';

const COLORS: Record<string, { bg: string; fg: string }> = {
  // Assignment / leave status
  candidate: { bg: '#fff3cd', fg: '#856404' },
  confirmed: { bg: '#d4edda', fg: '#155724' },
  approved: { bg: '#d4edda', fg: '#155724' },
  rejected: { bg: '#f8d7da', fg: '#721c24' },
  pending: { bg: '#cce5ff', fg: '#004085' },
  // Priority
  P1: { bg: '#f8d7da', fg: '#721c24' },
  P2: { bg: '#fff3cd', fg: '#856404' },
  P3: { bg: '#cce5ff', fg: '#004085' },
  P4: { bg: '#d4edda', fg: '#155724' },
  P5: { bg: '#e2e3e5', fg: '#383d41' },
  // Alert levels
  overdue: { bg: '#f8d7da', fg: '#721c24' },
  urgent: { bg: '#fff3cd', fg: '#856404' },
  warning: { bg: '#cce5ff', fg: '#004085' },
};

interface Props {
  value: string;
  label?: string;
}

const StatusBadge: React.FC<Props> = ({ value, label }) => {
  const color = COLORS[value] || { bg: '#e2e3e5', fg: '#383d41' };
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '3px 10px',
        borderRadius: 12,
        fontSize: 12,
        fontWeight: 600,
        background: color.bg,
        color: color.fg,
      }}
    >
      {label || value}
    </span>
  );
};

export default StatusBadge;
