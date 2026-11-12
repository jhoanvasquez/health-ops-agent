interface Props {
  error: string | null;
  loading: boolean;
}

export default function EmptyState({ error, loading }: Props) {
  if (error) {
    return (
      <div className="empty">
        <div>
          <div className="big">Can&rsquo;t reach the API</div>
          <div>{error}</div>
        </div>
      </div>
    );
  }
  if (loading) {
    return (
      <div className="empty">
        <div>Loading…</div>
      </div>
    );
  }
  return (
    <div className="empty">
      <div>
        <div className="big">Queue is clear</div>
        <div>No cases are waiting for review. Check back soon.</div>
      </div>
    </div>
  );
}
