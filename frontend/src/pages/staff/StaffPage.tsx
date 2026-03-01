import React, { useState } from 'react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import { useApi } from '../../hooks/useApi';
import { fetchStaffMembers, updateStaff } from '../../api/endpoints';
import { parseApiError } from '../../api/parseApiError';
import type { PaginatedResponse, Staff } from '../../types/models';
import StaffForm from './StaffForm';
import TransferForm from './TransferForm';

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

const WORK_STATUS_LABELS: Record<string, string> = {
  active: 'Active',
  on_leave: 'On Leave',
  maternity: 'Maternity',
  temporary: 'Temporary',
};

const StaffPage: React.FC = () => {
  const { data, loading, refetch } = useApi<PaginatedResponse<Staff>>(
    () => fetchStaffMembers({ page_size: '100' }),
    [],
  );

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [transferringId, setTransferringId] = useState<number | null>(null);

  const handleToggleActive = async (s: Staff) => {
    try {
      await updateStaff(s.id, { is_active: !s.is_active });
      refetch();
    } catch (err) {
      alert(parseApiError(err));
    }
  };

  const columns = [
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
      key: 'work_status',
      header: 'Status',
      render: (s: Staff) => (
        <StatusBadge value={s.work_status} label={WORK_STATUS_LABELS[s.work_status] || s.work_status} />
      ),
    },
    {
      key: 'store_name',
      header: 'Store',
      render: (s: Staff) => s.store_name || '(HQ / Rounder)',
    },
    {
      key: 'is_rounder',
      header: 'Rounder',
      render: (s: Staff) => (s.is_rounder ? 'Yes' : '—'),
    },
    {
      key: 'hr',
      header: 'HR',
      render: (s: Staff) => (s.rounder_profile ? s.rounder_profile.hunter_rank : '—'),
    },
    {
      key: 'paid_leave_used',
      header: 'PTO Used',
      render: (s: Staff) => `${s.paid_leave_used}/5`,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (s: Staff) => (
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            style={styles.actionBtn}
            onClick={() => {
              setEditingId(editingId === s.id ? null : s.id);
              setTransferringId(null);
            }}
          >
            {editingId === s.id ? 'Close' : 'Edit'}
          </button>
          <button
            style={{
              ...styles.actionBtn,
              background: transferringId === s.id ? '#cfe2ff' : '#e7f1ff',
              color: '#084298',
            }}
            onClick={() => {
              setTransferringId(transferringId === s.id ? null : s.id);
              setEditingId(null);
            }}
          >
            {transferringId === s.id ? 'Close' : 'Transfer'}
          </button>
          <button
            style={{
              ...styles.actionBtn,
              background: s.is_active ? '#fff3cd' : '#d4edda',
              color: s.is_active ? '#856404' : '#155724',
            }}
            onClick={() => handleToggleActive(s)}
          >
            {s.is_active ? 'Deactivate' : 'Activate'}
          </button>
        </div>
      ),
    },
  ];

  const staff = data?.results ?? [];

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.heading}>Staff</h1>
        <span style={styles.count}>{data?.count ?? 0} members</span>
        <button
          style={styles.addBtn}
          onClick={() => {
            setShowCreateForm(!showCreateForm);
            setEditingId(null);
          }}
        >
          {showCreateForm ? 'Cancel' : '+ Add Staff'}
        </button>
      </div>

      {showCreateForm && (
        <StaffForm
          onSaved={() => {
            setShowCreateForm(false);
            refetch();
          }}
          onCancel={() => setShowCreateForm(false)}
        />
      )}

      <DataTable columns={columns} data={staff} loading={loading} />

      {staff.map(
        (s) =>
          editingId === s.id && (
            <div key={`edit-${s.id}`} style={styles.editPanel}>
              <StaffForm
                staff={s}
                onSaved={() => {
                  setEditingId(null);
                  refetch();
                }}
                onCancel={() => setEditingId(null)}
              />
            </div>
          ),
      )}

      {staff.map(
        (s) =>
          transferringId === s.id && (
            <div key={`transfer-${s.id}`} style={styles.editPanel}>
              <TransferForm
                staff={s}
                onTransferred={() => {
                  setTransferringId(null);
                  refetch();
                }}
                onCancel={() => setTransferringId(null)}
              />
            </div>
          ),
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  header: { display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 16 },
  heading: { margin: 0, fontSize: 22 },
  count: { color: '#888', fontSize: 14 },
  addBtn: {
    marginLeft: 'auto',
    padding: '6px 14px',
    background: '#0d6efd',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    fontSize: 13,
    cursor: 'pointer',
  },
  actionBtn: {
    padding: '3px 10px',
    background: '#e2e3e5',
    color: '#383d41',
    border: 'none',
    borderRadius: 4,
    fontSize: 12,
    cursor: 'pointer',
  },
  editPanel: { marginBottom: 8 },
};

export default StaffPage;
