import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { AuthLayout } from './components/layout/AuthLayout'
import { ProtectedRoute } from './components/layout/ProtectedRoute'
import { LoginPage } from './pages/auth/Login'
import { RegisterPage } from './pages/auth/Register'
import { ForgotPasswordPage } from './pages/auth/ForgotPassword'
import { ResetPasswordPage } from './pages/auth/ResetPassword'
import { AcceptInvitePage } from './pages/auth/AcceptInvite'
import { DashboardPage } from './pages/dashboard/DashboardPage'
import { JobListPage } from './pages/jobs/JobList'
import { JobDetailPage } from './pages/jobs/JobDetail'
import { JobFormPage } from './pages/jobs/JobForm'
import { CandidateListPage } from './pages/candidates/CandidateList'
import { CandidateDetailPage } from './pages/candidates/CandidateDetail'
import { PipelineBoardPage } from './pages/pipelines/PipelineBoard'
import { ApplicationDetailPage } from './pages/pipelines/ApplicationDetail'
import { InterviewListPage } from './pages/interviews/InterviewList'
import { InterviewDetailPage } from './pages/interviews/InterviewDetail'
import { AssessmentListPage, AssessmentDetailPage } from './pages/assessments/AssessmentPages'
import { OfferListPage, OfferDetailPage } from './pages/offers/OfferPages'
import { TalentPoolsPage, ReferralsPage } from './pages/talent/TalentPages'
import { AnalyticsPage } from './pages/analytics/AnalyticsPage'
import { CareerHomePage, JobPublicDetailPage, ApplyFormPage } from './pages/career/CareerPages'
import {
  PortalLayout,
  PortalHomePage,
  MyApplicationsPage,
  MyInterviewsPage,
  MyAssessmentsPage,
  MyOffersPage,
  PortalMessagesPage,
  PortalDocumentsPage,
} from './pages/portal/PortalPages'
import { SettingsPage } from './pages/settings/SettingsPage'
import { SearchPage } from './pages/search/SearchPage'
import { MessagesPage } from './pages/messages/MessagesPage'
import { NotificationsPage } from './pages/notifications/NotificationsPage'
import { useAuth } from './hooks/useAuth'
import { Spinner } from './components/ui'

function HomeRedirect() {
  const { isAuthenticated, isStaff, isCandidate, loading } = useAuth()
  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading…" />
      </div>
    )
  }
  if (!isAuthenticated) return <Navigate to="/careers" replace />
  if (!isCandidate || isStaff) return <Navigate to="/portal" replace />
  return <Navigate to="/app" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />

      {/* Auth */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/accept-invite" element={<AcceptInvitePage />} />
      </Route>

      {/* Public career site */}
      <Route path="/careers" element={<CareerHomePage />} />
      <Route path="/careers/jobs/:jobId" element={<JobPublicDetailPage />} />
      <Route path="/careers/jobs/:jobId/apply" element={<ApplyFormPage />} />

      {/* Staff ATS */}
      <Route element={<ProtectedRoute staffOnly />}>
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<JobListPage />} />
          <Route path="jobs" element={<JobListPage />} />
          <Route path="jobs/new" element={<JobFormPage />} />
          <Route path="jobs/:id" element={<JobDetailPage />} />
          <Route path="jobs/:id/edit" element={<JobFormPage />} />
          <Route path="candidates" element={<CandidateListPage />} />
          <Route path="candidates/:id" element={<CandidateDetailPage />} />
          <Route path="pipeline" element={<PipelineBoardPage />} />
          <Route path="pipeline/applications/:id" element={<ApplicationDetailPage />} />
          <Route path="interviews" element={<InterviewListPage />} />
          <Route path="interviews/:id" element={<InterviewDetailPage />} />
          <Route path="assessments" element={<AssessmentListPage />} />
          <Route path="assessments/:id" element={<AssessmentDetailPage />} />
          <Route path="offers" element={<OfferListPage />} />
          <Route path="offers/:id" element={<AssessmentDetailPage />} />
          <Route path="talent" element={<TalentPoolsPage />} />
          <Route path="referrals" element={<ReferralsPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="messages" element={<MessagesPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Route>

      {/* Candidate portal */}
      <Route element={<ProtectedRoute candidateOnly />}>
        <Route path="/portal" element={<PortalLayout />}>
          <Route index element={<PortalHomePage />} />
          <Route path="applications" element={<MyApplicationsPage />} />
          <Route path="interviews" element={<MyInterviewsPage />} />
          <Route path="assessments" element={<MyAssessmentsPage />} />
          <Route path="offers" element={<MyOffersPage />} />
          <Route path="messages" element={<PortalMessagesPage />} />
          <Route path="documents" element={<PortalDocumentsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
