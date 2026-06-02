import { CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { DocumentStatus } from "../api/types";

const CONFIG: Record<
  DocumentStatus,
  { label: string; cls: string; icon: LucideIcon; spin?: boolean }
> = {
  pending: {
    label: "En cola",
    cls: "bg-surface-100 text-surface-600 ring-surface-200 dark:bg-surface-800 dark:text-surface-300 dark:ring-surface-700",
    icon: Clock,
  },
  processing: {
    label: "Procesando",
    cls: "bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/30",
    icon: Loader2,
    spin: true,
  },
  indexed: {
    label: "Indexado",
    cls: "bg-accent-50 text-accent-700 ring-accent-200 dark:bg-accent-500/15 dark:text-accent-300 dark:ring-accent-500/30",
    icon: CheckCircle2,
  },
  failed: {
    label: "Error",
    cls: "bg-red-50 text-red-700 ring-red-200 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/30",
    icon: XCircle,
  },
};

export default function StatusBadge({ status }: { status: DocumentStatus }) {
  const { label, cls, icon: Icon, spin } = CONFIG[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${cls}`}
    >
      <Icon className={`h-3.5 w-3.5 ${spin ? "animate-spin" : ""}`} />
      {label}
    </span>
  );
}
