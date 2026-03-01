// API response types matching Django REST Framework serializers

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  roles: string[];
  is_active: boolean;
}

export interface Store {
  id: number;
  name: string;
  area: string;
  base_difficulty: string;
  effective_difficulty: string;
  slots: number;
  min_pharmacists: number;
  has_controlled_medical_device: boolean;
  has_toxic_substances: boolean;
  has_workers_comp: boolean;
  has_auto_insurance: boolean;
  has_special_public_expense: boolean;
  has_local_voucher: boolean;
  has_holiday_rules: boolean;
  active_flag_count: number;
  monthly_working_days: number | null;
  operates_on_holidays: boolean;
  zoom_account: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Staff {
  id: number;
  user: number | null;
  name: string;
  role: 'pharmacist' | 'clerk' | 'managing_pharmacist';
  employment_type: 'full_time' | 'part_time' | 'dispatch';
  store: number | null;
  store_name: string | null;
  is_rounder: boolean;
  paid_leave_deadline: string;
  paid_leave_used: number;
  monthly_working_days: number | null;
  effective_monthly_working_days: number;
  work_status: 'active' | 'on_leave' | 'maternity' | 'temporary';
  is_active: boolean;
  rounder_profile: Rounder | null;
  created_at: string;
}

export interface Rounder {
  id: number;
  staff: number;
  staff_name: string;
  hunter_rank: string;
  can_work_alone: boolean;
  max_prescriptions: number;
  has_car: boolean;
  can_long_distance: boolean;
  managing_pharmacist_years: string;
  initial_hr: string;
  store_experiences: StoreExperience[];
  updated_at: string;
}

export interface StoreExperience {
  id: number;
  rounder: number;
  store: number;
  store_name: string;
  first_visit_date: string | null;
  last_visit_date: string | null;
  visit_count: number;
}

export interface ShiftPeriod {
  id: number;
  start_date: string;
  end_date: string;
  request_deadline: string;
  is_finalized: boolean;
  created_at: string;
}

export interface Shift {
  id: number;
  staff: number;
  staff_name: string;
  shift_period: number;
  date: string;
  store: number | null;
  store_name: string | null;
  shift_type: 'full' | 'morning' | 'afternoon';
  leave_type: string | null;
  is_confirmed: boolean;
  is_late_request: boolean;
  note: string;
  created_at: string;
}

export interface SupportSlot {
  id: number;
  store: number;
  store_name: string;
  shift_period: number;
  date: string;
  priority: number;
  priority_display: string;
  base_difficulty: string | null;
  attending_pharmacists: number;
  attending_clerks: number;
  has_chief_present: boolean;
  solo_hours: string;
  prescription_forecast: string;
  effective_difficulty_hr: string | null;
  required_hr: string | null;
  is_filled: boolean;
  note: string;
}

export interface Assignment {
  id: number;
  rounder: number;
  rounder_name: string;
  slot: number;
  slot_info: SupportSlot;
  status: 'candidate' | 'confirmed' | 'rejected' | 'cancelled' | 'handed_over';
  confirmed_by: number | null;
  confirmed_at: string | null;
  score: string | null;
  created_at: string;
}

export interface AssignmentLog {
  id: number;
  assignment: number;
  from_status: string;
  from_status_display: string;
  to_status: string;
  to_status_display: string;
  changed_by: number | null;
  changed_by_name: string;
  notification_log: number | null;
  notification_sent: boolean;
  created_at: string;
}

export interface RounderUnavailability {
  id: number;
  rounder: number;
  rounder_name: string;
  shift_period: number;
  reason: string;
  created_at: string;
}

export interface HrEvaluation {
  id: number;
  evaluator: number;
  evaluator_name: string;
  rounder: number;
  rounder_name: string;
  period_start: string;
  period_end: string;
  score: string;
  evaluation_type: 'supervisor' | 'self';
  reason: string;
  rounder_comment: string;
  requires_approval: boolean;
  created_at: string;
}

export interface HrPeriodSummary {
  id: number;
  rounder: number;
  rounder_name: string;
  period_start: string;
  period_end: string;
  supervisor_total: string;
  self_total: string;
  carried_over: string;
  total_points: string;
  computed_hr: string;
  created_at: string;
}

export interface LeaveRequest {
  id: number;
  staff: number;
  staff_name: string;
  date: string;
  leave_type: string;
  leave_type_display: string;
  reason: string;
  status: 'pending' | 'approved' | 'rejected';
  status_display: string;
  reviewer: number | null;
  reviewer_name: string | null;
  review_comment: string;
  is_late: boolean;
  created_at: string;
}

export interface PaidLeaveAlert {
  staff_id: number;
  staff_name: string;
  level: 'warning' | 'urgent' | 'overdue';
  message: string;
  deadline: string;
  remaining_leave: number;
}

export interface StaffTransfer {
  id: number;
  staff: number;
  staff_name: string;
  from_store: number | null;
  from_store_name: string | null;
  to_store: number | null;
  to_store_name: string | null;
  reason: string;
  transferred_by: number | null;
  transferred_by_email: string | null;
  created_at: string;
}

export interface TransferResponse {
  staff: Staff;
  transfer: StaffTransfer;
}

export interface StoreWeeklySchedule {
  id: number;
  store: number;
  store_name: string;
  day_of_week: number;
  day_of_week_display: string;
  is_open: boolean;
  open_time: string | null;
  close_time: string | null;
  staffing_delta: string;
  note: string;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface DailyScheduleOverride {
  id: number;
  store: number;
  store_name: string;
  date: string;
  is_open: boolean;
  note: string;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface StaffingAdjustment {
  id: number;
  store: number;
  store_name: string;
  shift_period: number;
  date: string;
  delta: string;
  source: 'manual' | 'model';
  note: string;
  min_pharmacists: number;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface TokenResponse {
  access: string;
  refresh: string;
}
