import { cn } from "@/lib/utils";
import type { ItemStatus } from "@/types";

const STATUS_CLASS: Record<ItemStatus, string> = {
  Bom: "bg-success/15 text-success",
  Alerta: "bg-warning/15 text-warning",
  Ruim: "bg-orange-500/15 text-orange-400",
  "Em falta": "bg-destructive/15 text-destructive",
};

export function StatusBadge({ status }: { status: ItemStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap",
        STATUS_CLASS[status],
      )}
    >
      {status}
    </span>
  );
}
