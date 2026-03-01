import React, { useMemo, useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { fetchShifts, fetchStaffMembers, fetchStores } from '../../api/endpoints';
import type { PaginatedResponse, Shift, ShiftPeriod, Staff, Store } from '../../types/models';
import { generateDateRange, isPharmacistRole } from './utils';

interface Props {
  periodId: string;
  period: ShiftPeriod | null;
}

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const SUPPORT_COLS = 3;

const StoreStaffingTab: React.FC<Props> = ({ periodId, period }) => {
  const [selectedStore, setSelectedStore] = useState<string>('');

  const { data: storeData } = useApi<PaginatedResponse<Store>>(
    () => fetchStores({ page_size: '200' }),
    [],
  );

  const staffParams = useMemo(() => {
    const p: Record<string, string> = { page_size: '100', is_active: 'true' };
    if (selectedStore) p.store = selectedStore;
    return p;
  }, [selectedStore]);

  const { data: staffData } = useApi<PaginatedResponse<Staff>>(
    () => fetchStaffMembers(staffParams),
    [selectedStore],
  );

  const shiftParams = useMemo(() => {
    const p: Record<string, string> = { shift_period: periodId, page_size: '500' };
    if (selectedStore) p.store = selectedStore;
    return p;
  }, [periodId, selectedStore]);

  const { data: shiftData, loading } = useApi<PaginatedResponse<Shift>>(
    () => fetchShifts(shiftParams),
    [periodId, selectedStore],
  );

  const stores = storeData?.results ?? [];
  const homeStaff = useMemo(() => {
    const list = staffData?.results ?? [];
    return [...list].sort((a, b) => {
      const aMan = a.role === 'managing_pharmacist' ? 0 : 1;
      const bMan = b.role === 'managing_pharmacist' ? 0 : 1;
      return aMan - bMan;
    });
  }, [staffData]);
  const shifts = shiftData?.results ?? [];
  const currentStore = stores.find((s) => String(s.id) === selectedStore);

  const dateRange = useMemo(() => {
    if (!period) return [];
    return generateDateRange(period.start_date, period.end_date);
  }, [period]);

  // Index: staffId+date -> shift
  const shiftIndex = useMemo(() => {
    const map: Record<string, Shift> = {};
    for (const s of shifts) {
      map[`${s.staff}-${s.date}`] = s;
    }
    return map;
  }, [shifts]);

  // Find support staff (not home staff) per date
  const homeStaffIds = useMemo(() => new Set(homeStaff.map((s) => s.id)), [homeStaff]);

  const supportByDate = useMemo(() => {
    const map: Record<string, Shift[]> = {};
    for (const s of shifts) {
      if (!homeStaffIds.has(s.staff) && !s.leave_type) {
        if (!map[s.date]) map[s.date] = [];
        map[s.date].push(s);
      }
    }
    return map;
  }, [shifts, homeStaffIds]);

  // Count pharmacists per date
  const pharmacistCount = useMemo(() => {
    const countMap: Record<string, number> = {};
    for (const entry of dateRange) {
      let count = 0;
      // Home staff working at this store
      for (const staff of homeStaff) {
        if (!isPharmacistRole(staff.role)) continue;
        const shift = shiftIndex[`${staff.id}-${entry.date}`];
        if (shift && !shift.leave_type) count++;
      }
      // Support staff (already filtered to this store, non-leave)
      const support = supportByDate[entry.date] ?? [];
      // We count all support staff as pharmacists since they're rounders
      count += support.length;
      countMap[entry.date] = count;
    }
    return countMap;
  }, [dateRange, homeStaff, shiftIndex, supportByDate]);

  const renderCell = (shift: Shift | undefined): React.ReactNode => {
    if (!shift) return <span style={{ color: '#ccc' }}>—</span>;
    if (shift.leave_type) {
      return (
        <span style={{ color: '#f39c12', fontWeight: 500, fontSize: 12 }}>
          {shift.leave_type}
        </span>
      );
    }
    const label = shift.shift_type === 'full' ? '全日' : shift.shift_type === 'morning' ? 'AM' : 'PM';
    return (
      <span style={{ color: '#27ae60', fontWeight: 500, fontSize: 12 }}>
        {label}
      </span>
    );
  };

  return (
    <div>
      <div style={styles.controls}>
        <select
          value={selectedStore}
          onChange={(e) => setSelectedStore(e.target.value)}
          style={styles.select}
        >
          <option value="">-- 店舗選択 --</option>
          {stores.map((s) => (
            <option key={s.id} value={String(s.id)}>
              {s.name} ({s.area})
            </option>
          ))}
        </select>

        {currentStore && (
          <div style={styles.summary}>
            <span style={styles.summaryItem}>
              必要最低薬剤師数: <strong>{currentStore.min_pharmacists}</strong>
            </span>
            <span style={styles.summaryItem}>
              所属スタッフ数: <strong>{homeStaff.length}</strong>
            </span>
          </div>
        )}
      </div>

      {!selectedStore && (
        <p style={{ color: '#999', textAlign: 'center', marginTop: 40 }}>
          店舗を選択してください
        </p>
      )}

      {selectedStore && loading && <p>Loading...</p>}

      {selectedStore && !loading && (
        <div style={styles.tableWrapper}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={{ ...styles.th, ...styles.stickyCol }}>日付</th>
                {homeStaff.map((s) => (
                  <th key={s.id} style={styles.th}>
                    {s.name}
                    <br />
                    <span style={{ fontSize: 10, color: '#888', fontWeight: 400 }}>
                      {s.role === 'managing_pharmacist' ? '管薬' : s.role === 'pharmacist' ? '薬剤師' : '事務'}
                    </span>
                  </th>
                ))}
                {Array.from({ length: SUPPORT_COLS }, (_, i) => (
                  <th key={`sup-${i}`} style={{ ...styles.th, background: '#e8f4fd' }}>
                    応援{i + 1}
                  </th>
                ))}
                <th style={{ ...styles.th, background: '#e8f8e8' }}>薬剤師計</th>
              </tr>
            </thead>
            <tbody>
              {dateRange.map(({ date, dayOfWeek, isWeekend, isHoliday, holidayName }, rowIdx) => {
                const count = pharmacistCount[date] ?? 0;
                const isShortage = currentStore
                  ? count < currentStore.min_pharmacists
                  : false;
                const support = supportByDate[date] ?? [];

                const annotation = isHoliday ? ` 祝(${holidayName})` : '';

                return (
                  <tr
                    key={date}
                    style={{
                      background: isShortage
                        ? '#fce4ec'
                        : rowIdx % 2 === 0
                        ? '#fff'
                        : '#f9f9f9',
                    }}
                  >
                    <td
                      style={{
                        ...styles.td,
                        ...styles.stickyCol,
                        fontWeight: 600,
                        color: isWeekend || isHoliday ? '#e94560' : '#333',
                        background: isShortage
                          ? '#fce4ec'
                          : rowIdx % 2 === 0
                          ? '#fff'
                          : '#f9f9f9',
                        borderLeft: isShortage ? '4px solid #e94560' : undefined,
                      }}
                    >
                      {date} ({DAYS[dayOfWeek]})
                      {annotation && (
                        <span style={{ fontSize: 10, color: '#e94560' }}>{annotation}</span>
                      )}
                    </td>
                    {homeStaff.map((staff) => (
                      <td key={staff.id} style={styles.td}>
                        {renderCell(shiftIndex[`${staff.id}-${date}`])}
                      </td>
                    ))}
                    {Array.from({ length: SUPPORT_COLS }, (_, i) => {
                      const sup = support[i];
                      return (
                        <td key={`sup-${i}`} style={{ ...styles.td, background: sup ? '#e8f4fd' : undefined }}>
                          {sup ? (
                            <span style={{ fontSize: 12 }}>{sup.staff_name}</span>
                          ) : (
                            <span style={{ color: '#ccc' }}>—</span>
                          )}
                        </td>
                      );
                    })}
                    <td
                      style={{
                        ...styles.td,
                        fontWeight: 700,
                        color: isShortage ? '#e94560' : '#27ae60',
                        textAlign: 'center',
                      }}
                    >
                      {count}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  controls: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    marginBottom: 16,
    flexWrap: 'wrap',
  },
  select: {
    padding: '8px 12px',
    borderRadius: 6,
    border: '1px solid #ddd',
    fontSize: 14,
  },
  summary: {
    display: 'flex',
    gap: 16,
    fontSize: 14,
  },
  summaryItem: {
    color: '#555',
  },
  tableWrapper: {
    overflowX: 'auto',
    border: '1px solid #ddd',
    borderRadius: 6,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 13,
    minWidth: 600,
  },
  th: {
    padding: '8px 10px',
    background: '#f5f5f5',
    borderBottom: '2px solid #ddd',
    textAlign: 'left',
    fontSize: 12,
    fontWeight: 600,
    whiteSpace: 'nowrap',
  },
  td: {
    padding: '6px 10px',
    borderBottom: '1px solid #eee',
    whiteSpace: 'nowrap',
  },
  stickyCol: {
    position: 'sticky',
    left: 0,
    zIndex: 1,
  },
};

export default StoreStaffingTab;
