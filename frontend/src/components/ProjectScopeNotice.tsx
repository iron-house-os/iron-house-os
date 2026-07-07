export function ProjectScopeNotice({ name }: { name: string | null }) {
  if (!name) return null;
  return <div className="rounded-md border border-iron-100 bg-white p-4 text-sm text-iron-700">Working project: {name}</div>;
}
