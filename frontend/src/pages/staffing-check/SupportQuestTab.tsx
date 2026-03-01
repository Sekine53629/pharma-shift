import React, { useMemo, useState } from 'react';
import StatusBadge from '../../components/common/StatusBadge';
import { useApi } from '../../hooks/useApi';
import { fetchAssignments, fetchRounders, fetchSupportSlots } from '../../api/endpoints';
import type {
  Assignment,
  PaginatedResponse,
  Rounder,
  ShiftPeriod,
  SupportSlot,
} from '../../types/models';
import { generateDateRange } from './utils';

interface Props {
  periodId: string;
  period: ShiftPeriod | null;
}

const PRIORITIES = [1, 2, 3, 4, 5];
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const SupportQuestTab: React.FC<Props> = ({ periodId, period }) => {
  const [enabledPriorities, setEnabledPriorities] = useState<Set<number>>(
    new Set(PRIORITIES),
  );

  const { data: slotData, loading: slotsLoading } = useApi<PaginatedResponse<SupportSlot>>(
    () => fetchSupportSlots({ shift_period: periodId, page_size: '200' }),
    [periodId],
  );

  const { data: assignData } = useApi<PaginatedResponse<Assignment>>(
    () => fetchAssignments({ page_size: '200' }),
    [],
  );

  const { data: rounderData } = useApi<PaginatedResponse<Rounder>>(
    () => fetchRounders({ page_size: '200' }),
    [],
  );

  const slots = slotData?.results ?? [];
  const assignments = assignData?.results ?? [];
  const rounders = rounderData?.results ?? [];

  // Filter by priority
  const filteredSlots = useMemo(
    () => slots.filter((s) => enabledPriorities.has(s.priority)),
    [slots, enabledPriorities],
  );

  // Assignment map: slotId -> confirmed assignment
  const assignBySlot = useMemo(() => {
    const map: Record<number, Assignment> = {};
    for (const a of assignments) {
      if (a.status === 'confirmed') {
        map[a.slot] = a;
      }
    }
    return map;
  }, [assignments]);

  // Rounder map: rounderId -> Rounder
  const rounderMap = useMemo(() => {
    const map: Record<number, Rounder> = {};
    for (const r of rounders) {
      map[r.id] = r;
    }
    return map;
  }, [rounders]);

  // Unique stores with slots
  const storeColumns = useMemo(() => {
    const storeMap = new Map<number, string>();
    for (const s of filteredSlots) {
      if (!storeMap.has(s.store)) {
        storeMap.set(s.store, s.store_name);
      }
    }
    return Array.from(storeMap.entries()).map(([id, name]) => ({ id, name }));
  }, [filteredSlots]);

  // Grid: date+storeId -> slot
  const slotGrid = useMemo(() => {
    const map: Record<string, SupportSlot> = {};
    for (const s of filteredSlots) {
      map[`${s.date}-${s.store}`] = s;
    }
    return map;
  }, [filteredSlots]);

  const dateRange = useMemo(() => {
    if (!period) return [];
    return generateDateRange(period.start_date, period.end_date);
  }, [period]);

  const togglePriority = (p: number) => {
    setEnabledPriorities((prev) => {
      const next = new Set(prev);
      if (next.has(p)) {
        next.delete(p);
      } else {
        next.add(p);
      }
      return next;
    });
  };

  if (slotsLoading) return <p>Loading...</p>;

  return (
    <div>
      {/* Priority filter */}
      <div style={styles.filterRow}>
        <span style={{ fontSize: 13, color: '#555', marginRight: 8 }}>優先度:</span>
        {PRIORITIES.map((p) => (
          <label key={p} style={styles.filterLabel}>
            <input
              type="checkbox"
              checked={enabledPriorities.has(p)}
              onChange={() => togglePriority(p)}
            />
            <StatusBadge value={`P${p}`} />
          </label>
        ))}
      </div>

      {storeColumns.length === 0 ? (
        <p style={{ color: '#999', textAlign: 'center', marginTop: 40 }}>
          該当する応援枠がありません
        </p>
      ) : (
        <div style={styles.tableWrapper}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={{ ...styles.th, ...styles.stickyCol }}>日付</th>
                {storeColumns.map((store) => (
                  <th key={store.id} style={styles.th}>
                    {store.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dateRange.map(({ date, dayOfWeek, isWeekend }, rowIdx) => {
                const hasAnySlot = storeColumns.some(
                  (store) => slotGrid[`${date}-${store.id}`],
                );
                if (!hasAnySlot) return null;

                return (
                  <tr
                    key={date}
                    style={{ background: rowIdx % 2 === 0 ? '#fff' : '#f9f9f9' }}
                  >
                    <td
                      style={{
                        ...styles.td,
                        ...styles.stickyCol,
                        fontWeight: 600,
                        color: isWeekend ? '#e94560' : '#333',
                        background: rowIdx % 2 === 0 ? '#fff' : '#f9f9f9',
                      }}
                    >
                      {date} ({DAYS[dayOfWeek]})
                    </td>
                    {storeColumns.map((store) => {
                      const slot = slotGrid[`${date}-${store.id}`];
                      if (!slot) {
                        return (
                          <td key={store.id} style={styles.td}>
                            <span style={{ color: '#ccc' }}>—</span>
                          </td>
                        );
                      }

                      const assign = assignBySlot[slot.id];
                      const isFilled = slot.is_filled && assign;
                      const rounder = assign ? rounderMap[assign.rounder] : null;
                      const hrMatch =
                        rounder && slot.required_hr
                          ? parseFloat(rounder.hunter_rank) >= parseFloat(slot.required_hr)
                          : true;

                      return (
                        <td
                          key={store.id}
                          style={{
                            ...styles.td,
                            background: isFilled ? '#d4edda' : '#fff3cd',
                          }}
                        >
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                              <StatusBadge value={`P${slot.priority}`} />
                              <span style={{ fontSize: 11, color: '#666' }}>
                                HR:{slot.effective_difficulty_hr ?? '—'}
                              </span>
                            </div>
                            {isFilled ? (
                              <div style={{ fontSize: 12 }}>
                                <span style={{ fontWeight: 500 }}>{assign.rounder_name}</span>
                                {!hrMatch && (
                                  <span style={styles.hrWarning}> HR不足</span>
                                )}
                              </div>
                            ) : (
                              <span style={styles.openLabel}>OPEN</span>
                            )}
                          </div>
                        </td>
                      );
                    })}
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
  filterRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
    flexWrap: 'wrap',
  },
  filterLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    cursor: 'pointer',
    fontSize: 13,
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
    minWidth: 400,
  },
  th: {
    padding: '8px 12px',
    background: '#f5f5f5',
    borderBottom: '2px solid #ddd',
    textAlign: 'left',
    fontSize: 12,
    fontWeight: 600,
    whiteSpace: 'nowrap',
  },
  td: {
    padding: '8px 12px',
    borderBottom: '1px solid #eee',
    verticalAlign: 'top',
    minWidth: 140,
  },
  stickyCol: {
    position: 'sticky',
    left: 0,
    zIndex: 1,
  },
  openLabel: {
    color: '#e94560',
    fontWeight: 700,
    fontSize: 12,
  },
  hrWarning: {
    color: '#e67e22',
    fontSize: 11,
    fontWeight: 600,
  },
};

export default SupportQuestTab;
