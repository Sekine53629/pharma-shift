import React, { useState } from 'react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import { useApi } from '../../hooks/useApi';
import {
  confirmAssignment,
  fetchAssignments,
  fetchSupportSlots,
  generateCandidates,
  rejectAssignment,
} from '../../api/endpoints';
import type { Assignment, PaginatedResponse, SupportSlot } from '../../types/models';

const AssignmentsPage: React.FC = () => {
  const [tab, setTab] = useState<'slots' | 'assignments'>('slots');

  const { data: slots, loading: slotsLoading, refetch: refetchSlots } =
    useApi<PaginatedResponse<SupportSlot>>(() => fetchSupportSlots(), []);

  const { data: assignments, loading: assignLoading, refetch: refetchAssign } =
    useApi<PaginatedResponse<Assignment>>(() => fetchAssignments(), []);

  const [generating, setGenerating] = useState<number | null>(null);

  const handleGenerate = async (slotId: number) => {
    setGenerating(slotId);
    try {
      await generateCandidates(slotId);
      refetchAssign();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to generate candidates');
    } finally {
      setGenerating(null);
    }
  };

  const handleConfirm = async (id: number) => {
    try {
      await confirmAssignment(id);
      refetchAssign();
      refetchSlots();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed');
    }
  };

  const handleReject = async (id: number) => {
    try {
      await rejectAssignment(id);
      refetchAssign();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed');
    }
  };

  const slotColumns = [
    {
      key: 'priority',
      header: 'Priority',
      render: (s: SupportSlot) => <StatusBadge value={`P${s.priority}`} />,
    },
    { key: 'store_name', header: 'Store' },
    { key: 'date', header: 'Date' },
    { key: 'effective_difficulty_hr', header: 'Difficulty (HR)' },
    {
      key: 'is_filled',
      header: 'Status',
      render: (s: SupportSlot) => (
        <StatusBadge
          value={s.is_filled ? 'confirmed' : 'pending'}
          label={s.is_filled ? 'Filled' : 'Open'}
        />
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (s: SupportSlot) =>
        !s.is_filled ? (
          <button
            onClick={() => handleGenerate(s.id)}
            disabled={generating === s.id}
            style={styles.btn}
          >
            {generating === s.id ? '...' : 'Generate'}
          </button>
        ) : null,
    },
  ];

  const assignColumns = [
    { key: 'rounder_name', header: 'Rounder' },
    {
      key: 'slot_info',
      header: 'Slot',
      render: (a: Assignment) =>
        `[P${a.slot_info.priority}] ${a.slot_info.store_name} ${a.slot_info.date}`,
    },
    {
      key: 'score',
      header: 'Score',
      render: (a: Assignment) => a.score ?? '—',
    },
    {
      key: 'status',
      header: 'Status',
      render: (a: Assignment) => <StatusBadge value={a.status} />,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (a: Assignment) =>
        a.status === 'candidate' ? (
          <span style={{ display: 'flex', gap: 6 }}>
            <button onClick={() => handleConfirm(a.id)} style={styles.btnConfirm}>
              Confirm
            </button>
            <button onClick={() => handleReject(a.id)} style={styles.btnReject}>
              Reject
            </button>
          </span>
        ) : null,
    },
  ];

  return (
    <div>
      <h1 style={styles.heading}>Assignments</h1>

      <div style={styles.tabs}>
        <button
          onClick={() => setTab('slots')}
          style={{ ...styles.tab, ...(tab === 'slots' ? styles.tabActive : {}) }}
        >
          Support Slots ({slots?.count ?? 0})
        </button>
        <button
          onClick={() => setTab('assignments')}
          style={{ ...styles.tab, ...(tab === 'assignments' ? styles.tabActive : {}) }}
        >
          Assignments ({assignments?.count ?? 0})
        </button>
      </div>

      {tab === 'slots' && (
        <DataTable columns={slotColumns} data={slots?.results ?? []} loading={slotsLoading} />
      )}

      {tab === 'assignments' && (
        <DataTable columns={assignColumns} data={assignments?.results ?? []} loading={assignLoading} />
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  heading: { margin: '0 0 16px', fontSize: 22 },
  tabs: { display: 'flex', gap: 0, marginBottom: 16 },
  tab: {
    padding: '10px 20px',
    border: '1px solid #ddd',
    background: '#fff',
    cursor: 'pointer',
    fontSize: 14,
  },
  tabActive: {
    background: '#0f3460',
    color: '#fff',
    borderColor: '#0f3460',
  },
  btn: {
    padding: '4px 12px',
    background: '#0f3460',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 12,
  },
  btnConfirm: {
    padding: '4px 10px',
    background: '#27ae60',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 12,
  },
  btnReject: {
    padding: '4px 10px',
    background: '#e74c3c',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 12,
  },
};

export default AssignmentsPage;
