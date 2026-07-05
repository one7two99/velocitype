import type { LayoutInfo } from "../../api/types";

// Physical geometry per shipped layout. Columns run pinky-outer -> inner-index
// for the left hand and inner-index -> pinky-outer for the right, matching how
// the keys sit on a split board. Cells that are not single trainable characters
// (e.g. "tab", "shift", "'") are drawn as greyed, non-interactive decoration so
// boards like the Corne can show their outer modifier columns truthfully.
interface LayoutGeo {
  left: string[][];
  right: string[][];
  staggerL: number[]; // per-column vertical offset, pinky-outer .. inner
  staggerR: number[]; // per-column vertical offset, inner .. pinky-outer
  thumbsL: string[]; // thumb labels, left hand, drawn left -> right
  thumbsR: string[]; // thumb labels, right hand, drawn left -> right
}

// 3x5 columnar silhouette shared by the Ferris Sweep and the QWERTY baseline.
const STAGGER5_L = [10, 5, 0, 4, 12]; // pinky..inner
const STAGGER5_R = [12, 4, 0, 5, 10]; // inner..pinky
// 3x6: the Corne adds an outer pinky column, sat roughly level with the pinky.
const STAGGER6_L = [10, 10, 5, 0, 4, 12]; // outer,pinky..inner
const STAGGER6_R = [12, 4, 0, 5, 10, 10]; // inner..pinky,outer

const GEO: Record<string, LayoutGeo> = {
  ferris_sweep_colemak_dh: {
    left: [
      ["q", "w", "f", "p", "b"],
      ["a", "r", "s", "t", "g"],
      ["z", "x", "c", "d", "v"],
    ],
    right: [
      ["j", "l", "u", "y", ";"],
      ["m", "n", "e", "i", "o"],
      ["k", "h", ",", ".", "/"],
    ],
    staggerL: STAGGER5_L,
    staggerR: STAGGER5_R,
    thumbsL: ["space", "backspace"],
    thumbsR: ["enter", "shift"],
  },
  qwerty: {
    left: [
      ["q", "w", "e", "r", "t"],
      ["a", "s", "d", "f", "g"],
      ["z", "x", "c", "v", "b"],
    ],
    right: [
      ["y", "u", "i", "o", "p"],
      ["h", "j", "k", "l", ";"],
      ["n", "m", ",", ".", "/"],
    ],
    staggerL: STAGGER5_L,
    staggerR: STAGGER5_R,
    thumbsL: ["space", "backspace"],
    thumbsR: ["enter", "shift"],
  },
  corne_colemak_dh: {
    left: [
      ["tab", "q", "w", "f", "p", "b"],
      ["ctrl", "a", "r", "s", "t", "g"],
      ["shift", "z", "x", "c", "d", "v"],
    ],
    right: [
      ["j", "l", "u", "y", ";", "'"],
      ["m", "n", "e", "i", "o", "bsp"],
      ["k", "h", ",", ".", "/", "ent"],
    ],
    staggerL: STAGGER6_L,
    staggerR: STAGGER6_R,
    thumbsL: ["gui", "space", "enter"],
    thumbsR: ["bsp", "sym", "alt"],
  },
  corne_qwerty: {
    left: [
      ["tab", "q", "w", "e", "r", "t"],
      ["ctrl", "a", "s", "d", "f", "g"],
      ["shift", "z", "x", "c", "v", "b"],
    ],
    right: [
      ["y", "u", "i", "o", "p", "bsp"],
      ["h", "j", "k", "l", ";", "'"],
      ["n", "m", ",", ".", "/", "ent"],
    ],
    staggerL: STAGGER6_L,
    staggerR: STAGGER6_R,
    thumbsL: ["gui", "space", "enter"],
    thumbsR: ["bsp", "sym", "alt"],
  },
};

export interface KeyPos {
  char: string;
  label: string;
  x: number;
  y: number;
  hand: "L" | "R";
  deco: boolean; // true = non-trainable modifier key (greyed, no heat/tooltip)
}

const KEY = 40; // keycap size
const GAP = 6;
const HAND_GAP = 44; // space between the two halves

function geoFor(layout: LayoutInfo): LayoutGeo {
  if (GEO[layout.id]) return GEO[layout.id];
  // Fallback: split the layout's characters into left/right by hand_map.
  const left: string[] = [];
  const right: string[] = [];
  for (const [ch, hand] of Object.entries(layout.hand_map)) {
    (hand === "L" ? left : right).push(ch);
  }
  const chunk = (arr: string[]) =>
    [0, 1, 2].map((r) => arr.slice(r * 5, r * 5 + 5));
  const thumbs = layout.thumb_keys;
  return {
    left: chunk(left),
    right: chunk(right),
    staggerL: STAGGER5_L,
    staggerR: STAGGER5_R,
    thumbsL: [thumbs[0] ?? "", thumbs[1] ?? ""],
    thumbsR: [thumbs[2] ?? "", thumbs[3] ?? ""],
  };
}

export function buildPositions(layout: LayoutInfo): {
  keys: KeyPos[];
  width: number;
  height: number;
  thumbs: { label: string; x: number; y: number }[];
} {
  const geo = geoFor(layout);
  const trainable = new Set(Object.keys(layout.hand_map));
  const keys: KeyPos[] = [];

  const colsL = Math.max(...geo.left.map((r) => r.length));
  const colsR = Math.max(...geo.right.map((r) => r.length));
  const leftWidth = colsL * KEY + (colsL - 1) * GAP;
  const rightWidth = colsR * KEY + (colsR - 1) * GAP;
  const rightStartX = leftWidth + HAND_GAP;

  const place = (
    grid: string[][],
    startX: number,
    stagger: number[],
    hand: "L" | "R",
  ) => {
    grid.forEach((row, r) => {
      row.forEach((cell, c) => {
        if (!cell) return;
        const deco = !(cell.length === 1 && trainable.has(cell));
        keys.push({
          char: cell,
          label: cell,
          x: startX + c * (KEY + GAP),
          y: (stagger[c] ?? 0) + r * (KEY + GAP),
          hand,
          deco,
        });
      });
    });
  };

  place(geo.left, 0, geo.staggerL, "L");
  place(geo.right, rightStartX, geo.staggerR, "R");

  const maxStagger = Math.max(...geo.staggerL, ...geo.staggerR);
  const gridHeight = maxStagger + 3 * KEY + 2 * GAP;

  // Thumb cluster: labels sit under the inner columns of each hand, centred so
  // 2- and 3-key clusters both look balanced under the main block.
  const thumbY = gridHeight + 14;
  const thumbs: { label: string; x: number; y: number }[] = [];
  const step = KEY + GAP;
  const placeThumbs = (labels: string[], anchorRight: boolean, base: number) => {
    // left hand grows leftwards from its inner edge; right hand rightwards from
    // its inner edge, so both clusters hug the centre gap.
    labels.forEach((label, i) => {
      if (!label) return;
      const x = anchorRight
        ? base - (labels.length - i) * step
        : base + i * step;
      thumbs.push({ label, x, y: thumbY });
    });
  };
  placeThumbs(geo.thumbsL, true, leftWidth);
  placeThumbs(geo.thumbsR, false, rightStartX);

  const width = rightStartX + rightWidth;
  const height = thumbY + KEY;
  return { keys, width, height, thumbs };
}

export const KEY_SIZE = KEY;
