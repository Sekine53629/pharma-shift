import React, { useMemo, useState } from 'react';
import StatusBadge from '../../components/common/StatusBadge';
import { useApi } from '../../hooks/useApi';
import { fetchShifts, fetchShiftPeriods } from '../../api/endpoints';
import type { PaginatedResponse, Shift, ShiftPeriod } from '../../types/models';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const ShiftsPage: React.FC = () => {
  const { data: periods } = useApi<PaginatedResponse<ShiftPeriod>>(
    () => fetchShiftPeriods(),
    [],
  );

  const [selectedPeriod, setSelectedPeriod] = useState<string>('');

  const params = useMemo(() => {
    const p: Record<string, string> = { page_size: '500' };
    if (selectedPeriod) p.shift_period = selectedPeriod;
    return p;
  }, [selectedPeriod]);

  const { data: shifts, loading } = useApi<PaginatedResponse<Shift>>(
    () => fetchShifts(params),
    [selectedPeriod],
  );

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
          {periods?.results.map((p) => (
            <option key={p.id} value={String(p.id)}>
              {p.start_date} ~ {p.end_date}
              {p.is_finalized ? ' (Finalized)' : ''}
            </option>
          ))}
        </select>
      </div>

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
              </div>
              <div style={styles.shiftList}>
                {shiftsByDate[date].map((s) => (
                  <div key={s.id} style={styles.shiftRow}>
                    <span style={styles.staffName}>{s.staff_name}</span>
                    <span style={styles.storeName}>
                      {s.store_name || (s.leave_type ? `Leave (${s.leave_type})` : 'Off')}
                    </span>
                    <span style={styles.shiftType}>{s.shift_type}</span>
                    {s.is_confirmed && <StatusBadge value="confirmed" label="Confirmed" />}
                  </div>
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
};

export default ShiftsPage;
