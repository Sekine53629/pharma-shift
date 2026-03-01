import React, { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { autoGenerateSupportSlots, fetchShiftPeriods } from '../../api/endpoints';
import type { PaginatedResponse, ShiftPeriod } from '../../types/models';
import StaffingAdjustmentTab from './StaffingAdjustmentTab';
import StoreStaffingTab from './StoreStaffingTab';
import SupportQuestTab from './SupportQuestTab';
import PersonalShiftTab from './PersonalShiftTab';

const TABS = [
  { key: 'adjustment', label: '人工調整' },
  { key: 'store', label: '店舗別工数' },
  { key: 'quest', label: '応援一覧' },
  { key: 'personal', label: '個人シフト' },
] as const;

type TabKey = typeof TABS[number]['key'];

const StaffingCheckPage: React.FC = () => {
  const [tab, setTab] = useState<TabKey>('store');
  const [selectedPeriod, setSelectedPeriod] = useState<string>('');
  const [generating, setGenerating] = useState(false);
  const [genResult, setGenResult] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const { data: periods } = useApi<PaginatedResponse<ShiftPeriod>>(
    () => fetchShiftPeriods(),
    [],
  );

  const currentPeriod = periods?.results.find((p) => String(p.id) === selectedPeriod);

  const handleAutoGenerate = async () => {
    if (!selectedPeriod) return;
    setGenerating(true);
    setGenResult(null);
    try {
      const res = await autoGenerateSupportSlots(Number(selectedPeriod));
      const count = res.data.created;
      setGenResult(count > 0 ? `${count}件の応援枠を生成しました` : '新規生成対象はありません（既存枠あり）');
      // Switch to quest tab and force refresh
      setRefreshKey((k) => k + 1);
      if (count > 0) setTab('quest');
    } catch {
      setGenResult('生成に失敗しました');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.heading}>Staffing Check</h1>
        <select
          value={selectedPeriod}
          onChange={(e) => setSelectedPeriod(e.target.value)}
          style={styles.select}
        >
          <option value="">-- Select Period --</option>
          {periods?.results.map((p) => (
            <option key={p.id} value={String(p.id)}>
              {p.start_date} ~ {p.end_date}
              {p.is_finalized ? ' (Finalized)' : ''}
            </option>
          ))}
        </select>

        {selectedPeriod && (
          <button
            onClick={handleAutoGenerate}
            disabled={generating}
            style={{
              ...styles.generateBtn,
              opacity: generating ? 0.6 : 1,
            }}
          >
            {generating ? '生成中...' : '手配（応援枠一括生成）'}
          </button>
        )}

        {genResult && (
          <span style={{ fontSize: 13, color: genResult.includes('失敗') ? '#e94560' : '#27ae60' }}>
            {genResult}
          </span>
        )}
      </div>

      <div style={styles.tabs}>
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{ ...styles.tab, ...(tab === t.key ? styles.tabActive : {}) }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {!selectedPeriod && (
        <p style={{ color: '#999', textAlign: 'center', marginTop: 40 }}>
          シフト期間を選択してください
        </p>
      )}

      {selectedPeriod && tab === 'adjustment' && (
        <StaffingAdjustmentTab periodId={selectedPeriod} period={currentPeriod ?? null} />
      )}
      {selectedPeriod && tab === 'store' && (
        <StoreStaffingTab periodId={selectedPeriod} period={currentPeriod ?? null} />
      )}
      {selectedPeriod && tab === 'quest' && (
        <SupportQuestTab key={refreshKey} periodId={selectedPeriod} period={currentPeriod ?? null} />
      )}
      {selectedPeriod && tab === 'personal' && (
        <PersonalShiftTab periodId={selectedPeriod} period={currentPeriod ?? null} />
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
  generateBtn: {
    padding: '8px 16px',
    background: '#e94560',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    fontSize: 14,
    cursor: 'pointer',
    fontWeight: 600,
  },
};

export default StaffingCheckPage;
