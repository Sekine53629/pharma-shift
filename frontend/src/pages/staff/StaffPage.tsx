import React from 'react';
import DataTable from '../../components/common/DataTable';
import { useApi } from '../../hooks/useApi';
import { fetchStaffMembers } from '../../api/endpoints';
import type { PaginatedResponse, Staff } from '../../types/models';

const ROLE_LABELS: Record<string, string> = {
  pharmacist: 'Pharmacist',
  clerk: 'Clerk',
  managing_pharmacist: 'Managing Pharmacist',
};

const EMP_LABELS: Record<string, string> = {
  full_time: 'Full-time',
  part_time: 'Part-time',
  dispatch: 'Dispatch',
};

const COLUMNS = [
  { key: 'name', header: 'Name' },
  {
    key: 'role',
    header: 'Role',
    render: (s: Staff) => ROLE_LABELS[s.role] || s.role,
  },
  {
    key: 'employment_type',
    header: 'Employment',
    render: (s: Staff) => EMP_LABELS[s.employment_type] || s.employment_type,
  },
  {
    key: 'store_name',
    header: 'Store',
    render: (s: Staff) => s.store_name || '(HQ / Rounder)',
  },
  {
    key: 'is_rounder',
    header: 'Rounder',
    render: (s: Staff) => s.is_rounder ? 'Yes' : '—',
  },
  {
    key: 'hr',
    header: 'HR',
    render: (s: Staff) => s.rounder_profile ? s.rounder_profile.hunter_rank : '—',
  },
  {
    key: 'paid_leave_used',
    header: 'PTO Used',
    render: (s: Staff) => `${s.paid_leave_used}/5`,
  },
];

const StaffPage: React.FC = () => {
  const { data, loading } = useApi<PaginatedResponse<Staff>>(
    () => fetchStaffMembers({ page_size: '100' }),
    [],
  );

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.heading}>Staff</h1>
        <span style={styles.count}>{data?.count ?? 0} members</span>
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

export default StaffPage;
