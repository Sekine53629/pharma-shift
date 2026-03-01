import React, { useState } from 'react';
import PharmacistTab from './PharmacistTab';
import ClerkTab from './ClerkTab';

type Tab = 'pharmacist' | 'clerk';

const BufferPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('pharmacist');

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.heading}>Buffer Management</h1>
      </div>
      <div style={styles.tabs}>
        <button
          onClick={() => setActiveTab('pharmacist')}
          style={{
            ...styles.tab,
            ...(activeTab === 'pharmacist' ? styles.activeTab : {}),
          }}
        >
          Pharmacists
        </button>
        <button
          onClick={() => setActiveTab('clerk')}
          style={{
            ...styles.tab,
            ...(activeTab === 'clerk' ? styles.activeTab : {}),
          }}
        >
          Clerks
        </button>
      </div>
      <div style={styles.content}>
        {activeTab === 'pharmacist' ? <PharmacistTab /> : <ClerkTab />}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  header: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 12,
    marginBottom: 16,
  },
  heading: { margin: 0, fontSize: 22 },
  tabs: {
    display: 'flex',
    gap: 0,
    borderBottom: '2px solid #dee2e6',
    marginBottom: 16,
  },
  tab: {
    padding: '8px 20px',
    background: 'transparent',
    border: 'none',
    borderBottom: '2px solid transparent',
    fontSize: 14,
    fontWeight: 500,
    color: '#666',
    cursor: 'pointer',
    marginBottom: -2,
  },
  activeTab: {
    color: '#0f3460',
    borderBottomColor: '#0f3460',
    fontWeight: 600,
  },
  content: {},
};

export default BufferPage;
