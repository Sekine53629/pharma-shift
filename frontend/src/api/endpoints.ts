import client from './client';
import type {
  Assignment,
  HrEvaluation,
  HrPeriodSummary,
  LeaveRequest,
  PaginatedResponse,
  PaidLeaveAlert,
  Rounder,
  Shift,
  ShiftPeriod,
  Staff,
  Store,
  SupportSlot,
  TokenResponse,
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

// Assignments
export const fetchAssignments = (params?: Record<string, string>) =>
  client.get<PaginatedResponse<Assignment>>('/api/assignments/entries/', { params });
export const confirmAssignment = (id: number) =>
  client.post<Assignment>(`/api/assignments/entries/${id}/confirm/`);
export const rejectAssignment = (id: number) =>
  client.post<Assignment>(`/api/assignments/entries/${id}/reject/`);

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
