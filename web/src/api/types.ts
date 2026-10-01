// Types mirror the FastAPI schemas (see /docs). Money arrives as decimal strings.

export type Role = "CUSTOMER" | "PROVIDER" | "ADMIN";
export type Locale = "en" | "sw";

export type BookingStatus =
  | "PENDING_CONFIRMATION"
  | "CONFIRMED"
  | "FINDING_PROVIDER"
  | "PROVIDER_ASSIGNED"
  | "PROVIDER_EN_ROUTE"
  | "PROVIDER_ARRIVED"
  | "SERVICE_IN_PROGRESS"
  | "COMPLETED_BY_PROVIDER"
  | "CUSTOMER_CONFIRMED"
  | "CLOSED"
  | "CANCELLED"
  | "REASSIGNMENT_REQUIRED"
  | "DISPUTED";

export type PaymentMethod = "CASH" | "MOBILE_MONEY" | "CARD";
export type PaymentStatus = "PENDING" | "PAID" | "FAILED" | "REFUNDED" | "CANCELLED";
export type AssignmentStatus = "OFFERED" | "ACCEPTED" | "REJECTED" | "EXPIRED" | "CANCELLED" | "WITHDRAWN";
export type VerificationStatus = "PENDING" | "VERIFIED" | "REJECTED" | "SUSPENDED";
export type ProviderType = "INDIVIDUAL" | "COMPANY";
export type OptionGroup = "PROPERTY_TYPE" | "SIZE" | "ADDON";
export type ComplaintCategory = "QUALITY" | "LATE_OR_NO_SHOW" | "DAMAGE" | "CONDUCT" | "PAYMENT" | "OTHER";
export type ComplaintStatus = "OPEN" | "IN_REVIEW" | "RESOLVED" | "REJECTED";
export type SettlementStatus = "PENDING" | "SETTLED";

