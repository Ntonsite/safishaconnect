import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { Link, type LinkProps } from "react-router-dom";
import clsx from "clsx";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "secondary" | "soft" | "ghost" | "danger" | "danger-solid";
type Size = "sm" | "md" | "lg";

interface Common {
  variant?: Variant;
  size?: Size;
  block?: boolean;
  icon?: ReactNode;
}

function classes({ variant = "primary", size = "md", block }: Common, extra?: string) {
  return clsx("btn", `btn-${variant}`, size !== "md" && `btn-${size}`, block && "btn-block", extra);
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, Common {
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant, size, block, icon, loading, children, className, disabled, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={classes({ variant, size, block }, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Loader2 className="spin" aria-hidden /> : icon}
      {children}
    </button>
  );
});

export function ButtonLink({ variant, size, block, icon, children, className, ...rest }: LinkProps & Common) {
  return (
    <Link className={classes({ variant, size, block }, className)} {...rest}>
      {icon}
      {children}
    </Link>
  );
}
