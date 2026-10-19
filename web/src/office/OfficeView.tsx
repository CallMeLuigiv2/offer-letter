export default function OfficeView(props: {
  personas: { id: string; name: string; color: string }[];
  onPersonaClick?: (id: string) => void;
}) {
  void props;
  return <div style={{ padding: 24 }}>The office opens soon</div>;
}
