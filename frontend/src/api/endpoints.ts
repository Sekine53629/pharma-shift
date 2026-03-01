import client from './client';
import type {
  Assignment,
  AssignmentLog,
  DailyScheduleOverride,
  HrEvaluation,
  HrPeriodSummary,
  LeaveRequest,
  PaginatedResponse,
  PaidLeaveAlert,
  Rounder,
  RounderUnavailability,
  Shift,
  ShiftPeriod,
  Staff,
  StaffingAdjustment,
  StaffTransfer,
  Store,
  StoreWeeklySchedule,
  SupportSlot,
  TokenResponse,
  TransferResponse,
  User,
} from '../types/models';

// Auth
export const login = (email: string, password: string) =>
  client.post<TokenResponse>('/api/auth/token/', { email, password });

export const refreshToken = (refresh: string) =>
  client.post<TokenResponse>('/api/auth/token/refresh/', { refresh });

// Users
export const fetchMe = () => client.get<User>('/api/accounts/users/me/');
export const fetchUsers = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<User>>('/api/accounts/users/', { params });
export const createUser = (data: Partial<User> & { password: string }) =>
  client.post<User>('/api/accounts/users/', data);
export const changePassword = (old_password: string, new_password: string) =>
  client.post('/api/accounts/users/change_password/', { old_password, new_password });

// Stores
export const fetchStores = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<Store>>('/api/stores/', { params });
export const fetchStore = (id: number) => client.get<Store>(`/api/stores/${id}/`);
export const createStore = (data: Partial<Store>) => client.post<Store>('/api/stores/', data);
export const updateStore = (id: number, data: Partial<Store>) =>
  client.put<Store>(`/api/stores/${id}/`, data);
export const deleteStore = (id: number) => client.delete(`/api/stores/${id}/`);

// Staff
export const fetchStaffMembers = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<Staff>>('/api/staff/members/', { params });
export const createStaff = (data: Partial<Staff>) =>
  client.post<Staff>('/api/staff/members/', data);
export const updateStaff = (id: number, data: Partial<Staff>) =>
  client.patch<Staff>(`/api/staff/members/${id}/`, data);

// Staff Transfers
export const transferStaff = (staffId: number, toStore: number | null, reason?: string) =>
  client.post<TransferResponse>(`/api/staff/members/${staffId}/transfer/`, {
    to_store: toStore,
    reason: reason ?? '',
  });
export const fetchStaffTransfers = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<StaffTransfer>>('/api/staff/transfers/', { params });

// Rounders
export const fetchRounders = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<Rounder>>('/api/staff/rounders/', { params });

// Shift Periods
export const fetchShiftPeriods = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<ShiftPeriod>>('/api/shifts/periods/', { params });
export const createShiftPeriod = (data: Partial<ShiftPeriod>) =>
  client.post<ShiftPeriod>('/api/shifts/periods/', data);

// Shifts
export const fetchShifts = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<Shift>>('/api/shifts/entries/', { params });
export const createShift = (data: Partial<Shift>) =>
  client.post<Shift>('/api/shifts/entries/', data);
export const updateShift = (id: number, data: Partial<Shift>) =>
  client.patch<Shift>(`/api/shifts/entries/${id}/`, data);
export const deleteShift = (id: number) =>
  client.delete(`/api/shifts/entries/${id}/`);

// Support Slots
export const fetchSupportSlots = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<SupportSlot>>('/api/assignments/slots/', { params });
export const createSupportSlot = (data: Partial<SupportSlot>) =>
  client.post<SupportSlot>('/api/assignments/slots/', data);
export const generateCandidates = (slotId: number, limit = 5) =>
  client.post<Assignment[]>(`/api/assignments/slots/${slotId}/generate_candidates/`, {
    slot_id: slotId,
    limit,
  });
export const autoGenerateSupportSlots = (shiftPeriod: number, dailyRx = 150) =>
  client.post<{ created: number; slots: SupportSlot[] }>(
    '/api/assignments/slots/auto_generate/',
    { shift_period: shiftPeriod, daily_rx: dailyRx },
  );

// Assignments
export const fetchAssignments = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<Assignment>>('/api/assignments/entries/', { params });
export const confirmAssignment = (id: number) =>
  client.post<Assignment>(`/api/assignments/entries/${id}/confirm/`);
