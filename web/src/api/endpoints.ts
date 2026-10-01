import { api } from "./client";
import type {
  Area,
  AuditEntry,
  Availability,
  AvailabilityDay,
  BookingCreate,
  BookingDetail,
  BookingStatus,
  BookingSummary,
  City,
  Complaint,
  ComplaintCategory,
  ComplaintStatus,
  CustomerRow,
  Earnings,
  EligibleProvider,
  Job,
  Me,
  NotificationList,
  Page,
  PaymentRow,
  PaymentStatus,
  ProviderDashboard,
  ProviderProfile,
  ProviderRow,
  ProviderType,
  PublicConfig,
  PublicReview,
  Quote,
  QuoteRequest,
  Review,
  Service,
  ServiceOption,
  Setting,
  SettlementRow,
  Stats,
  TokenPair,
  VerificationStatus,
} from "./types";

const post = <T>(path: string, body: unknown = {}) => api<T>(path, { method: "POST", body });
const patch = <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body });
const put = <T>(path: string, body: unknown) => api<T>(path, { method: "PUT", body });

export const publicApi = {
  config: () => api<PublicConfig>("/config", { auth: false }),
  services: () => api<Service[]>("/services", { auth: false }),
  service: (key: string) => api<Service>(`/services/${key}`, { auth: false }),
  areas: () => api<Area[]>("/areas", { auth: false }),
  quote: (body: QuoteRequest) => api<Quote>("/quotes", { method: "POST", body, auth: false }),
  availability: (q: { service_id: string; area_id: string; date: string; duration_minutes: number }) =>
    api<Availability>("/availability", { query: q, auth: false }),
  reviews: () => api<PublicReview[]>("/reviews/public", { auth: false }),
};

export interface CustomerRegisterBody {
  full_name: string;
  phone: string;
  email?: string | null;
  password: string;
  preferred_locale: string;
}

export interface ProviderRegisterBody extends CustomerRegisterBody {
  provider_type: ProviderType;
  business_name?: string | null;
  email: string;
  bio: string;
  years_experience: number;
  registration_number?: string | null;
  capacity: number;
  service_ids: string[];
  area_ids: string[];
  availability: AvailabilityDay[];
}

export const authApi = {
  login: (identifier: string, password: string) =>
    api<TokenPair>("/auth/login", { method: "POST", body: { identifier, password }, auth: false }),
  register: (body: CustomerRegisterBody) => api<TokenPair>("/auth/register", { method: "POST", body, auth: false }),
  registerProvider: (body: ProviderRegisterBody) =>
    api<TokenPair>("/auth/register/provider", { method: "POST", body, auth: false }),
  logout: (refresh_token: string) => api<void>("/auth/logout", { method: "POST", body: { refresh_token }, auth: false }),
  me: () => api<Me>("/auth/me"),
  updateMe: (body: Partial<Pick<Me, "full_name" | "email" | "phone" | "preferred_locale" | "default_area_id" | "default_address">>) =>
    patch<Me>("/auth/me", body),
  changePassword: (current_password: string, new_password: string) =>
    post<{ message: string }>("/auth/change-password", { current_password, new_password }),
};

export const customerApi = {
  createBooking: (body: BookingCreate) => post<BookingDetail>("/bookings", body),
  bookings: (scope: "all" | "active" | "history" = "all") => api<BookingSummary[]>("/bookings", { query: { scope } }),
  booking: (id: string) => api<BookingDetail>(`/bookings/${id}`),
  confirm: (id: string) => post<BookingDetail>(`/bookings/${id}/confirm`),
  cancel: (id: string, reason?: string) => post<BookingDetail>(`/bookings/${id}/cancel`, { reason }),
  confirmCompletion: (id: string) => post<BookingDetail>(`/bookings/${id}/confirm-completion`),
  review: (booking_id: string, rating: number, comment?: string) =>
    post<Review>("/reviews", { booking_id, rating, comment }),
  myReviews: () => api<Review[]>("/reviews/mine"),
  complain: (booking_id: string, category: ComplaintCategory, description: string) =>
    post<Complaint>("/complaints", { booking_id, category, description }),
  complaints: () => api<Complaint[]>("/complaints"),
};

export const providerApi = {
  profile: () => api<ProviderProfile>("/providers/me"),
  updateProfile: (body: Partial<ProviderProfile>) => patch<ProviderProfile>("/providers/me", body),
  setServices: (ids: string[]) => put<ProviderProfile>("/providers/me/services", { ids }),
  setAreas: (ids: string[]) => put<ProviderProfile>("/providers/me/areas", { ids }),
  setAvailability: (days: AvailabilityDay[]) => put<ProviderProfile>("/providers/me/availability", { days }),
  dashboard: () => api<ProviderDashboard>("/providers/me/dashboard"),
  earnings: () => api<Earnings>("/providers/me/earnings"),
  reviews: () => api<Review[]>("/providers/me/reviews"),
  jobs: (scope: "offers" | "active" | "completed") => api<Job[]>("/providers/me/jobs", { query: { scope } }),
  job: (bookingId: string) => api<Job>(`/providers/me/jobs/${bookingId}`),
  advance: (bookingId: string, expected_status: BookingStatus) =>
    post<Job>(`/providers/me/jobs/${bookingId}/advance`, { expected_status }),
  withdraw: (bookingId: string, reason?: string) =>
    post<BookingDetail>(`/providers/me/jobs/${bookingId}/withdraw`, { reason }),
  accept: (assignmentId: string) => post<Job>(`/assignments/${assignmentId}/accept`),
  reject: (assignmentId: string, reason?: string) => post<Job>(`/assignments/${assignmentId}/reject`, { reason }),
  confirmCash: (bookingId: string, note?: string) => post(`/payments/bookings/${bookingId}/confirm-cash`, { note }),
};

