interface EmptyStateProps {
  icon?: string;
  title: string;
  message?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon, title, message, action }: EmptyStateProps) {
  return (
    <div className="glass-card flex flex-col items-center justify-center p-10 text-center">
      {icon && <span className="mb-3 text-2xl">{icon}</span>}
      <p className="text-sm font-medium">{title}</p>
      {message && (
        <p className="mt-1 max-w-sm text-xs text-muted-foreground">{message}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
