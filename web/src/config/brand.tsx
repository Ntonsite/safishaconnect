import { createContext, useContext, useEffect, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { publicApi } from "../api/endpoints";
import type { PublicConfig } from "../api/types";

/**
 * Brand configuration. Build-time defaults come from VITE_* env vars; the API's
 * /config endpoint (driven by backend env) overrides them at runtime, so the
 * product can be renamed without touching component code.
 */
const DEFAULT_CONFIG: PublicConfig = {
  brand: {
    app_name: import.meta.env.VITE_APP_NAME || "SafishaCon",
    tagline: "Book. We assign. We clean.",
    logo_url: "/brand/mark.svg",
    support_email: "support@safishacon.local",
    support_phone: "+255 700 000 000",
    support_whatsapp: "+255 700 000 000",
    office_address: "Dar es Salaam, Tanzania",
  },
  currency: "TZS",
  default_locale: "en",
  supported_locales: ["en", "sw"],
  timezone: "Africa/Dar_es_Salaam",
  demo_mode: false,
  payment_methods: [
    { method: "CASH", available: true, status: "AVAILABLE" },
    { method: "MOBILE_MONEY", available: false, status: "COMING_SOON" },
    { method: "CARD", available: false, status: "COMING_SOON" },
  ],
  booking_slot_start_hour: 7,
  booking_slot_end_hour: 17,
  demo_accounts: [],
};

const ConfigContext = createContext<PublicConfig>(DEFAULT_CONFIG);

export function ConfigProvider({ children }: { children: ReactNode }) {
  const { data } = useQuery({ queryKey: ["config"], queryFn: publicApi.config, staleTime: 10 * 60_000 });
  const config = data ?? DEFAULT_CONFIG;
  useEffect(() => {
    document.title = `${config.brand.app_name} — ${config.brand.tagline}`;
  }, [config.brand.app_name, config.brand.tagline]);
  return <ConfigContext.Provider value={config}>{children}</ConfigContext.Provider>;
}

export function useConfig() {
  return useContext(ConfigContext);
}

export function useBrand() {
  return useContext(ConfigContext).brand;
}
