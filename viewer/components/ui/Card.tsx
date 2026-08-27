export function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded border border-line bg-panel ${className}`}>
      {title ? (
        <div className="border-b border-line px-4 py-2">
          <h3 className="label-caps text-xs font-semibold text-muted">{title}</h3>
        </div>
      ) : null}
      <div className="p-4">{children}</div>
    </div>
  );
}
