import React from 'react';
import DataTable from '../../components/common/DataTable';
import { useApi } from '../../hooks/useApi';
import { fetchStores } from '../../api/endpoints';
import type { PaginatedResponse, Store } from '../../types/models';

const COLUMNS = [
  { key: 'name', header: 'Store Name' },
  { key: 'area', header: 'Area' },
  { key: 'base_difficulty', header: 'Base Diff.' },
  {
    key: 'effective_difficulty',
    header: 'Eff. Diff.',
    render: (s: Store) => (
      <span style={{ fontWeight: 600, color: parseFloat(s.effective_difficulty) >= 4 ? '#c0392b' : '#333' }}>
        {s.effective_difficulty}
      </span>
    ),
  },
  { key: 'slots', header: 'Slots' },
  {
    key: 'flags',
    header: 'Flags',
    render: (s: Store) => {
      const flags: string[] = [];
      if (s.has_controlled_medical_device) flags.push('Medical Device');
      if (s.has_toxic_substances) flags.push('Toxic');
      if (s.has_workers_comp) flags.push('Workers Comp');
      if (s.has_auto_insurance) flags.push('Auto Ins.');
      if (s.has_special_public_expense) flags.push('Special Public');
      if (s.has_local_voucher) flags.push('Voucher');
      if (s.has_holiday_rules) flags.push('Holiday');
      return (
        <span style={{ fontSize: 12, color: '#666' }}>
          {flags.length > 0 ? flags.join(', ') : '—'}
        </span>
      );
    },
  },
  {
    key: 'is_active',
    header: 'Status',
    render: (s: Store) => (
      <span style={{ color: s.is_active ? '#27ae60' : '#999' }}>
        {s.is_active ? 'Active' : 'Inactive'}
      </span>
    ),
  },
];

const StoresPage: React.FC = () => {
  const { data, loading } = useApi<PaginatedResponse<Store>>(
    () => fetchStores({ page_size: '100' }),
    [],
  );

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.heading}>Stores</h1>
        <span style={styles.count}>{data?.count ?? 0} stores</span>
      </div>
      <DataTable columns={COLUMNS} data={data?.results ?? []} loading={loading} />
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  header: { display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 16 },
  heading: { margin: 0, fontSize: 22 },
  count: { color: '#888', fontSize: 14 },
};

export default StoresPage;
