import { useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import clsx from "clsx";
import { Button } from "./Button";
import { Field, Textarea } from "./Field";

interface ModalProps {
  open: boolean;
  title: ReactNode;
  description?: ReactNode;
  onClose: () => void;
  children?: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}

export function Modal({ open, title, description, onClose, children, footer, wide }: ModalProps) {
  const { t } = useTranslation();
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    const first = dialogRef.current?.querySelector<HTMLElement>("input, textarea, select, button:not([data-close])");
    (first ?? dialogRef.current)?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      previous?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;
  return createPortal(
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={dialogRef} className={clsx("modal", wide && "modal-wide")} role="dialog" aria-modal="true" tabIndex={-1}>
        <div className="modal-header">
          <div className="stack-sm">
            <h2 style={{ fontSize: "var(--text-lg)" }}>{title}</h2>
            {description && <p className="muted">{description}</p>}
          </div>
          <button className="icon-btn" onClick={onClose} aria-label={t("common.close")} data-close>
            <X />
          </button>
        </div>
        {children && <div className="modal-body">{children}</div>}
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}

interface ConfirmProps {
  open: boolean;
  title: ReactNode;
  description?: ReactNode;
  confirmLabel: string;
  tone?: "primary" | "danger";
  loading?: boolean;
  withReason?: string;
  onConfirm: (reason?: string) => void;
  onClose: () => void;
}

/** Confirmation dialog with an optional free-text reason. */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  tone = "primary",
  loading,
  withReason,
  onConfirm,
  onClose,
}: ConfirmProps) {
  const { t } = useTranslation();
  const [reason, setReason] = useState("");
  useEffect(() => {
    if (open) setReason("");
  }, [open]);
  return (
    <Modal
      open={open}
      title={title}
      description={description}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            variant={tone === "danger" ? "danger-solid" : "primary"}
            loading={loading}
            onClick={() => onConfirm(reason.trim() || undefined)}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      {withReason && (
        <Field label={withReason}>
          <Textarea value={reason} onChange={(e) => setReason(e.target.value)} maxLength={255} rows={3} />
        </Field>
      )}
    </Modal>
  );
}
