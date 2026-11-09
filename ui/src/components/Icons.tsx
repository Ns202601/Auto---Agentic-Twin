// Small stroke icons (24px grid), drawn for this app.
import type { SVGProps } from "react";

const base = { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" } as const;

export const IconPipeline = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base} {...p}><circle cx="5" cy="6" r="2" /><circle cx="5" cy="18" r="2" /><circle cx="19" cy="12" r="2" /><path d="M7 6h4a3 3 0 0 1 3 3v0a3 3 0 0 0 3 3M7 18h4a3 3 0 0 0 3-3v0a3 3 0 0 1 3-3" /></svg>
);
export const IconPlus = (p: SVGProps<SVGSVGElement>) => (<svg {...base} {...p}><path d="M12 5v14M5 12h14" /></svg>);
export const IconFolder = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base} {...p}><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /></svg>
);
export const IconLayers = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base} {...p}><path d="m12 3 9 5-9 5-9-5z" /><path d="m3 13 9 5 9-5" /></svg>
);
export const IconSearch = (p: SVGProps<SVGSVGElement>) => (<svg {...base} {...p}><circle cx="11" cy="11" r="6" /><path d="m20 20-4-4" /></svg>);
export const IconCheck = (p: SVGProps<SVGSVGElement>) => (<svg {...base} {...p}><path d="m5 12 5 5 9-10" /></svg>);
export const IconX = (p: SVGProps<SVGSVGElement>) => (<svg {...base} {...p}><path d="M6 6l12 12M18 6 6 18" /></svg>);
export const IconEdit = (p: SVGProps<SVGSVGElement>) => (<svg {...base} {...p}><path d="M4 20h4L19 9l-4-4L4 16z" /></svg>);
export const IconMark = () => (
  <svg viewBox="0 0 32 32" width="18" height="18" aria-hidden="true"><path d="M7 23V9h5l4 8 4-8h1v14" stroke="#fff" strokeWidth="2.6" fill="none" strokeLinejoin="round" /></svg>
);
