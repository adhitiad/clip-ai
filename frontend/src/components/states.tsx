import { Skeleton } from '#/components/ui/skeleton'
import { Button } from '#/components/ui/button'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '#/components/ui/empty'

export const LoadingState = ({
  label = 'Memuat data dari backend…',
}: {
  label?: string
}) => (
  <div
    className="neon-panel rise-in space-y-2 rounded-xl p-4"
    role="status"
    aria-live="polite"
  >
    <p className="text-sm text-[var(--ink-muted)]">{label}</p>
    <Skeleton className="h-5 w-1/3" />
    <Skeleton className="h-4 w-2/3" />
  </div>
)

export const ErrorState = ({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) => (
  <div
    role="alert"
    className="neon-panel neon-glow-magenta rise-in rounded-xl border-[var(--negative)] px-4 py-3"
  >
    <p className="text-sm">{message}</p>
    {onRetry ? (
      <Button
        type="button"
        onClick={onRetry}
        variant="outline"
        className="mt-2"
      >
        Coba lagi
      </Button>
    ) : null}
  </div>
)

export const EmptyState = ({
  message,
  action,
}: {
  message: string
  action?: { label: string; onClick: () => void }
}) => (
  <Empty role="status" className="neon-panel rise-in rounded-xl">
    <EmptyHeader>
      <EmptyTitle>Belum ada data</EmptyTitle>
      <EmptyDescription>{message}</EmptyDescription>
    </EmptyHeader>
    {action ? (
      <EmptyContent>
        <Button type="button" onClick={action.onClick} variant="outline">
          {action.label}
        </Button>
      </EmptyContent>
    ) : null}
  </Empty>
)
