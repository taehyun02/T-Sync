export default function SectionCard({ eyebrow, title, description, children }) {
  return (
    <section className="section-card">
      <div className="section-head">
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      {children}
    </section>
  );
}
