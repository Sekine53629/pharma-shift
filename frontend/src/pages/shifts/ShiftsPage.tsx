import React, { useMemo, useState } from 'react';
import StatusBadge from '../../components/common/StatusBadge';
import { useApi } from '../../hooks/useApi';
import {
  fetchShifts,
  fetchShiftPeriods,
  fetchStaffMembers,
  deleteShift,
} from '../../api/endpoints';
import { parseApiError } from '../../api/parseApiError';
import type { PaginatedResponse, Shift, ShiftPeriod, Staff } from '../../types/models';
import ShiftForm from './ShiftForm';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const ShiftsPage: React.FC = () => {
  const { data: periods } = useApi<PaginatedResponse<ShiftPeriod>>(
    () => fetchShiftPeriods(),
    [],
  );

  const { data: staffData } = useApi<PaginatedResponse<Staff>>(
    () => fetchStaffMembers({ page_size: '200' }),
    [],
  );

  const [selectedPeriod, setSelectedPeriod] = useState<string>('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [addForDate, setAddForDate] = useState<string | null>(null);

  const params = useMemo(() => {
    const p: Record<string, string> = { page_size: '500' };
    if (selectedPeriod) p.shift_period = selectedPeriod;
    return p;
  }, [selectedPeriod]);

  const { data: shifts, loading, refetch } = useApi<PaginatedResponse<Shift>>(
    () => fetchShifts(params),
    [selectedPeriod],
  );

  const staffList = staffData?.results ?? [];
  const periodList = periods?.results ?? [];

  // Group shifts by date
  const shiftsByDate = useMemo(() => {
    const map: Record<string, Shift[]> = {};
    for (const s of shifts?.results ?? []) {
      if (!map[s.date]) map[s.date] = [];
      map[s.date].push(s);
    }
    return map;
  }, [shifts]);

  const sortedDates = Object.keys(shiftsByDate).sort();

  const handleDelete = async (id: number) => {
    if (!window.confirm('Delete this shift?')) return;
    try {
      await deleteShift(id);
      refetch();
    } catch (err) {
      alert(parseApiError(err));
    }
  };

  const handleSaved = () => {
    setShowCreateForm(false);
    setEditingId(null);
    setAddForDate(null);
    refetch();
  };

  const handleCancel = () => {
    setShowCreateForm(false);
    setEditingId(null);
    setAddForDate(null);
  };

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.heading}>Shifts</h1>
        <select
          value={selectedPeriod}
          onChange={(e) => setSelectedPeriod(e.target.value)}
          style={styles.select}
        >
          <option value="">All Periods</option>
          {periodList.map((p) => (
            <option key={p.id} value={String(p.id)}>
              {p.start_date} ~ {p.end_date}
              {p.is_finalized ? ' (Finalized)' : ''}
            </option>
          ))}
        </select>
        <button
          style={styles.addBtn}
          onClick={() => {
            setShowCreateForm(!showCreateForm);
            setEditingId(null);
            setAddForDate(null);
          }}
        >
          {showCreateForm ? 'Cancel' : '+ Add Shift'}
        </button>
      </div>

      {showCreateForm && (
        <ShiftForm
          staffList={staffList}
          periods={periodList}
          selectedPeriodId={selectedPeriod}
          onSaved={handleSaved}
          onCancel={handleCancel}
        />
      )}

      {loading && <p>Loading...</p>}

      <div style={styles.calendar}>
        {sortedDates.map((date) => {
          const d = new Date(date + 'T00:00:00');
          const dayName = DAYS[d.getDay()];
          const isWeekend = d.getDay() === 0 || d.getDay() === 6;

          return (
            <div
              key={date}
              style={{
                ...styles.dayCard,
                borderLeftColor: isWeekend ? '#e94560' : '#0f3460',
              }}
            >
              <div style={styles.dateHeader}>
                <span style={styles.dateText}>{date}</span>
                <span style={{ ...styles.dayLabel, color: isWeekend ? '#e94560' : '#666' }}>
                  {dayName}
                </span>
                <button
                  style={styles.dayAddBtn}
                  onClick={() => {
                    setAddForDate(addForDate === date ? null : date);
                    setEditingId(null);
                    setShowCreateForm(false);
                  }}
                  title="Add shift for this date"
                >
                  +
                </button>
              </div>

              {addForDate === date && (
                <div style={{ marginBottom: 8 }}>
                  <ShiftForm
                    staffList={staffList}
                    periods={periodList}
                    selectedPeriodId={selectedPeriod}
                    defaultDate={date}
                    onSaved={handleSaved}
                    onCancel={handleCancel}
                  />
                </div>
              )}

              <div style={styles.shiftList}>
                {shiftsByDate[date].map((s) => (
                  <React.Fragment key={s.id}>
                    <div style={styles.shiftRow}>
                      <span style={styles.staffName}>{s.staff_name}</span>
                      <span style={styles.storeName}>
                        {s.store_name || (s.leave_type ? `Leave (${s.leave_type})` : 'Off')}
                      </span>
                      <span style={styles.shiftType}>{s.shift_type}</span>
                      {s.is_confirmed && <StatusBadge value="confirmed" label="Confirmed" />}
                      <button
                        style={styles.rowBtn}
                        onClick={() => {
                          setEditingId(editingId === s.id ? null : s.id);
                          setAddForDate(null);
                          setShowCreateForm(false);
                        }}
                      >
                        {editingId === s.id ? 'Close' : 'Edit'}
                      </button>
                      <button
                        style={{ ...styles.rowBtn, color: '#dc3545' }}
                        onClick={() => handleDelete(s.id)}
                      >
                        Delete
                      </button>
                    </div>
                    {editingId === s.id && (
                      <div style={{ marginBottom: 8 }}>
                        <ShiftForm
                          shift={s}
                          staffList={staffList}
                          periods={periodList}
                          selectedPeriodId={selectedPeriod}
                          onSaved={handleSaved}
                          onCancel={handleCancel}
                        />
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {sortedDates.length === 0 && !loading && (
        <p style={{ color: '#999', textAlign: 'center', marginTop: 40 }}>
          No shifts for selected period
        </p>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  header: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 16,
    marginBottom: 20,
    flexWrap: 'wrap',
  },
  heading: { margin: 0, fontSize: 22 },
  select: {
    padding: '8px 12px',
    borderRadius: 6,
    border: '1px solid #ddd',
    fontSize: 14,
  },
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
  calendar: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  dayCard: {
    background: '#fff',
    borderRadius: 6,
    padding: '12px 16px',
    borderLeft: '4px solid #0f3460',
    boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
  },
  dateHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  dateText: { fontWeight: 600, fontSize: 14 },
  dayLabel: { fontSize: 12 },
  dayAddBtn: {
    marginLeft: 'auto',
    width: 24,
    height: 24,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#e2e3e5',
    border: 'none',
    borderRadius: 4,
    fontSize: 14,
    fontWeight: 700,
    cursor: 'pointer',
    color: '#383d41',
  },
  shiftList: { display: 'flex', flexDirection: 'column', gap: 4 },
  shiftRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '4px 0',
    fontSize: 13,
    borderTop: '1px solid #f5f5f5',
  },
  staffName: { fontWeight: 500, minWidth: 100 },
  storeName: { color: '#555', flex: 1 },
  shiftType: { color: '#888', fontSize: 12 },
  rowBtn: {
    padding: '2px 8px',
    background: 'none',
    border: '1px solid #dee2e6',
    borderRadius: 4,
    fontSize: 11,
    cursor: 'pointer',
    color: '#495057',
  },
};

export default ShiftsPage;
