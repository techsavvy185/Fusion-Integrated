import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const ComplaintsPage = lazy(() => import("./pages/ComplaintsPage"));
const EscalationsPage = lazy(() => import("./pages/EscalationsPage"));
const ReopenRequestsPage = lazy(() => import("./pages/ReopenRequestsPage"));
const FeedbackPage = lazy(() => import("./pages/FeedbackPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const PolicyPage = lazy(() => import("./pages/PolicyPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="complaints" replace /> },
  { path: "complaints", element: guarded("cms.complaint.view", <ComplaintsPage />) },
  { path: "escalations", element: guarded("cms.escalation.view", <EscalationsPage />) },
  { path: "reopen-requests", element: guarded("cms.reopen_request.approve", <ReopenRequestsPage />) },
  { path: "feedback", element: guarded("cms.feedback.review", <FeedbackPage />) },
  { path: "announcements", element: guarded("cms.announcement.view", <AnnouncementsPage />) },
  { path: "reports", element: guarded("cms.report.view", <ReportsPage />) },
  { path: "policy", element: guarded("cms.policy.manage", <PolicyPage />) },
];
