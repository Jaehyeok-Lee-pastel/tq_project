type RouteLoadingProps = {
  label: string;
};

export function RouteLoading({ label }: RouteLoadingProps) {
  return (
    <section className="route-loading" aria-busy="true" aria-live="polite" aria-label={label}>
      <div className="route-loading-card">
        <span className="route-loading-kicker">TQ Coach</span>
        <strong>{label}</strong>
        <div className="route-loading-lines" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
    </section>
  );
}
