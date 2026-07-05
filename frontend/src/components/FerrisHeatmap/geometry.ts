import type { LayoutInfo } from "../../api/types";

// Canonical physical grids (3 rows x 5 cols per hand) for the shipped layouts.
// Columns run pinky -> inner-index for the left hand and inner-index -> pinky
// for the right, matching how the keys sit on a split board.
const GRIDS: Record<string, { left: string[][]; right: string[][] }> = {
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
  },
};

export interface KeyPos {
  char: string;
  x: number;
  y: number;
  hand: "L" | "R";
}

const KEY = 40; // keycap size
const GAP = 6;
const HAND_GAP = 44; // space between the two halves
const COL_STAGGER_L = [10, 5, 0, 4, 12]; // pinky..inner (columnar silhouette)
const COL_STAGGER_R = [12, 4, 0, 5, 10]; // inner..pinky

function gridFor(layout: LayoutInfo) {
  if (GRIDS[layout.id]) return GRIDS[layout.id];
  // Fallback: split the layout's characters into left/right by hand_map.
  const left: string[] = [];
  const right: string[] = [];
  for (const [ch, hand] of Object.entries(layout.hand_map)) {
    (hand === "L" ? left : right).push(ch);
  }
  const chunk = (arr: string[]) =>
    [0, 1, 2].map((r) => arr.slice(r * 5, r * 5 + 5));
  return { left: chunk(left), right: chunk(right) };
}

export function buildPositions(layout: LayoutInfo): {
  keys: KeyPos[];
  width: number;
  height: number;
  thumbs: { label: string; x: number; y: number }[];
} {
  const { left, right } = gridFor(layout);
  const keys: KeyPos[] = [];

  const leftWidth = 5 * KEY + 4 * GAP;
  const rightStartX = leftWidth + HAND_GAP;

  const place = (
    grid: string[][],
    startX: number,
    stagger: number[],
    hand: "L" | "R",
  ) => {
    grid.forEach((row, r) => {
      row.forEach((char, c) => {
        if (!char) return;
        keys.push({
          char,
          x: startX + c * (KEY + GAP),
          y: (stagger[c] ?? 0) + r * (KEY + GAP),
          hand,
        });
      });
    });
  };

  place(left, 0, COL_STAGGER_L, "L");
  place(right, rightStartX, COL_STAGGER_R, "R");

  const maxStagger = Math.max(...COL_STAGGER_L, ...COL_STAGGER_R);
  const gridHeight = maxStagger + 3 * KEY + 2 * GAP;

  // Thumb cluster: the Ferris Sweep has 2 thumb keys per hand, sitting under the
  // inner columns (index / inner-index).
  const thumbLabels = layout.thumb_keys.slice(0, 4);
  const thumbs: { label: string; x: number; y: number }[] = [];
  const thumbY = gridHeight + 14;
  for (let i = 0; i < 2; i++) {
    // left hand: two inner (right-most) columns
    thumbs.push({
      label: thumbLabels[i] ?? "",
      x: leftWidth - (2 - i) * (KEY + GAP),
      y: thumbY,
    });
    // right hand: two inner (left-most) columns
    thumbs.push({
      label: thumbLabels[i + 2] ?? "",
      x: rightStartX + i * (KEY + GAP),
      y: thumbY,
    });
  }

  const width = rightStartX + leftWidth;
  const height = thumbY + KEY;
  return { keys, width, height, thumbs };
}

export const KEY_SIZE = KEY;
