import { lazy, Suspense, type ComponentType } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { PageLoader } from "./shared/components/Feedback";
import { loadAuthPages } from "./prefetch";
import { RequireRole } from "./auth/RequireRole";
import { PublicLayout } from "./layouts/PublicLayout";
import { HelpPage, HowItWorksPage, NotFoundPage, ServicesPage } from "./features/public/InfoPages";
import { LandingPage } from "./features/public/LandingPage";

// The landing page and light public pages ship in the entry chunk. Everything a visitor
// doesn't need to see "/" — form libraries, signed-in shells and pages — loads on demand.
function lazyNamed<M, K extends keyof M>(loader: () => Promise<M>, name: K) {
  type C = M[K] extends ComponentType<infer P> ? ComponentType<P> : never;
  return lazy(async () => ({ default: (await loader())[name] as unknown as C }));
}

const LoginPage = lazyNamed(loadAuthPages, "LoginPage");
const RegisterPage = lazyNamed(loadAuthPages, "RegisterPage");
const JoinPage = lazyNamed(() => import("./features/public/JoinPage"), "JoinPage");
const CustomerLayout = lazyNamed(() => import("./layouts/RoleLayouts"), "CustomerLayout");
const ProviderLayout = lazyNamed(() => import("./layouts/RoleLayouts"), "ProviderLayout");
const AdminLayout = lazyNamed(() => import("./layouts/RoleLayouts"), "AdminLayout");

const AdminBookingDetailPage = lazyNamed(() => import("./features/admin/AdminBookings"), "AdminBookingDetailPage");
const AdminBookingsPage = lazyNamed(() => import("./features/admin/AdminBookings"), "AdminBookingsPage");
const AdminAreasPage = lazyNamed(() => import("./features/admin/AdminCatalog"), "AdminAreasPage");
const AdminServicesPage = lazyNamed(() => import("./features/admin/AdminCatalog"), "AdminServicesPage");
const AdminOverview = lazyNamed(() => import("./features/admin/AdminOverview"), "AdminOverview");
const AdminCustomersPage = lazyNamed(() => import("./features/admin/AdminPeople"), "AdminCustomersPage");
const AdminProviderDetailPage = lazyNamed(() => import("./features/admin/AdminPeople"), "AdminProviderDetailPage");
const AdminProvidersPage = lazyNamed(() => import("./features/admin/AdminPeople"), "AdminProvidersPage");
const BookingDetailPage = lazyNamed(() => import("./features/customer/BookingDetailPage"), "BookingDetailPage");
const BookingsPage = lazyNamed(() => import("./features/customer/CustomerPages"), "BookingsPage");
const CustomerDashboard = lazyNamed(() => import("./features/customer/CustomerPages"), "CustomerDashboard");
const MyReviewsPage = lazyNamed(() => import("./features/customer/CustomerPages"), "MyReviewsPage");
const NewBookingPage = lazyNamed(() => import("./features/customer/NewBookingPage"), "NewBookingPage");
const ProfilePage = lazyNamed(() => import("./features/customer/ProfilePage"), "ProfilePage");
const JobDetailPage = lazyNamed(() => import("./features/provider/ProviderJobsPages"), "JobDetailPage");
const JobsListPage = lazyNamed(() => import("./features/provider/ProviderJobsPages"), "JobsListPage");
const OffersPage = lazyNamed(() => import("./features/provider/ProviderJobsPages"), "OffersPage");
const ProviderDashboard = lazyNamed(() => import("./features/provider/ProviderJobsPages"), "ProviderDashboard");
const RatingsPage = lazyNamed(() => import("./features/provider/ProviderJobsPages"), "RatingsPage");
const AvailabilityPage = lazyNamed(() => import("./features/provider/ProviderSettingsPages"), "AvailabilityPage");
const CoveragePage = lazyNamed(() => import("./features/provider/ProviderSettingsPages"), "CoveragePage");
const EarningsPage = lazyNamed(() => import("./features/provider/ProviderSettingsPages"), "EarningsPage");
const ProviderProfilePage = lazyNamed(() => import("./features/provider/ProviderSettingsPages"), "ProviderProfilePage");
const NotificationsPage = lazyNamed(() => import("./features/shared/NotificationsPage"), "NotificationsPage");
const AdminAuditPage = lazyNamed(() => import("./features/admin/AdminOperations"), "AdminAuditPage");
const AdminComplaintsPage = lazyNamed(() => import("./features/admin/AdminOperations"), "AdminComplaintsPage");
const AdminPaymentsPage = lazyNamed(() => import("./features/admin/AdminOperations"), "AdminPaymentsPage");
const AdminReviewsPage = lazyNamed(() => import("./features/admin/AdminOperations"), "AdminReviewsPage");
const AdminSettingsPage = lazyNamed(() => import("./features/admin/AdminOperations"), "AdminSettingsPage");
const AdminSettlementsPage = lazyNamed(() => import("./features/admin/AdminOperations"), "AdminSettlementsPage");

export function App() {
  return (
    <Suspense fallback={<PageLoader />}>
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<LandingPage />} />
        <Route path="services" element={<ServicesPage />} />
        <Route path="how-it-works" element={<HowItWorksPage />} />
        <Route path="help" element={<HelpPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="join" element={<JoinPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      <Route element={<RequireRole role="CUSTOMER" />}>
        <Route path="app" element={<CustomerLayout />}>
          <Route index element={<CustomerDashboard />} />
          <Route path="book" element={<NewBookingPage />} />
          <Route path="bookings" element={<BookingsPage />} />
          <Route path="bookings/:id" element={<BookingDetailPage />} />
          <Route path="reviews" element={<MyReviewsPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="profile" element={<ProfilePage />} />
        </Route>
      </Route>

      <Route element={<RequireRole role="PROVIDER" />}>
        <Route path="provider" element={<ProviderLayout />}>
          <Route index element={<ProviderDashboard />} />
          <Route path="offers" element={<OffersPage />} />
          <Route path="jobs" element={<JobsListPage scope="active" />} />
          <Route path="jobs/:id" element={<JobDetailPage />} />
          <Route path="completed" element={<JobsListPage scope="completed" />} />
          <Route path="availability" element={<AvailabilityPage />} />
          <Route path="coverage" element={<CoveragePage />} />
          <Route path="earnings" element={<EarningsPage />} />
          <Route path="ratings" element={<RatingsPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="profile" element={<ProviderProfilePage />} />
        </Route>
      </Route>

      <Route element={<RequireRole role="ADMIN" />}>
        <Route path="admin" element={<AdminLayout />}>
          <Route index element={<AdminOverview />} />
          <Route path="bookings" element={<AdminBookingsPage />} />
          <Route path="bookings/:id" element={<AdminBookingDetailPage />} />
          <Route path="providers" element={<AdminProvidersPage />} />
          <Route path="providers/:id" element={<AdminProviderDetailPage />} />
          <Route path="customers" element={<AdminCustomersPage />} />
          <Route path="services" element={<AdminServicesPage />} />
          <Route path="areas" element={<AdminAreasPage />} />
          <Route path="payments" element={<AdminPaymentsPage />} />
          <Route path="settlements" element={<AdminSettlementsPage />} />
          <Route path="complaints" element={<AdminComplaintsPage />} />
          <Route path="reviews" element={<AdminReviewsPage />} />
          <Route path="audit" element={<AdminAuditPage />} />
          <Route path="settings" element={<AdminSettingsPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Route>
      </Route>
    </Routes>
    </Suspense>
  );
}
