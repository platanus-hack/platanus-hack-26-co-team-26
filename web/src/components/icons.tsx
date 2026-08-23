import type { SVGProps } from 'react';
const Icon = ({ children, ...props }: SVGProps<SVGSVGElement>) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{children}</svg>;
export const LayersIcon = (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 17l9 5 9-5"/></Icon>;
export const TargetIcon = (p: SVGProps<SVGSVGElement>) => <Icon {...p}><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3"/></Icon>;
export const SignalIcon = (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M5 12.5a10 10 0 0 1 14 0M8 16a6 6 0 0 1 8 0M11 19.5a1.5 1.5 0 0 1 2 0"/></Icon>;
export const CloseIcon = (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="m6 6 12 12M18 6 6 18"/></Icon>;
