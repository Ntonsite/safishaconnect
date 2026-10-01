import { useCallback } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "../../api/client";

/** Translate API errors by their stable code, falling back to the server's message. */
export function useErrorMessage() {
  const { t, i18n } = useTranslation();
  return useCallback(
    (error: unknown): string => {
      if (error instanceof ApiError) {
        const key = `errors.${error.code}`;
        if (i18n.exists(key)) {
          // Prefer the precise field message for validation errors in English.
          if (error.code === "VALIDATION_FAILED" && i18n.language === "en" && error.message) return error.message;
          return t(key);
        }
        return error.message || t("common.unknownError");
      }
      return t("common.unknownError");
    },
    [t, i18n],
  );
}
