/**
 * colorUtils.js — WCAG-compliant text contrast utilities.
 *
 * getReadableTextColor(bgHex)
 *   Given any CSS hex color (3 or 6 digit, with or without '#'),
 *   returns '#000000' (black) for light backgrounds or '#FFFFFF' (white)
 *   for dark backgrounds using the WCAG 2.1 relative luminance formula:
 *
 *     L = 0.2126·R_lin + 0.7152·G_lin + 0.0722·B_lin
 *
 *   where each channel is linearised as:
 *     c ≤ 0.04045  →  c / 12.92
 *     c  > 0.04045  →  ((c + 0.055) / 1.055)^2.4
 *
 *   Threshold: luminance < 0.179 → white text, otherwise black text.
 *   (0.179 ≈ midpoint on a perceptual scale, tuned for readability)
 *
 * This function never hardcodes per-palette text colors — it recalculates
 * dynamically for any background, including custom user-picked colors.
 */

/**
 * @param {string} bgHex - A CSS hex colour, e.g. "#1b9e77", "#fff", "013E37"
 * @returns {"#000000"|"#FFFFFF"}
 */
export function getReadableTextColor(bgHex) {
  try {
    let h = String(bgHex).trim().replace(/^#/, '');
    // Expand shorthand: #rgb → #rrggbb
    if (h.length === 3) {
      h = h.split('').map((c) => c + c).join('');
    }
    const r = parseInt(h.slice(0, 2), 16) / 255;
    const g = parseInt(h.slice(2, 4), 16) / 255;
    const b = parseInt(h.slice(4, 6), 16) / 255;

    const linearise = (c) =>
      c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);

    const luminance =
      0.2126 * linearise(r) +
      0.7152 * linearise(g) +
      0.0722 * linearise(b);

    return luminance < 0.179 ? '#FFFFFF' : '#000000';
  } catch {
    return '#FFFFFF'; // safe fallback for any invalid input
  }
}