export const rejectAssignment = (id: number) =>
  client.post<Assignment>(`/api/assignments/entries/${id}/reject/`);
export const cancelAssignment = (id: number) =>
  client.post<Assignment>(`/api/assignments/entries/${id}/cancel/`);
export const handOverAssignment = (id: number, newRounderId: number) =>
  client.post<{ old_assignment: Assignment; new_assignment: Assignment }>(
    `/api/assignments/entries/${id}/hand_over/`,
    { new_rounder_id: newRounderId },
  );

// Assignment Logs
export const fetchAssignmentLogs = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<AssignmentLog>>('/api/assignments/logs/', { params });

// Buffer Management
export const fetchBufferStaff = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<Staff>>('/api/staff/buffer/', { params });
export const toggleRounder = (staffId: number) =>
  client.post<Staff>(`/api/staff/buffer/${staffId}/toggle_rounder/`);
export const updateRounderCapabilities = (staffId: number, data: Partial<Rounder>) =>
  client.patch<Staff>(`/api/staff/buffer/${staffId}/update_capabilities/`, data);

// Rounder Unavailabilities
export const fetchRounderUnavailabilities = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<RounderUnavailability>>('/api/staff/unavailabilities/', { params });
export const createRounderUnavailability = (data: Partial<RounderUnavailability>) =>
  client.post<RounderUnavailability>('/api/staff/unavailabilities/', data);
export const deleteRounderUnavailability = (id: number) =>
  client.delete(`/api/staff/unavailabilities/${id}/`);

// HR
export const fetchHrEvaluations = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<HrEvaluation>>('/api/hr/evaluations/', { params });
export const createHrEvaluation = (data: Partial<HrEvaluation>) =>
  client.post<HrEvaluation>('/api/hr/evaluations/', data);
export const addEvaluationComment = (id: number, comment: string) =>
  client.post(`/api/hr/evaluations/${id}/add_comment/`, { comment });
export const fetchHrSummaries = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<HrPeriodSummary>>('/api/hr/summaries/', { params });

// Leave
export const fetchLeaveRequests = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<LeaveRequest>>('/api/leave/requests/', { params });
export const createLeaveRequest = (data: Partial<LeaveRequest>) =>
  client.post<LeaveRequest>('/api/leave/requests/', data);
export const reviewLeaveRequest = (id: number, status: string, review_comment: string) =>
  client.post(`/api/leave/requests/${id}/review/`, { status, review_comment });
export const fetchPaidLeaveAlerts = () =>
  client.get<PaidLeaveAlert[]>('/api/leave/requests/paid_leave_alerts/');

// Staffing Adjustments
export const fetchStaffingAdjustments = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<StaffingAdjustment>>('/api/staffing/adjustments/', { params });

export const bulkUpsertStaffingAdjustments = (
  shiftPeriod: number,
  adjustments: { store_id: number; date: string; delta: string; note?: string }[],
) =>
  client.post<{ created: number; updated: number }>('/api/staffing/adjustments/bulk_upsert/', {
    shift_period: shiftPeriod,
    adjustments,
  });

// Weekly Schedules
export const fetchWeeklySchedules = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<StoreWeeklySchedule>>('/api/staffing/weekly-schedules/', {
    params,
  });

export const bulkUpsertWeeklySchedules = (
  storeId: number,
  operatesOnHolidays: boolean,
  schedules: {
    day_of_week: number;
    is_open: boolean;
    open_time: string | null;
    close_time: string | null;
    staffing_delta: string;
    note?: string;
  }[],
) =>
  client.post<{ created: number; updated: number }>(
    '/api/staffing/weekly-schedules/bulk_upsert/',
    { store_id: storeId, operates_on_holidays: operatesOnHolidays, schedules },
  );

// Daily Schedule Overrides
export const fetchDailyOverrides = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<DailyScheduleOverride>>('/api/staffing/daily-overrides/', {
    params,
  });

export const bulkUpsertDailyOverrides = (
  storeId: number,
  overrides: { date: string; is_open: boolean; note?: string }[],
) =>
  client.post<{ created: number; updated: number }>(
    '/api/staffing/daily-overrides/bulk_upsert/',
    { store_id: storeId, overrides },
  );

export const removeDailyOverride = (storeId: number, date: string) =>
  client.delete('/api/staffing/daily-overrides/remove/', {
    params: { store: String(storeId), date },
  });
