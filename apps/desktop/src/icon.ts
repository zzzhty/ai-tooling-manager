import design from './assets/app-icon.json';

// Trusted bundled geometry; the native exporter reads the same source.
type Rect = { x: number; y: number; width: number; height: number; radius: number; bottomRadius?: number };
type Shape = { paint: string; rect?: Rect; points?: number[][]; strokeWidth?: number };
const color = (rgb: number[]) => `rgb(${rgb.join(',')})`;
const paints = { foreground: color(design.foreground), accent: color(design.accent), background: 'url(#atm)' };
const rect = (r: Rect, fill: string) => {
  const { x, y, width: w, height: h, radius: t } = r;
  const b = r.bottomRadius ?? t;
  // Separate upper/lower corner radii preserve the toolbox lid and square seam.
  const arc = (radius: number, endX: number, endY: number) => radius ? `A${radius},${radius} 0 0 1 ${endX},${endY}` : `L${endX},${endY}`;
  return `<path fill="${fill}" d="M${x+t},${y} H${x+w-t} ${arc(t,x+w,y+t)} V${y+h-b} ${arc(b,x+w-b,y+h)} H${x+b} ${arc(b,x,y+h-b)} V${y+t} ${arc(t,x+t,y)} Z"/>`;
};
const shapes = (design.shapes as Shape[]).map(shape => {
  const paint = paints[shape.paint as keyof typeof paints];
  if (shape.rect) return rect(shape.rect, paint);
  return `<polyline points="${shape.points!.map(point => point.join(',')).join(' ')}" fill="none" stroke="${paint}" stroke-width="${shape.strokeWidth}" stroke-linecap="round" stroke-linejoin="round"/>`;
}).join('');
export const appIconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${design.size} ${design.size}"><defs><linearGradient id="atm" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="${design.size}" y2="${design.size}"><stop stop-color="${color(design.gradientStart)}"/><stop offset="1" stop-color="${color(design.gradientEnd)}"/></linearGradient></defs>${rect(design.background,'url(#atm)')}${shapes}</svg>`;
export const appIconUrl = `data:image/svg+xml,${encodeURIComponent(appIconSvg)}`;
