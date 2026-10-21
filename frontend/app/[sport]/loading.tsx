/** Shown while a page's data is on its way. */
export default function Loading() {
  return (
    <div className="skeleton" aria-hidden="true">
      <i className="s" />
      <i className="h" />
      <i />
      <i className="m" />
      <i className="f" />
      <i />
      <i />
      <i className="m" />
    </div>
  );
}
