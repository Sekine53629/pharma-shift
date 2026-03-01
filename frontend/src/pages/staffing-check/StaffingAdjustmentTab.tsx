import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useApi } from '../../hooks/useApi';
import {
  bulkUpsertStaffingAdjustments,
  fetchDailyOverrides,
  fetchStaffingAdjustments,
  fetchStores,
  fetchWeeklySchedules,
  removeDailyOverride,
  bulkUpsertDailyOverrides,
} from '../../api/endpoints';
import type {
  DailyScheduleOverride,
  PaginatedResponse,
  ShiftPeriod,
  StaffingAdjustment,
  Store,
  StoreWeeklySchedule,
} from '../../types/models';
import { generateDateRange, jsDayToPythonWeekday } from './utils';
import WeeklySchedulePanel from './WeeklySchedulePanel';

interface Props {
  periodId: string;
  period: ShiftPeriod | null;
}

const DAYS = ['日', '月', '火', '水', '木', '金', '土'];

interface ScheduleInfo {
  is_open: boolean;
  staffing_delta: number;
  open_time: string;
  close_time: string;
}

const StaffingAdjustmentTab: React.FC<Props> = ({ periodId, period }) => {
  const [selectedStore, setSelectedStore] = useState<string>('');
  const [deltas, setDeltas] = useState<Record<string, string>>({});
  const [dirty, setDirty] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null);

  // Weekly schedules: python weekday (0=Mon..6=Sun) -> ScheduleInfo
  const [weeklyMap, setWeeklyMap] = useState<Record<number, ScheduleInfo>>({});
  // Daily overrides: date string -> DailyScheduleOverride
  const [overrideMap, setOverrideMap] = useState<Record<string, DailyScheduleOverride>>({});
  const [scheduleVersion, setScheduleVersion] = useState(0);

  const {
    data: storeData,
    refetch: refetchStores,
  } = useApi<PaginatedResponse<Store>>(
    () => fetchStores({ page_size: '200' }),
    [],
  );

  const adjParams = useMemo(() => {
    const p: Record<string, string> = { shift_period: periodId, page_size: '500' };
    if (selectedStore) p.store = selectedStore;
    return p;
  }, [periodId, selectedStore]);

  const { data: adjData, loading, refetch } = useApi<PaginatedResponse<StaffingAdjustment>>(
    () => fetchStaffingAdjustments(adjParams),
    [periodId, selectedStore],
  );

  const stores = storeData?.results ?? [];
  const currentStore = stores.find((s) => String(s.id) === selectedStore);
  const adjustments = adjData?.results ?? [];

  // Load weekly schedules + daily overrides
  useEffect(() => {
    if (!selectedStore) {
      setWeeklyMap({});
      setOverrideMap({});
      return;
    }
    let cancelled = false;
    const load = async () => {
      try {
        const [wsRes, doRes] = await Promise.all([
          fetchWeeklySchedules({ store: selectedStore, page_size: '10' }),
          fetchDailyOverrides({ store: selectedStore, page_size: '500' }),
        ]);
        if (!cancelled) {
          const wm: Record<number, ScheduleInfo> = {};
          for (const s of wsRes.data.results as StoreWeeklySchedule[]) {
            wm[s.day_of_week] = {
              is_open: s.is_open,
              staffing_delta: parseFloat(s.staffing_delta) || 0,
              open_time: s.open_time ?? '',
              close_time: s.close_time ?? '',
            };
          }
          setWeeklyMap(wm);

          const om: Record<string, DailyScheduleOverride> = {};
          for (const o of doRes.data.results as DailyScheduleOverride[]) {
            om[o.date] = o;
          }
          setOverrideMap(om);
        }
      } catch {
        if (!cancelled) {
          setWeeklyMap({});
          setOverrideMap({});
        }
      }
    };
    load();
    return () => { cancelled = true; };
  }, [selectedStore, scheduleVersion]);

  const dateRange = useMemo(() => {
    if (!period) return [];
    return generateDateRange(period.start_date, period.end_date);
  }, [period]);

  // Split adjustments by source
  const { manualIndex, modelIndex } = useMemo(() => {
    const manual: Record<string, StaffingAdjustment> = {};
    const model: Record<string, StaffingAdjustment> = {};
    for (const a of adjustments) {
      if (a.source === 'model') {
        model[a.date] = a;
      } else {
        manual[a.date] = a;
      }
    }
    return { manualIndex: manual, modelIndex: model };
  }, [adjustments]);

  useEffect(() => {
    const d: Record<string, string> = {};
    for (const entry of dateRange) {
      const adj = manualIndex[entry.date];
      d[entry.date] = adj ? adj.delta : '0';
    }
    setDeltas(d);
    setDirty(new Set());
    setMessage(null);
  }, [dateRange, manualIndex]);

  /**
   * Determine if a date is operating, considering:
   *  1. Daily override (highest priority)
   *  2. Holiday + operates_on_holidays flag
   *  3. Weekly schedule
   *  4. Default: Mon-Sat open, Sun closed
   */
  const getOperatingStatus = useCallback(
    (date: string, dayOfWeek: number, isHoliday: boolean) => {
      const pyWeekday = jsDayToPythonWeekday(dayOfWeek);
      const override = overrideMap[date];
      const schedule = weeklyMap[pyWeekday];
      const operatesOnHolidays = currentStore?.operates_on_holidays ?? false;

      // 1. Daily override takes priority
      if (override) {
        return {
          isOpen: override.is_open,
          source: override.is_open ? '臨時営業' : '臨時休業',
          hasOverride: true,
          note: override.note,
        };
      }

      // 2. Holiday check (only if not overridden)
      if (isHoliday && !operatesOnHolidays) {
        return { isOpen: false, source: '祝日休業', hasOverride: false, note: '' };
      }

      // 3. Weekly schedule
      if (schedule) {
        return {
          isOpen: schedule.is_open,
          source: schedule.is_open ? '営業' : '定休',
          hasOverride: false,
          note: '',
        };
      }

      // 4. Default
      const defaultOpen = dayOfWeek !== 0; // Sun = closed
      return {
        isOpen: defaultOpen,
        source: defaultOpen ? '営業' : '定休',
        hasOverride: false,
        note: '',
      };
    },
    [overrideMap, weeklyMap, currentStore],
  );

  const handleDeltaChange = useCallback((date: string, value: string) => {
    setDeltas((prev) => ({ ...prev, [date]: value }));
    setDirty((prev) => {
      const next = new Set(prev);
      next.add(date);
      return next;
    });
    setMessage(null);
  }, []);

  const handleSave = async () => {
    if (!selectedStore || dirty.size === 0) return;
    setSaving(true);
    setMessage(null);
    try {
      const items = Array.from(dirty).map((date) => ({
        store_id: Number(selectedStore),
        date,
        delta: deltas[date] || '0',
      }));
      const res = await bulkUpsertStaffingAdjustments(Number(periodId), items);
      const { created, updated } = res.data;
      setMessage({ text: `保存しました（新規: ${created}件, 更新: ${updated}件）`, isError: false });
      setDirty(new Set());
      refetch();
    } catch {
      setMessage({ text: '保存に失敗しました', isError: true });
    } finally {
      setSaving(false);
    }
  };

  const handleToggleOverride = async (date: string, currentlyOpen: boolean, hasOverride: boolean) => {
    if (!selectedStore) return;
    const storeId = Number(selectedStore);
    try {
      if (hasOverride) {
        // Remove override → revert to weekly schedule
        await removeDailyOverride(storeId, date);
      } else {
        // Create override → toggle open/close
        await bulkUpsertDailyOverrides(storeId, [
          { date, is_open: !currentlyOpen, note: !currentlyOpen ? '臨時営業' : '臨時休業' },
        ]);
      }
      setScheduleVersion((v) => v + 1);
    } catch {
      setMessage({ text: '営業日変更に失敗しました', isError: true });
    }
  };

  const handleScheduleSaved = useCallback(() => {
    setScheduleVersion((v) => v + 1);
    refetchStores();
    refetch();
  }, [refetch, refetchStores]);

  const minPharmacists = currentStore?.min_pharmacists ?? 0;

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
              基本必要薬剤師数: <strong>{minPharmacists}</strong>
            </span>
          </div>
        )}

        {selectedStore && dirty.size > 0 && (
          <button
            onClick={handleSave}
            disabled={saving}
            style={{ ...styles.saveBtn, opacity: saving ? 0.6 : 1 }}
          >
            {saving ? '保存中...' : `手動調整を保存（${dirty.size}件）`}
          </button>
        )}

        {message && (
          <span style={{ fontSize: 13, color: message.isError ? '#e94560' : '#27ae60' }}>
            {message.text}
          </span>
        )}
      </div>

      {!selectedStore && (
        <p style={{ color: '#999', textAlign: 'center', marginTop: 40 }}>
          店舗を選択してください
        </p>
      )}

      {selectedStore && currentStore && (
        <WeeklySchedulePanel
          store={currentStore}
          onSaved={handleScheduleSaved}
        />
      )}

      {selectedStore && loading && <p>Loading...</p>}

      {selectedStore && !loading && (
        <div style={styles.tableWrapper}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={{ ...styles.th, ...styles.stickyCol }}>日付</th>
                <th style={styles.th}>曜日</th>
                <th style={{ ...styles.th, minWidth: 80 }}>営業状態</th>
                <th style={styles.th}>基本</th>
                <th style={styles.th}>曜日調整</th>
                <th style={{ ...styles.th, background: '#e8f4fd' }}>モデル予測</th>
                <th style={{ ...styles.th, minWidth: 90 }}>手動調整</th>
                <th style={styles.th}>実効必要数</th>
              </tr>
            </thead>
            <tbody>
              {dateRange.map(({ date, dayOfWeek, isWeekend, isHoliday, holidayName }, rowIdx) => {
                const pyWeekday = jsDayToPythonWeekday(dayOfWeek);
                const status = getOperatingStatus(date, dayOfWeek, isHoliday);
                const schedule = weeklyMap[pyWeekday];
                const wdDelta = status.isOpen ? (schedule?.staffing_delta ?? 0) : 0;
                const modelAdj = modelIndex[date];
                const modelDelta = status.isOpen ? (parseFloat(modelAdj?.delta ?? '0') || 0) : 0;
                const deltaStr = deltas[date] ?? '0';
                const manualDelta = parseFloat(deltaStr) || 0;
                const effective = status.isOpen
                  ? Math.max(minPharmacists + wdDelta + modelDelta + manualDelta, 0)
                  : 0;
                const isDirtyCell = dirty.has(date);

                const rowBg = !status.isOpen
                  ? '#f5f5f5'
                  : rowIdx % 2 === 0
                  ? '#fff'
                  : '#f9f9f9';

                const formatDelta = (v: number) => {
                  const s = v % 1 === 0 ? String(v) : v.toFixed(1);
                  return v > 0 ? `+${s}` : s;
                };

                const holidayAnnotation = isHoliday ? ` (${holidayName})` : '';

                return (
                  <tr key={date} style={{ background: rowBg }}>
                    {/* 日付 */}
                    <td
                      style={{
                        ...styles.td,
                        ...styles.stickyCol,
                        fontWeight: 600,
                        color: isWeekend || isHoliday ? '#e94560' : '#333',
                        background: rowBg,
                      }}
                    >
                      {date}
                      {holidayAnnotation && (
                        <span style={{ fontSize: 10, color: '#e94560', marginLeft: 3 }}>
                          {holidayAnnotation}
                        </span>
                      )}
                    </td>

                    {/* 曜日 */}
                    <td style={{ ...styles.td, color: isWeekend || isHoliday ? '#e94560' : '#333' }}>
                      {DAYS[dayOfWeek]}
                    </td>

                    {/* 営業状態 */}
                    <td style={styles.td}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span
                          style={{
                            ...styles.statusBadge,
                            background: status.isOpen ? '#d4edda' : '#f8d7da',
                            color: status.isOpen ? '#155724' : '#721c24',
                          }}
                        >
                          {status.source}
                        </span>
                        <button
                          onClick={() => handleToggleOverride(date, status.isOpen, status.hasOverride)}
                          style={styles.overrideBtn}
                          title={status.hasOverride ? 'オーバーライドを解除' : '営業/休業を切替'}
                        >
                          {status.hasOverride ? '↩' : '⇄'}
                        </button>
                      </div>
                    </td>

                    {/* 基本 */}
                    <td style={{ ...styles.td, textAlign: 'center', color: status.isOpen ? '#333' : '#bbb' }}>
                      {status.isOpen ? minPharmacists : '—'}
                    </td>

                    {/* 曜日調整 */}
                    <td
                      style={{
                        ...styles.td,
                        textAlign: 'center',
                        color: !status.isOpen ? '#bbb' : wdDelta !== 0 ? '#1565c0' : '#999',
                        fontWeight: wdDelta !== 0 ? 600 : 400,
                      }}
                    >
                      {!status.isOpen ? '—' : wdDelta === 0 ? '—' : formatDelta(wdDelta)}
                    </td>

                    {/* モデル予測 */}
                    <td
                      style={{
                        ...styles.td,
                        textAlign: 'center',
                        background: status.isOpen && modelDelta !== 0 ? '#e8f4fd' : undefined,
                        color: !status.isOpen ? '#bbb' : modelDelta !== 0 ? '#0d47a1' : '#ccc',
                        fontWeight: modelDelta !== 0 ? 600 : 400,
                        fontSize: 12,
                      }}
                    >
                      {!status.isOpen ? '—' : modelDelta === 0 ? '—' : formatDelta(modelDelta)}
                    </td>

                    {/* 手動調整 */}
                    <td style={{ ...styles.td, background: !status.isOpen ? undefined : manualDelta > 0 ? '#e3f2fd' : manualDelta < 0 ? '#fce4ec' : undefined }}>
                      {status.isOpen ? (
                        <input
                          type="number"
                          step="0.5"
                          min="-5"
                          max="5"
                          value={deltaStr}
                          onChange={(e) => handleDeltaChange(date, e.target.value)}
                          style={{
                            ...styles.input,
                            borderColor: isDirtyCell ? '#2196f3' : '#ddd',
                          }}
                        />
                      ) : (
                        <span style={{ color: '#bbb', fontSize: 12 }}>—</span>
                      )}
                    </td>

                    {/* 実効必要数 */}
                    <td
                      style={{
                        ...styles.td,
                        textAlign: 'center',
                        fontWeight: 700,
                        color: !status.isOpen
                          ? '#999'
                          : effective < minPharmacists
                          ? '#e94560'
                          : '#333',
                        fontStyle: !status.isOpen ? 'italic' : undefined,
                      }}
                    >
                      {!status.isOpen
                        ? '休業'
                        : effective % 1 === 0
                        ? effective
                        : effective.toFixed(1)}
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
  saveBtn: {
    padding: '8px 16px',
    background: '#0f3460',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    fontSize: 14,
    cursor: 'pointer',
    fontWeight: 600,
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
    minWidth: 780,
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
  input: {
    width: 70,
    padding: '4px 6px',
    border: '1px solid #ddd',
    borderRadius: 4,
    fontSize: 13,
    textAlign: 'center',
  },
  statusBadge: {
    display: 'inline-block',
    padding: '1px 6px',
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 600,
    whiteSpace: 'nowrap',
  },
  overrideBtn: {
    background: 'none',
    border: '1px solid #ccc',
    borderRadius: 3,
    padding: '0 4px',
    fontSize: 12,
    cursor: 'pointer',
    color: '#666',
    lineHeight: '18px',
  },
};

export default StaffingAdjustmentTab;
