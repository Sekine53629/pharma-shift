import React, { useMemo, useState } from 'react';
import StatusBadge from '../../components/common/StatusBadge';
import { useApi } from '../../hooks/useApi';
import { fetchShifts, fetchStaffMembers } from '../../api/endpoints';
import type { PaginatedResponse, Shift, ShiftPeriod, Staff } from '../../types/models';
import { generateDateRange } from './utils';

interface Props {
  periodId: string;
  period: ShiftPeriod | null;
}

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const PersonalShiftTab: React.FC<Props> = ({ periodId, period }) => {
  const [selectedStaff, setSelectedStaff] = useState<string>('');

  const { data: staffData } = useApi<PaginatedResponse<Staff>>(
    () => fetchStaffMembers({ page_size: '200', is_active: 'true' }),
    [],
  );

  const shiftParams = useMemo(() => {
    const p: Record<string, string> = { shift_period: periodId, page_size: '200' };
    if (selectedStaff) p.staff = selectedStaff;
    return p;
  }, [periodId, selectedStaff]);

  const { data: shiftData, loading } = useApi<PaginatedResponse<Shift>>(
    () => fetchShifts(shiftParams),
    [periodId, selectedStaff],
  );

  const shifts = shiftData?.results ?? [];
  const staffList = staffData?.results ?? [];
  const currentStaff = staffList.find((s) => String(s.id) === selectedStaff);

  const dateRange = useMemo(() => {
    if (!period) return [];
    return generateDateRange(period.start_date, period.end_date);
  }, [period]);

  // Shift lookup by date
  const shiftByDate = useMemo(() => {
    const map: Record<string, Shift[]> = {};
    for (const s of shifts) {
      if (!map[s.date]) map[s.date] = [];
      map[s.date].push(s);
    }
    return map;
  }, [shifts]);

  // Summary calculations
  const summary = useMemo(() => {
    const workDays = shifts.filter((s) => !s.leave_type).length;
    const leaveDays: Record<string, number> = {};
    for (const s of shifts) {
      if (s.leave_type) {
        leaveDays[s.leave_type] = (leaveDays[s.leave_type] || 0) + 1;
      }
    }
    const totalLeave = Object.values(leaveDays).reduce((a, b) => a + b, 0);
    const monthlyDays = currentStaff?.effective_monthly_working_days ?? dateRange.length;
    const remaining = monthlyDays - workDays - totalLeave;
    const confirmed = shifts.filter((s) => s.is_confirmed).length;

    return { workDays, leaveDays, totalLeave, remaining, confirmed, total: shifts.length, monthlyDays };
  }, [shifts, currentStaff, dateRange.length]);

  return (
    <div>
      <div style={styles.controls}>
        <select
          value={selectedStaff}
          onChange={(e) => setSelectedStaff(e.target.value)}
          style={styles.select}
        >
          <option value="">-- スタッフ選択 --</option>
          {staffList.map((s) => (
            <option key={s.id} value={String(s.id)}>
              {s.name} ({s.store_name ?? 'No store'})
            </option>
          ))}
        </select>
      </div>

      {!selectedStaff && (
        <p style={{ color: '#999', textAlign: 'center', marginTop: 40 }}>
          スタッフを選択してください
        </p>
      )}

      {selectedStaff && loading && <p>Loading...</p>}

      {selectedStaff && !loading && (
        <>
          {/* Summary Cards */}
          <div style={styles.cardRow}>
            <div style={styles.card}>
              <div style={styles.cardLabel}>出勤日数</div>
              <div style={styles.cardValue}>
                {summary.workDays} / {summary.monthlyDays}日
              </div>
            </div>
            <div style={styles.card}>
              <div style={styles.cardLabel}>休暇内訳</div>
              <div style={styles.cardValue}>
                {Object.keys(summary.leaveDays).length === 0
                  ? 'なし'
                  : Object.entries(summary.leaveDays)
                      .map(([type, count]) => `${type}: ${count}`)
                      .join(' / ')}
              </div>
            </div>
            <div style={styles.card}>
              <div style={styles.cardLabel}>残り出勤可能日数</div>
              <div style={{
                ...styles.cardValue,
                color: summary.remaining < 0 ? '#e94560' : '#333',
              }}>
                {summary.remaining}日
              </div>
            </div>
            <div style={styles.card}>
              <div style={styles.cardLabel}>確定率</div>
              <div style={styles.cardValue}>
                {summary.confirmed} / {summary.total}
              </div>
            </div>
          </div>

          {/* Day-by-day list */}
          <div style={styles.dayList}>
            {dateRange.map(({ date, dayOfWeek, isWeekend, isSunday, isHoliday, holidayName }) => {
              const dayShifts = shiftByDate[date] ?? [];
              const hasLeave = dayShifts.some((s) => s.leave_type);
              const annotation = isHoliday
                ? isSunday ? `日・祝(${holidayName})` : `祝(${holidayName})`
                : '';

              return (
                <div
                  key={date}
                  style={{
                    ...styles.dayCard,
                    borderLeftColor: isWeekend || isHoliday
                      ? '#e94560'
                      : hasLeave
                      ? '#f39c12'
                      : '#0f3460',
                  }}
                >
                  <div style={styles.dateHeader}>
                    <span style={styles.dateText}>{date}</span>
                    <span style={{ ...styles.dayLabel, color: isWeekend || isHoliday ? '#e94560' : '#666' }}>
                      {DAYS[dayOfWeek]}
                    </span>
                    {annotation && (
                      <span style={styles.closedBadge}>{annotation}</span>
                    )}
                  </div>
                  {dayShifts.length === 0 ? (
                    <span style={styles.noShift}>—</span>
                  ) : (
                    dayShifts.map((s) => (
                      <div key={s.id} style={styles.shiftRow}>
                        <span style={styles.storeName}>
                          {s.leave_type ? `休暇 (${s.leave_type})` : s.store_name ?? '—'}
                        </span>
                        <span style={styles.shiftType}>{s.shift_type}</span>
                        {s.is_confirmed && <StatusBadge value="confirmed" label="Confirmed" />}
                      </div>
                    ))
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  controls: {
    marginBottom: 16,
  },
  select: {
    padding: '8px 12px',
    borderRadius: 6,
    border: '1px solid #ddd',
    fontSize: 14,
  },
  cardRow: {
    display: 'flex',
    gap: 12,
    marginBottom: 20,
    flexWrap: 'wrap',
  },
  card: {
    flex: '1 1 180px',
    background: '#fff',
    borderRadius: 8,
    padding: '16px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    minWidth: 160,
  },
  cardLabel: {
    fontSize: 12,
    color: '#888',
    marginBottom: 4,
  },
  cardValue: {
    fontSize: 20,
    fontWeight: 700,
    color: '#333',
  },
  dayList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  dayCard: {
    background: '#fff',
    borderRadius: 6,
    padding: '10px 16px',
    borderLeft: '4px solid #0f3460',
    boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
  },
  dateHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  dateText: { fontWeight: 600, fontSize: 14 },
  dayLabel: { fontSize: 12 },
  shiftRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '4px 0',
    fontSize: 13,
  },
  storeName: { color: '#555', flex: 1 },
  shiftType: { color: '#888', fontSize: 12 },
  noShift: { color: '#ccc', fontSize: 13 },
  closedBadge: {
    fontSize: 11,
    color: '#fff',
    background: '#bbb',
    padding: '1px 8px',
    borderRadius: 10,
    marginLeft: 4,
  },
};

export default PersonalShiftTab;
