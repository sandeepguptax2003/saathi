import { Skeleton } from "@/components/ui/skeleton";

export function ListSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-3" aria-busy="true">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex flex-col gap-2 rounded-xl border p-4">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-4 w-4/5" />
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="flex flex-col gap-3 rounded-xl border p-5" aria-busy="true">
      <Skeleton className="h-5 w-1/2" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}

export function TranscriptSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true">
      <Skeleton className="ml-auto h-10 w-2/3 rounded-2xl" />
      <Skeleton className="h-16 w-3/4 rounded-2xl" />
    </div>
  );
}
