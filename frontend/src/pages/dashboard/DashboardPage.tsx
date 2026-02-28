import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import StatusBadge from '../../components/common/StatusBadge';
import { useApi } from '../../hooks/useApi';
import { fetchPaidLeaveAlerts, fetchSupportSlots } from '../../api/endpoints';
import type { PaidLeaveAlert, PaginatedResponse, SupportSlot } from '../../types/models';

const DashboardPage: React.FC = () => {
  const { user, hasAnyRole } = useAuth();

  const { data: alerts } = useApi<PaidLeaveAlert[]>(
    () => fetchPaidLeaveAlerts(),
    [],
  );

  const { data: unfilled } = useApi<PaginatedResponse<SupportSlot>>(
    () => fetchSupportSlots({ is_filled: 'false' }),
    [],
  );

  const showAdminWidgets = hasAnyRole('admin', 'supervisor');

  return (
    <div>
      <h1 style={styles.heading}>Dashboard</h1>
      <p style={styles.welcome}>Welcome, {user?.email}</p>

      <div style={styles.grid}>
        {/* Unfilled Support Slots */}
        {showAdminWidgets && (
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>Unfilled Support Slots</h3>
            {unfilled && unfilled.results.length > 0 ? (
              <ul style={styles.list}>
                {unfilled.results.slice(0, 10).map((slot) => (
                  <li key={slot.id} style={styles.listItem}>
                    <StatusBadge value={`P${slot.priority}`} />
                    <span style={{ marginLeft: 8 }}>
                      {slot.store_name} — {slot.date}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p style={styles.empty}>All slots filled</p>
            )}
            {unfilled && unfilled.count > 10 && (
              <p style={styles.more}>+{unfilled.count - 10} more</p>
            )}
          </div>
        )}

        {/* Paid Leave Alerts */}
        {showAdminWidgets && (
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>Paid Leave Alerts</h3>
            {alerts && alerts.length > 0 ? (
              <ul style={styles.list}>
                {alerts.map((a) => (
                  <li key={a.staff_id} style={styles.listItem}>
                    <StatusBadge value={a.level} label={a.level.toUpperCase()} />
                    <span style={{ marginLeft: 8 }}>
                      {a.staff_name} — {a.remaining_leave} days left (due {a.deadline})
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p style={styles.empty}>No alerts</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  heading: { margin: 0, fontSize: 22 },
  welcome: { color: '#666', marginBottom: 24 },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
    gap: 20,
  },
  card: {
    background: '#fff',
    borderRadius: 8,
    padding: 20,
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  cardTitle: { margin: '0 0 12px', fontSize: 16 },
  list: { listStyle: 'none', padding: 0, margin: 0 },
  listItem: {
    padding: '8px 0',
    borderBottom: '1px solid #f0f0f0',
    display: 'flex',
    alignItems: 'center',
    fontSize: 14,
  },
  empty: { color: '#999', fontSize: 14 },
  more: { color: '#666', fontSize: 13, marginTop: 8 },
};

export default DashboardPage;
