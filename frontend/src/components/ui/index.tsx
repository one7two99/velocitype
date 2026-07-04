import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
} from "react";
import "./ui.css";

type Variant = "default" | "primary" | "ghost" | "danger";

export function Button({
  variant = "default",
  className = "",
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  const v = variant === "default" ? "" : `tf-btn--${variant}`;
  return (
    <button className={`tf-btn ${v} ${className}`} {...rest}>
      {children}
    </button>
  );
}

export function Card({
  className = "",
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return <div className={`tf-card ${className}`}>{children}</div>;
}

export function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor?: string;
  children: ReactNode;
}) {
  return (
    <div className="tf-field">
      <label htmlFor={htmlFor}>{label}</label>
      {children}
    </div>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className="tf-input" {...props} />;
}

export function Alert({ children }: { children: ReactNode }) {
  return <div className="tf-alert">{children}</div>;
}

export function Spinner() {
  return <div className="tf-spinner" aria-label="loading" />;
}
