import { ArrowLeft, CheckCircle2, FolderUp } from "lucide-react";
import { ReactNode } from "react";

import { MediaCategory } from "../api/media";
import { UniversalPhotoField } from "./UniversalPhotoField";

export type FormReviewItem = {
  label: string;
  value: ReactNode;
};

type Props = {
  title: string;
  destination: string;
  items: FormReviewItem[];
  files: File[];
  onFilesChange: (files: File[]) => void;
  category: MediaCategory;
  onBack: () => void;
  onPost: () => void;
  posting?: boolean;
  postLabel?: string;
  children?: ReactNode;
};

export function FormReviewPanel({
  title,
  destination,
  items,
  files,
  onFilesChange,
  category,
  onBack,
  onPost,
  posting = false,
  postLabel = "Post to job folder",
  children,
}: Props) {
  return (
    <section aria-label={`Review ${title}`} className="rounded-xl border border-brand-gold/40 bg-white p-4 shadow-sm sm:p-5">
      <div className="flex items-start gap-3">
        <CheckCircle2 className="mt-0.5 h-6 w-6 shrink-0 text-brand-gold-dark" />
        <div>
          <h2 className="font-semibold text-iron-950">Review before posting</h2>
          <p className="mt-1 text-sm text-iron-500">Confirm the complete form and every photo. Nothing is posted until you use the final button below.</p>
        </div>
      </div>

      <div className="mt-4 rounded-md border border-brand-gold/30 bg-brand-gold/5 p-3">
        <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-brand-gold-dark">Destination</div>
        <div className="mt-1 flex items-center gap-2 text-sm font-semibold text-iron-950"><FolderUp className="h-4 w-4" />{destination}</div>
      </div>

      <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => (
          <div key={item.label} className="rounded-md bg-iron-50 p-3">
            <dt className="text-[10px] font-semibold uppercase tracking-wide text-iron-500">{item.label}</dt>
            <dd className="mt-1 break-words text-sm font-semibold text-iron-950">{item.value || "Not entered"}</dd>
          </div>
        ))}
      </dl>

      {children ? <div className="mt-4">{children}</div> : null}

      <div className="mt-4">
        <UniversalPhotoField files={files} onFilesChange={onFilesChange} category={category} label={`Photos selected (${files.length})`} />
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        <button type="button" disabled={posting} onClick={onBack} className="flex min-h-11 items-center gap-2 rounded-md border border-iron-100 px-4 text-sm font-semibold disabled:opacity-50"><ArrowLeft className="h-4 w-4" />Back to edit</button>
        <button type="button" disabled={posting} onClick={onPost} className="flex min-h-11 items-center gap-2 rounded-md bg-brand-gold px-4 text-sm font-semibold text-brand-black disabled:opacity-50"><FolderUp className="h-4 w-4" />{posting ? "Posting…" : postLabel}</button>
      </div>
    </section>
  );
}
