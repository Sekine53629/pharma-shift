import React, { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import {
  createRounderUnavailability,
  deleteRounderUnavailability,
  fetchRounderUnavailabilities,
  fetchShiftPeriods,
} from '../../api/endpoints';
import type {
  PaginatedResponse,
  RounderUnavailability,
  ShiftPeriod,
} from '../../types/models';

interface Props {
  rounderId: number;
}

const UnavailabilityManager: React.FC<Props> = ({ rounderId }) => {
  const { data: unavailData, refetch } = useApi<PaginatedResponse<RounderUnavailability>>(
    () => fetchRounderUnavailabilities({ rounder: String(rounderId), page_size: '50' }),
    [rounderId],
  );
  const { data: periodsData } = useApi<PaginatedResponse<ShiftPeriod>>(
    () => fetchShiftPeriods({ page_size: '20' }),
    [],
  );

  const [selectedPeriod, setSelectedPeriod] = useState('');
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);

  const unavailabilities = unavailData?.results ?? [];
  const periods = periodsData?.results ?? [];
  const usedPeriodIds = new Set(unavailabilities.map((u) => u.shift_period));

  const handleAdd = async () => {
    if (!selectedPeriod) return;
    setSaving(true);
    try {
      await createRounderUnavailability({
        rounder: rounderId,
        shift_period: Number(selectedPeriod),
        reason,
      });
      setSelectedPeriod('');
      setReason('');
      refetch();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    await deleteRounderUnavailability(id);
    refetch();
  };

  return (
    <div style={styles.container}>
      {unavailabilities.length > 0 && (
        <div style={styles.list}>
          {unavailabilities.map((u) => {
            const period = periods.find((p) => p.id === u.shift_period);
            return (
              <div key={u.id} style={styles.item}>
                <span style={{ fontSize: 13 }}>
                  {period
                    ? `${period.start_date} ~ ${period.end_date}`
                    : `Period #${u.shift_period}`}
                </span>
                {u.reason && (
                  <span style={{ fontSize: 12, color: '#666' }}>({u.reason})</span>
                )}
                <button onClick={() => handleDelete(u.id)} style={styles.deleteBtn}>
                  Remove
                </button>
              </div>
            );
          })}
        </div>
      )}
      <div style={styles.addRow}>
        <select
          value={selectedPeriod}
          onChange={(e) => setSelectedPeriod(e.target.value)}
          style={styles.select}
        >
          <option value="">Select period...</option>
          {periods
            .filter((p) => !usedPeriodIds.has(p.id))
            .map((p) => (
              <option key={p.id} value={p.id}>
                {p.start_date} ~ {p.end_date}
              </option>
            ))}
        </select>
        <input
          placeholder="Reason (optional)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          style={styles.input}
        />
        <button onClick={handleAdd} disabled={!selectedPeriod || saving} style={styles.addBtn}>
          {saving ? '...' : 'Add'}
        </button>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '8px 16px',
    background: '#f8f9fa',
    borderRadius: 6,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  list: { display: 'flex', flexDirection: 'column', gap: 4 },
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '4px 0',
  },
  deleteBtn: {
    padding: '2px 8px',
    background: '#e94560',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    fontSize: 11,
    cursor: 'pointer',
    marginLeft: 'auto',
  },
  addRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  select: {
    padding: '4px 8px',
    border: '1px solid #ccc',
    borderRadius: 4,
    fontSize: 13,
  },
  input: {
    padding: '4px 8px',
    border: '1px solid #ccc',
    borderRadius: 4,
    fontSize: 13,
    flex: 1,
    minWidth: 120,
  },
  addBtn: {
    padding: '4px 16px',
    background: '#0f3460',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    fontSize: 13,
    cursor: 'pointer',
  },
};

export default UnavailabilityManager;
