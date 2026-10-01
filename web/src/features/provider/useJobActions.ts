import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError } from "../../api/client";
import { providerApi } from "../../api/endpoints";
import type { BookingStatus } from "../../api/types";
import { useToast } from "../../shared/components/Toast";

/** Next status for each provider action; sent as `expected_status` so stale taps are rejected. */
export const ACTION_TARGET: Record<string, BookingStatus> = {
  MARK_EN_ROUTE: "PROVIDER_EN_ROUTE",
  MARK_ARRIVED: "PROVIDER_ARRIVED",
  START_SERVICE: "SERVICE_IN_PROGRESS",
  COMPLETE_SERVICE: "COMPLETED_BY_PROVIDER",
};

export function useJobActions() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["provider"] });
    void qc.invalidateQueries({ queryKey: ["notifications"] });
  };
  const onError = (e: unknown) => {
    toast.error(e);
    if (e instanceof ApiError && e.status === 409) refresh();
  };

  return {
    accept: useMutation({
      mutationFn: (assignmentId: string) => providerApi.accept(assignmentId),
      onSuccess: () => {
        toast.success(t("provider.jobAccepted"));
        refresh();
      },
      onError,
    }),
    reject: useMutation({
      mutationFn: ({ assignmentId, reason }: { assignmentId: string; reason?: string }) =>
        providerApi.reject(assignmentId, reason),
      onSuccess: () => {
        toast.success(t("provider.jobRejected"));
        refresh();
      },
      onError,
    }),
    advance: useMutation({
      mutationFn: ({ bookingId, action }: { bookingId: string; action: string }) =>
        providerApi.advance(bookingId, ACTION_TARGET[action]),
      onSuccess: () => {
        toast.success(t("provider.statusUpdated"));
        refresh();
      },
      onError,
    }),
    confirmCash: useMutation({
      mutationFn: (bookingId: string) => providerApi.confirmCash(bookingId),
      onSuccess: () => {
        toast.success(t("provider.cashConfirmed"));
        refresh();
      },
      onError,
    }),
    withdraw: useMutation({
      mutationFn: ({ bookingId, reason }: { bookingId: string; reason?: string }) => providerApi.withdraw(bookingId, reason),
      onSuccess: refresh,
      onError,
    }),
  };
}
