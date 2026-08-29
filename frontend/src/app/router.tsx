import { createBrowserRouter, Navigate } from "react-router";

import { MediaPage } from "../features/media/MediaPage";
import { OverviewPage } from "../features/overview/OverviewPage";
import { TransfersPage } from "../features/transfers/TransfersPage";
import { TrendsPage } from "../features/trends/TrendsPage";
import { UptimePage } from "../features/uptime/UptimePage";
import { Shell } from "./Shell";

// The FastAPI app serves index.html for every /app/* path (AC-022), so the
// browser router owns everything below /app.
export const routes = [
  {
    path: "/app",
    element: <Shell />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: "transfers", element: <TransfersPage /> },
      { path: "trends", element: <TrendsPage /> },
      { path: "media", element: <MediaPage /> },
      { path: "uptime", element: <UptimePage /> },
      { path: "*", element: <Navigate to="/app" replace /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
