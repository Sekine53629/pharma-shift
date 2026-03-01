import React, { useState } from 'react';
import DataTable from '../../components/common/DataTable';
import { useApi } from '../../hooks/useApi';
import { fetchBufferStaff, toggleRounder } from '../../api/endpoints';
import type { PaginatedResponse, Staff } from '../../types/models';
import CapabilityEditor from './CapabilityEditor';
import UnavailabilityManager from './UnavailabilityManager';

const EMP_LABELS: Record<string, string> = {
  full_time: 'Full-time',
  part_time: 'Part-time',
  dispatch: 'Dispatch',
};

const ClerkTab: React.FC = () => {
  const { data, loading, refetch } = useApi<PaginatedResponse<Staff>>(
    () => fetchBufferStaff({ page_size: '200' }),
    [],
  );

  const [expandedCap, setExpandedCap] = useState<number | null>(null);
  const [expandedUnavail, setExpandedUnavail] = useState<number | null>(null);

  const handleToggle = async (staffId: number) => {
    await toggleRounder(staffId);
    refetch();
  };

  const staff = (data?.results ?? []).filter((s) => s.role === 'clerk');

  const columns = [
    { key: 'name', header: 'Name' },
    {
      key: 'employment_type',
      header: 'Employment',
      render: (s: Staff) => EMP_LABELS[s.employment_type] || s.employment_type,
    },
    {
      key: 'store_name',
      header: 'Store',
      render: (s: Staff) => s.store_name || '(HQ)',
    },
    {
      key: 'is_rounder',
      header: 'Rounder',
      render: (s: Staff) => (
        <button
          onClick={() => handleToggle(s.id)}
          style={{
            ...styles.toggleBtn,
            background: s.is_rounder ? '#155724' : '#ccc',
          }}
        >
          {s.is_rounder ? 'ON' : 'OFF'}
        </button>
      ),
    },
    {
      key: 'capabilities',
      header: 'Capabilities',
      render: (s: Staff) =>
        s.is_rounder ? (
          <button
            onClick={() => setExpandedCap(expandedCap === s.id ? null : s.id)}
            style={styles.expandBtn}
          >
            {expandedCap === s.id ? 'Close' : 'Edit'}
          </button>
        ) : (
          <span style={{ color: '#999', fontSize: 12 }}>—</span>
        ),
    },
    {
      key: 'unavailability',
      header: 'Unavailability',
      render: (s: Staff) =>
        s.is_rounder && s.rounder_profile ? (
          <button
            onClick={() => setExpandedUnavail(expandedUnavail === s.id ? null : s.id)}
            style={styles.expandBtn}
          >
            {expandedUnavail === s.id ? 'Close' : 'Manage'}
          </button>
        ) : (
          <span style={{ color: '#999', fontSize: 12 }}>—</span>
        ),
    },
  ];

  return (
    <div>
      <DataTable columns={columns} data={staff} loading={loading} emptyMessage="No clerks found" />
      {staff.map((s) => (
        <React.Fragment key={s.id}>
          {expandedCap === s.id && s.is_rounder && (
            <div style={styles.expandPanel}>
              <div style={styles.panelLabel}>Capabilities: {s.name}</div>
              <CapabilityEditor staff={s} onUpdated={refetch} />
            </div>
          )}
          {expandedUnavail === s.id && s.is_rounder && s.rounder_profile && (
            <div style={styles.expandPanel}>
              <div style={styles.panelLabel}>Unavailability: {s.name}</div>
              <UnavailabilityManager rounderId={s.rounder_profile.id} />
            </div>
          )}
        </React.Fragment>
      ))}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  toggleBtn: {
    padding: '3px 12px',
    color: '#fff',
    border: 'none',
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
  },
  expandBtn: {
    padding: '3px 10px',
    background: '#e2e3e5',
    color: '#383d41',
    border: 'none',
    borderRadius: 4,
    fontSize: 12,
    cursor: 'pointer',
  },
  expandPanel: {
    margin: '0 0 8px',
    padding: 12,
    background: '#fff',
    border: '1px solid #dee2e6',
    borderRadius: 6,
  },
  panelLabel: {
    fontSize: 13,
    fontWeight: 600,
    marginBottom: 8,
    color: '#333',
  },
};

export default ClerkTab;
