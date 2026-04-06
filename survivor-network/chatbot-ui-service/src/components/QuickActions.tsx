import type { QuickAction } from '../quickActions'

type QuickActionsProps = {
  actions: QuickAction[]
  disabled?: boolean
  onSelect: (value: string) => void
}

export default function QuickActions({
  actions,
  disabled = false,
  onSelect,
}: QuickActionsProps) {
  if (!actions.length) return null

  return (
    <div className="quick-actions">
      {actions.map((action) => (
        <button
          key={`${action.label}-${action.value}`}
          type="button"
          className="quick-action-chip"
          disabled={disabled}
          onClick={() => onSelect(action.value)}
        >
          {action.label}
        </button>
      ))}
    </div>
  )
}