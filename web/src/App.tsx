import { Navigate, Route, Routes } from "react-router-dom";
import { RequireRole } from "./auth/RequireRole";
import { AdminLayout, CustomerLayout, ProviderLayout } from "./layouts/RoleLayouts";
import { PublicLayout } from "./layouts/PublicLayout";
import { AdminBookingDetailPage, AdminBookingsPage } from "./features/admin/AdminBookings";
import { AdminAreasPage, AdminServicesPage } from "./features/admin/AdminCatalog";
import {
  AdminAuditPage,
  AdminComplaintsPage,
  AdminPaymentsPage,
  AdminReviewsPage,
  AdminSettingsPage,
  AdminSettlementsPage,
} from "./features/admin/AdminOperations";
import { AdminOverview } from "./features/admin/AdminOverview";
import { AdminCustomersPage, AdminProviderDetailPage, AdminProvidersPage } from "./features/admin/AdminPeople";
import { BookingDetailPage } from "./features/customer/BookingDetailPage";
import { BookingsPage, CustomerDashboard, MyReviewsPage } from "./features/customer/CustomerPages";
import { NewBookingPage } from "./features/customer/NewBookingPage";
import { ProfilePage } from "./features/customer/ProfilePage";
import { JobDetailPage, JobsListPage, OffersPage, ProviderDashboard, RatingsPage } from "./features/provider/ProviderJobsPages";
import { AvailabilityPage, CoveragePage, EarningsPage, ProviderProfilePage } from "./features/provider/ProviderSettingsPages";
import { LoginPage, RegisterPage } from "./features/public/AuthPages";
import { HelpPage, HowItWorksPage, NotFoundPage, ServicesPage } from "./features/public/InfoPages";
import { JoinPage } from "./features/public/JoinPage";
import { LandingPage } from "./features/public/LandingPage";
import { NotificationsPage } from "./features/shared/NotificationsPage";

export function App() {
  return (
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
  );
}
