import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@fontsource-variable/dm-sans";
import "@fontsource-variable/fraunces";
import { i18nReady } from "./i18n";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/components.css";
import "./styles/layouts.css";
import "./styles/landing.css";
import { ApiError } from "./api/client";
import { App } from "./App";
import { prefetchLikelyNextChunks } from "./prefetch";
import { AuthProvider } from "./auth/AuthContext";
import { ConfigProvider } from "./config/brand";
import { ToastProvider } from "./shared/components/Toast";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      refetchOnWindowFocus: true,
      // Don't hammer the API on client errors; retry transient failures once.
      retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 1,
    },
  },
});

void i18nReady.then(() => {
  createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <ConfigProvider>
          <ToastProvider>
            <AuthProvider>
              <App />
            </AuthProvider>
          </ToastProvider>
        </ConfigProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
  );
  prefetchLikelyNextChunks();
});