export const notificationsApi = {
  list: () => api<NotificationList>("/notifications"),
  read: (id: string) => post(`/notifications/${id}/read`),
  readAll: () => post<NotificationList>("/notifications/read-all"),
};

type Paging = { page?: number; page_size?: number };

export const adminApi = {
  stats: () => api<Stats>("/admin/stats"),
  customers: (q: Paging & { q?: string }) => api<Page<CustomerRow>>("/admin/customers", { query: q }),
  customerBookings: (id: string) => api<BookingSummary[]>(`/admin/customers/${id}/bookings`),
  setCustomerActive: (id: string, is_active: boolean) => patch<CustomerRow>(`/admin/customers/${id}`, { is_active }),
  providers: (q: Paging & { q?: string; verification_status?: VerificationStatus | ""; provider_type?: ProviderType | "" }) =>
    api<Page<ProviderRow>>("/admin/providers", { query: q }),
  provider: (id: string) => api<ProviderProfile>(`/admin/providers/${id}`),
  providerBookings: (id: string) => api<BookingSummary[]>(`/admin/providers/${id}/bookings`),
  providerReviews: (id: string) => api<Review[]>(`/admin/providers/${id}/reviews`),
  verifyProvider: (id: string, action: string, notes?: string) =>
    post<ProviderProfile>(`/admin/providers/${id}/verification`, { action, notes }),
  setProviderActive: (id: string, is_active: boolean) => patch<ProviderProfile>(`/admin/providers/${id}`, { is_active }),
  services: () => api<Service[]>("/admin/services"),
  createService: (body: Partial<Service>) => post<Service>("/admin/services", body),
  updateService: (id: string, body: Partial<Service>) => patch<Service>(`/admin/services/${id}`, body),
  createOption: (serviceId: string, body: Partial<ServiceOption>) =>
    post<ServiceOption>(`/admin/services/${serviceId}/options`, body),
  updateOption: (id: string, body: Partial<ServiceOption>) => patch<ServiceOption>(`/admin/options/${id}`, body),
  cities: () => api<City[]>("/admin/cities"),
  createCity: (body: { name: string; region: string }) => post<City>("/admin/cities", body),
  areas: () => api<Area[]>("/admin/areas"),
  createArea: (body: { city_id: string; name: string }) => post<Area>("/admin/areas", body),
  updateArea: (id: string, body: { name?: string; is_active?: boolean }) => patch<Area>(`/admin/areas/${id}`, body),
  bookings: (q: Paging & {
    status?: BookingStatus[];
    service_id?: string;
    area_id?: string;
    provider_id?: string;
    customer_id?: string;
    date_from?: string;
    date_to?: string;
    q?: string;
  }) => api<Page<BookingSummary>>("/admin/bookings", { query: q }),
  booking: (id: string) => api<BookingDetail>(`/admin/bookings/${id}`),
  eligibleProviders: (id: string, includeOffHours = false) =>
    api<EligibleProvider[]>(`/admin/bookings/${id}/eligible-providers`, { query: { include_off_hours: includeOffHours } }),
  assign: (id: string, provider_id: string, direct: boolean, note?: string) =>
    post<BookingDetail>(`/admin/bookings/${id}/assign`, { provider_id, direct, note }),
  setStatus: (id: string, status: BookingStatus, note?: string) =>
    post<BookingDetail>(`/admin/bookings/${id}/status`, { status, note }),
  setPayment: (id: string, status: PaymentStatus, note?: string) =>
    post<BookingDetail>(`/admin/bookings/${id}/payment`, { status, note }),
  payments: (q: Paging & { status?: PaymentStatus | ""; method?: string }) =>
    api<Page<PaymentRow>>("/admin/payments", { query: q }),
  settlements: (q: Paging & { status?: string }) => api<Page<SettlementRow>>("/admin/settlements", { query: q }),
  settle: (id: string, reference?: string, note?: string) =>
    post<SettlementRow>(`/admin/settlements/${id}/settle`, { reference, note }),
  complaints: (q: Paging & { status?: ComplaintStatus | "" }) => api<Page<Complaint>>("/admin/complaints", { query: q }),
  updateComplaint: (id: string, body: { status: ComplaintStatus; admin_notes?: string; resolution?: string }) =>
    patch<Complaint>(`/admin/complaints/${id}`, body),
  reviews: (q: Paging) => api<Page<Review>>("/admin/reviews", { query: q }),
  moderateReview: (id: string, is_hidden: boolean, moderation_note?: string) =>
    patch<Review>(`/admin/reviews/${id}`, { is_hidden, moderation_note }),
  audit: (q: Paging & { action?: string }) => api<Page<AuditEntry>>("/admin/audit", { query: q }),
  settings: () => api<Setting[]>("/admin/settings"),
  updateSetting: (key: string, value: string) => put<Setting[]>(`/admin/settings/${key}`, { value }),
};