export interface ApiErrorBody {
  error: { code: string; message: string; details?: { field: string; message: string }[] | Record<string, unknown> | null };
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface User {
  id: string;
  email: string | null;
  phone: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  preferred_locale: Locale;
  created_at: string;
}

export interface Me extends User {
  customer_id: string | null;
  provider_id: string | null;
  default_area_id: string | null;
  default_address: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface PublicConfig {
  brand: {
    app_name: string;
    tagline: string;
    logo_url: string;
    support_email: string;
    support_phone: string;
    support_whatsapp: string;
    office_address: string;
  };
  currency: string;
  default_locale: Locale;
  supported_locales: Locale[];
  timezone: string;
  demo_mode: boolean;
  payment_methods: { method: PaymentMethod; available: boolean; status: "AVAILABLE" | "COMING_SOON" }[];
  booking_slot_start_hour: number;
  booking_slot_end_hour: number;
  demo_accounts: { role: "admin" | "customer" | "cleaner" | "company"; email: string; password: string }[];
}

export interface Area {
  id: string;
  name: string;
  slug: string;
  city_id: string;
  city_name: string;
  is_active: boolean;
}

export interface City {
  id: string;
  name: string;
  region: string;
  country_code: string;
  is_active: boolean;
}

export interface ServiceOption {
  id: string;
  group: OptionGroup;
  code: string;
  name_en: string;
  name_sw: string;
  price_amount: string;
  duration_minutes: number;
  max_quantity: number;
  is_active: boolean;
  display_order: number;
}

export interface Service {
  id: string;
  slug: string;
  name_en: string;
  name_sw: string;
  summary_en: string;
  summary_sw: string;
  description_en: string;
  description_sw: string;
  icon: string;
  is_active: boolean;
  display_order: number;
  base_price: string;
  base_duration_minutes: number;
  uses_rooms: boolean;
  included_bedrooms: number;
  included_bathrooms: number;
  price_per_extra_bedroom: string;
  price_per_extra_bathroom: string;
  minutes_per_extra_room: number;
  max_rooms: number;
  options: ServiceOption[];
}

export interface AddonSelection {
  option_id: string;
  quantity: number;
}

export interface QuoteRequest {
  service_id: string;
  property_type_option_id?: string | null;
  size_option_id?: string | null;
  bedrooms: number;
  bathrooms: number;
  addons: AddonSelection[];
}

export interface QuoteLine {
  kind: string;
  code: string;
  label_en: string;
  label_sw: string;
  quantity: number;
  unit_amount: string;
  amount: string;
}

export interface Quote {
  service_id: string;
  currency: string;
  lines: QuoteLine[];
  base_amount: string;
  adjustments_amount: string;
  total_amount: string;
  estimated_duration_minutes: number;
}

export interface Slot {
  start_time: string;
  end_time: string;
  available: boolean;
}

export interface Availability {
  date: string;
  duration_minutes: number;
  slots: Slot[];
}

export interface BookingCreate extends QuoteRequest {
  area_id: string;
  address_line: string;
  landmark?: string | null;
  special_instructions?: string | null;
  scheduled_date: string;
  scheduled_start_time: string;
  payment_method: PaymentMethod;
}

export interface ServiceRef {
  id: string;
  slug: string;
  name_en: string;
  name_sw: string;
  icon: string;
}

export interface BookingSummary {
  id: string;
  reference: string;
  status: BookingStatus;
  service: ServiceRef;
  service_name: string;
  area_id: string;
  area_name: string;
  scheduled_date: string;
  scheduled_start_time: string;
  estimated_duration_minutes: number;
  total_amount: string;
  currency: string;
  payment_method: PaymentMethod;
  payment_status: PaymentStatus | null;
  provider_name: string | null;
  customer_name: string | null;
  created_at: string;
}

export interface StatusEvent {
  from_status: BookingStatus | null;
  to_status: BookingStatus;
  note: string | null;
  actor_name: string | null;
  actor_role: string | null;
  created_at: string;
}

export interface ProviderPublic {
  id: string;
  display_name: string;
  provider_type: ProviderType;
  rating_average: string;
  rating_count: number;
  years_experience: number;
  phone: string | null;
}

export interface PaymentSummary {
  id: string;
  method: PaymentMethod;
  status: PaymentStatus;
  amount: string;
  currency: string;
  paid_at: string | null;
  confirmed_by_name: string | null;
}

export interface AssignmentSummary {
  id: string;
  provider_id: string;
  provider_name: string;
  status: AssignmentStatus;
  is_manual: boolean;
  offered_at: string;
  expires_at: string | null;
  responded_at: string | null;
  response_note: string | null;
}

export interface OptionRef {
  id: string;
  code: string;
  name_en: string;
  name_sw: string;
}

export interface BookingDetail extends BookingSummary {
  address_line: string | null;
  landmark: string | null;
  bedrooms: number;
  bathrooms: number;
  property_type: OptionRef | null;
  size: OptionRef | null;
  special_instructions: string | null;
  base_amount: string;
  adjustments_amount: string;
  commission_percent: string | null;
  commission_amount: string | null;
  provider_earning: string | null;
  price_items: QuoteLine[];
  history: StatusEvent[];
  provider: ProviderPublic | null;
  customer: { id: string; full_name: string; phone: string | null; email: string | null } | null;
  payment: PaymentSummary | null;
  review: { id: string; rating: number; comment: string | null; is_hidden: boolean; created_at: string } | null;
  assignments: AssignmentSummary[] | null;
  has_open_complaint: boolean;
  allowed_actions: string[];
  confirmed_at: string | null;
  completed_at: string | null;
  customer_confirmed_at: string | null;
  closed_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
}

export interface Job {
  assignment_id: string;
  assignment_status: AssignmentStatus;
  offered_at: string;
  expires_at: string | null;
  responded_at: string | null;
  booking: BookingDetail;
}

export interface AvailabilityDay {
  day_of_week: number;
  start_time: string;
  end_time: string;
}

export interface ProviderProfile {
  id: string;
  user_id: string;
  provider_type: ProviderType;
  display_name: string;
  contact_person: string | null;
  full_name: string;
  phone: string;
  email: string | null;
  bio: string;
  years_experience: number;
  registration_number: string | null;
  verification_status: VerificationStatus;
  verified_at: string | null;
  is_accepting_jobs: boolean;
  capacity: number;
  rating_average: string;
  rating_count: number;
  is_active: boolean;
  services: { id: string; slug: string; name_en: string; name_sw: string }[];
  areas: Area[];
  availability: AvailabilityDay[];
  verification_history: { decision: string; notes: string | null; created_at: string }[];
  created_at: string;
}

export interface ProviderDashboard {
  verification_status: VerificationStatus;
  is_accepting_jobs: boolean;
  open_offers: number;
  active_jobs: number;
  completed_jobs: number;
  rating_average: string;
  rating_count: number;
  earnings_total: string;
  earnings_pending: string;
  currency: string;
  setup_complete: boolean;
  missing_setup: ("SERVICES" | "AREAS" | "AVAILABILITY")[];
}

export interface EarningRow {
  booking_id: string;
  reference: string;
  service_name: string;
  scheduled_date: string;
  status: BookingStatus;
  total_amount: string;
  commission_amount: string;
  provider_earning: string;
  payment_status: PaymentStatus | null;
  settlement_status: SettlementStatus | null;
  settled_at: string | null;
  settlement_reference: string | null;
}

export interface Earnings {
  currency: string;
  total_earned: string;
  pending_settlement: string;
  settled: string;
  awaiting_completion: string;
  rows: EarningRow[];
}

export interface Review {
  id: string;
  booking_id: string;
  booking_reference: string;
  service_name: string;
  provider_id: string;
  provider_name: string;
  customer_name: string;
  rating: number;
  comment: string | null;
  is_hidden: boolean;
  moderation_note: string | null;
  created_at: string;
}

export interface PublicReview {
  rating: number;
  comment: string | null;
  customer_first_name: string;
  area_name: string;
  service_name: string;
  created_at: string;
}

export interface Complaint {
  id: string;
  booking_id: string;
  booking_reference: string;
  booking_status: BookingStatus;
  customer_name: string;
  provider_name: string | null;
  category: ComplaintCategory;
  description: string;
  status: ComplaintStatus;
  admin_notes: string | null;
  resolution: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  booking_id: string | null;
  booking_reference: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationList {
  unread: number;
  items: Notification[];
}

// ---- Admin ---------------------------------------------------------------------------

export interface Stats {
  currency: string;
  total_customers: number;
  active_providers: number;
  providers_awaiting_verification: number;
  total_bookings: number;
  todays_bookings: number;
  completed_bookings: number;
  cancelled_bookings: number;
  gross_booking_value: string;
  platform_commission: string;
  pending_assignments: number;
  open_complaints: number;
  cash_awaiting_confirmation: number;
  settlements_pending_amount: string;
  bookings_by_status: Record<string, number>;
}

export interface CustomerRow {
  id: string;
  user_id: string;
  full_name: string;
  phone: string;
  email: string | null;
  is_active: boolean;
  bookings_count: number;
  total_spent: string;
  created_at: string;
}

export interface ProviderRow {
  id: string;
  display_name: string;
  provider_type: ProviderType;
  phone: string;
  email: string | null;
  verification_status: VerificationStatus;
  is_active: boolean;
  is_accepting_jobs: boolean;
  rating_average: string;
  rating_count: number;
  completed_jobs: number;
  area_names: string[];
  service_names: string[];
  created_at: string;
}

export interface EligibleProvider {
  id: string;
  display_name: string;
  provider_type: ProviderType;
  rating_average: string;
  rating_count: number;
  jobs_that_day: number;
}

export interface PaymentRow {
  id: string;
  booking_id: string;
  booking_reference: string;
  booking_status: BookingStatus;
  customer_name: string;
  provider_name: string | null;
  method: PaymentMethod;
  status: PaymentStatus;
  amount: string;
  currency: string;
  paid_at: string | null;
  confirmed_by_name: string | null;
  created_at: string;
}

export interface SettlementRow {
  id: string;
  booking_id: string;
  booking_reference: string;
  provider_id: string;
  provider_name: string;
  gross_amount: string;
  commission_amount: string;
  provider_earning: string;
  cash_collected_by_provider: boolean;
  status: SettlementStatus;
  settled_at: string | null;
  reference: string | null;
  note: string | null;
  created_at: string;
}

export interface AuditEntry {
  id: string;
  actor_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface Setting {
  key: string;
  value: string;
  description: string;
}
