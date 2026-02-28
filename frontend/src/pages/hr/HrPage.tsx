import React, { useState } from 'react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import { useApi } from '../../hooks/useApi';
import { fetchHrEvaluations, fetchHrSummaries } from '../../api/endpoints';
import type { HrEvaluation, HrPeriodSummary, PaginatedResponse } from '../../types/models';

function hrTier(hr: number): string {
  if (hr >= 81) return 'S';
  if (hr >= 61) return 'A';
  if (hr >= 41) return 'B';
  if (hr >= 21) return 'C';
  return 'D';
}

const HrPage: React.FC = () => {
  const [tab, setTab] = useState<'summaries' | 'evaluations'>('summaries');

  const { data: summaries, loading: sumLoading } =
    useApi<PaginatedResponse<HrPeriodSummary>>(() => fetchHrSummaries(), []);

  const { data: evals, loading: evalLoading } =
    useApi<PaginatedResponse<HrEvaluation>>(() => fetchHrEvaluations(), []);

  const summaryColumns = [
    { key: 'rounder_name', header: 'Rounder' },
    { key: 'period_start', header: 'Period Start' },
    { key: 'period_end', header: 'Period End' },
    {
      key: 'computed_hr',
      header: 'HR',
      render: (s: HrPeriodSummary) => {
        const hr = parseFloat(s.computed_hr);
        return (
          <span style={{ fontWeight: 700, fontSize: 16 }}>
            {s.computed_hr}
            <span style={styles.tier}>{hrTier(hr)}</span>
          </span>
        );
      },
    },
    { key: 'total_points', header: 'Total Points' },
    { key: 'supervisor_total', header: 'SV Eval' },
    { key: 'self_total', header: 'Self Eval' },
    { key: 'carried_over', header: 'Carried Over' },
  ];

  const evalColumns = [
    { key: 'rounder_name', header: 'Rounder' },
    { key: 'evaluator_name', header: 'Evaluator' },
    {
      key: 'score',
      header: 'Score',
      render: (e: HrEvaluation) => {
        const v = parseFloat(e.score);
        const color = v > 0 ? '#27ae60' : v < 0 ? '#e74c3c' : '#333';
        return <span style={{ fontWeight: 700, color }}>{e.score}</span>;
      },
    },
    {
      key: 'evaluation_type',
      header: 'Type',
      render: (e: HrEvaluation) => (e.evaluation_type === 'supervisor' ? 'Supervisor' : 'Self'),
    },
    { key: 'reason', header: 'Reason' },
    {
      key: 'requires_approval',
      header: 'Flag',
      render: (e: HrEvaluation) =>
        e.requires_approval ? <StatusBadge value="urgent" label="Needs Approval" /> : null,
    },
    { key: 'period_start', header: 'Period' },
  ];

  return (
    <div>
      <h1 style={styles.heading}>HR System (Hunter Rank)</h1>

      <div style={styles.tabs}>
        <button
          onClick={() => setTab('summaries')}
          style={{ ...styles.tab, ...(tab === 'summaries' ? styles.tabActive : {}) }}
        >
          HR Summaries
        </button>
        <button
          onClick={() => setTab('evaluations')}
          style={{ ...styles.tab, ...(tab === 'evaluations' ? styles.tabActive : {}) }}
        >
          Evaluations
        </button>
      </div>

      {tab === 'summaries' && (
        <DataTable columns={summaryColumns} data={summaries?.results ?? []} loading={sumLoading} />
      )}

      {tab === 'evaluations' && (
        <DataTable columns={evalColumns} data={evals?.results ?? []} loading={evalLoading} />
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
  tier: {
    marginLeft: 6,
    fontSize: 11,
    padding: '2px 6px',
    background: '#eee',
    borderRadius: 4,
    color: '#333',
    fontWeight: 600,
  },
};

export default HrPage;
