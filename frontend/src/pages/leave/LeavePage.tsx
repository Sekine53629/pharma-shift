import React, { useState } from 'react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import { useAuth } from '../../contexts/AuthContext';
import { useApi } from '../../hooks/useApi';
import {
  createLeaveRequest,
  fetchLeaveRequests,
  fetchPaidLeaveAlerts,
  reviewLeaveRequest,
} from '../../api/endpoints';
import type { LeaveRequest, PaginatedResponse, PaidLeaveAlert } from '../../types/models';

const LeavePage: React.FC = () => {
  const { user, hasAnyRole } = useAuth();
  const canReview = hasAnyRole('admin', 'supervisor', 'store_manager');

  const { data: requests, loading, refetch } =
    useApi<PaginatedResponse<LeaveRequest>>(() => fetchLeaveRequests(), []);

  const { data: alerts } =
    useApi<PaidLeaveAlert[]>(() => fetchPaidLeaveAlerts(), []);

  // New request form
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    staff: '',
    date: '',
    leave_type: 'paid',
    reason: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createLeaveRequest({
        staff: parseInt(formData.staff),
        date: formData.date,
        leave_type: formData.leave_type,
        reason: formData.reason,
      });
      setShowForm(false);
      setFormData({ staff: '', date: '', leave_type: 'paid', reason: '' });
      refetch();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit');
    }
  };

  const handleReview = async (id: number, status: string) => {
    const comment = prompt('Review comment (required):');
    if (!comment) return;
    try {
      await reviewLeaveRequest(id, status, comment);
      refetch();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed');
    }
  };

  const columns = [
    { key: 'staff_name', header: 'Staff' },
    { key: 'date', header: 'Date' },
    {
      key: 'leave_type_display',
      header: 'Type',
    },
    {
      key: 'status',
      header: 'Status',
      render: (r: LeaveRequest) => <StatusBadge value={r.status} label={r.status_display} />,
    },
    {
      key: 'is_late',
      header: 'Late',
      render: (r: LeaveRequest) =>
        r.is_late ? <StatusBadge value="urgent" label="Late" /> : null,
    },
    { key: 'reason', header: 'Reason' },
    { key: 'reviewer_name', header: 'Reviewer' },
    {
      key: 'actions',
      header: 'Actions',
      render: (r: LeaveRequest) =>
        r.status === 'pending' && canReview ? (
          <span style={{ display: 'flex', gap: 6 }}>
            <button onClick={() => handleReview(r.id, 'approved')} style={styles.btnApprove}>
              Approve
            </button>
            <button onClick={() => handleReview(r.id, 'rejected')} style={styles.btnReject}>
              Reject
            </button>
          </span>
        ) : null,
    },
  ];

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.heading}>Leave Requests</h1>
        <button onClick={() => setShowForm(!showForm)} style={styles.newBtn}>
          {showForm ? 'Cancel' : '+ New Request'}
        </button>
      </div>

      {/* PTO Alerts */}
      {canReview && alerts && alerts.length > 0 && (
        <div style={styles.alertBox}>
          <strong>Mandatory PTO Alerts:</strong>
          <ul style={{ margin: '8px 0 0', padding: '0 0 0 20px' }}>
            {alerts.map((a) => (
              <li key={a.staff_id}>
                <StatusBadge value={a.level} label={a.level.toUpperCase()} />{' '}
                {a.staff_name} — {a.remaining_leave} days remaining (deadline: {a.deadline})
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* New Request Form */}
      {showForm && (
        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.formRow}>
            <label>Staff ID:</label>
            <input
              type="number"
              value={formData.staff}
              onChange={(e) => setFormData({ ...formData, staff: e.target.value })}
              required
              style={styles.input}
            />
          </div>
          <div style={styles.formRow}>
            <label>Date:</label>
            <input
              type="date"
              value={formData.date}
              onChange={(e) => setFormData({ ...formData, date: e.target.value })}
              required
              style={styles.input}
            />
          </div>
          <div style={styles.formRow}>
            <label>Type:</label>
            <select
              value={formData.leave_type}
              onChange={(e) => setFormData({ ...formData, leave_type: e.target.value })}
              style={styles.input}
            >
              <option value="paid">Paid Leave</option>
              <option value="holiday">Holiday</option>
              <option value="sick">Sick</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div style={styles.formRow}>
            <label>Reason:</label>
            <textarea
              value={formData.reason}
              onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
              style={{ ...styles.input, minHeight: 60 }}
            />
          </div>
          <button type="submit" style={styles.submitBtn}>Submit Request</button>
        </form>
      )}

      <DataTable columns={columns} data={requests?.results ?? []} loading={loading} />
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  header: {
    display: 'flex',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  heading: { margin: 0, fontSize: 22 },
  newBtn: {
    padding: '8px 16px',
    background: '#0f3460',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 14,
  },
  alertBox: {
    background: '#fff3cd',
    border: '1px solid #ffc107',
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
    fontSize: 14,
  },
  form: {
    background: '#fff',
    padding: 20,
    borderRadius: 8,
    marginBottom: 16,
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  formRow: {
    marginBottom: 12,
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  input: {
    flex: 1,
    padding: '8px 12px',
    border: '1px solid #ddd',
    borderRadius: 6,
    fontSize: 14,
  },
  submitBtn: {
    padding: '10px 20px',
    background: '#27ae60',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 14,
  },
  btnApprove: {
    padding: '4px 10px',
    background: '#27ae60',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 12,
  },
  btnReject: {
    padding: '4px 10px',
    background: '#e74c3c',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 12,
  },
};

export default LeavePage;
