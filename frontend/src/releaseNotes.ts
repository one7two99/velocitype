// In-app release notes, newest first. Mirrors CHANGELOG.md in user-friendly
// wording. Keep this in sync with CHANGELOG.md whenever a release is cut.

export interface ReleaseSection {
  added?: string[];
  changed?: string[];
  fixed?: string[];
}

export interface Release {
  version: string;
  date: string;
  sections: ReleaseSection;
}

export const RELEASES: Release[] = [
  {
    version: "0.12.0",
    date: "2026-07-05",
    sections: {
      added: [
        "New Analysis page (nav item, hotkey 'a') with the three key heatmaps.",
      ],
      changed: [
        "The Dashboard now focuses on progress (trend, personal bests, recent sessions); the per-key heatmaps moved to Analysis.",
      ],
    },
  },
  {
    version: "0.11.0",
    date: "2026-07-05",
    sections: {
      fixed: [
        "The app now reports its real version everywhere (the API previously showed 1.0.0 internally).",
      ],
      added: [
        "A documented versioning policy and a check that keeps the frontend and backend versions in sync.",
      ],
    },
  },
  {
    version: "0.10.0",
    date: "2026-07-05",
    sections: {
      added: [
        "Third key heatmap on the Dashboard: consistency — how steady your timing is per key.",
        "Green means steady, red means erratic (a key you sometimes hit fast and sometimes hesitate on).",
      ],
    },
  },
  {
    version: "0.9.0",
    date: "2026-07-05",
    sections: {
      added: [
        "Two key heatmaps on the Dashboard: one by accuracy and one by speed.",
        "The speed heatmap colours each key against your target — green at or above target, red for slower keys.",
      ],
    },
  },
  {
    version: "0.8.0",
    date: "2026-07-04",
    sections: {
      added: [
        "Target speed (WPM) setting, keybr-style: choose the speed you're aiming for.",
        "The adaptive engine now prioritises keys slower than your target and 'graduates' them once they reach it.",
        "Results show your WPM against the target; the Dashboard adds a target line and a 'Keys @ target' count.",
      ],
    },
  },
  {
    version: "0.7.0",
    date: "2026-07-04",
    sections: {
      added: [
        "App version is now shown in the top bar.",
        "Release notes viewer — click the version to see what's new in each version.",
      ],
    },
  },
  {
    version: "0.6.0",
    date: "2026-07-04",
    sections: {
      added: [
        "AI Coach powered by a local Ollama model — nothing leaves your machine.",
        "Coaching analysis of your stats and AI-generated practice drills that start straight in the Trainer.",
        "Navigation hotkey: press C to open the Coach.",
      ],
    },
  },
  {
    version: "0.5.0",
    date: "2026-07-04",
    sections: {
      added: [
        "Account management in Settings: change password, change email, delete account.",
        "Timed mode: sessions now auto-finish when the time runs out, with a live countdown.",
        "Continuous integration and a project README.",
      ],
      fixed: [
        "Logout / account deletion now reliably signs you out.",
      ],
    },
  },
  {
    version: "0.4.0",
    date: "2026-07-04",
    sections: {
      added: [
        "Navigation hotkeys: T → Trainer, D → Dashboard, S → Settings.",
        "Press D on the results screen to jump to the Dashboard.",
      ],
    },
  },
  {
    version: "0.3.0",
    date: "2026-07-04",
    sections: {
      added: [
        "Results-screen shortcuts: Enter for the next lesson, Space to try again.",
      ],
    },
  },
  {
    version: "0.2.1",
    date: "2026-07-04",
    sections: {
      fixed: [
        "Text no longer shifts when you finish typing a word (caret jitter).",
      ],
    },
  },
  {
    version: "0.2.0",
    date: "2026-07-04",
    sections: {
      added: [
        "The full web app: Trainer with live WPM, accuracy and consistency, a slide-up results panel, and Tab+Enter restart.",
        "Dashboard with a 30-day trend, personal bests, recent sessions, and a Ferris Sweep key heatmap.",
        "Settings: theme, layout, session defaults, and MCP API-key management.",
        "Dark / light / system themes.",
      ],
    },
  },
  {
    version: "0.1.0",
    date: "2026-07-04",
    sections: {
      added: [
        "Backend foundation: accounts and secure login, adaptive lesson engine, and session/stats tracking.",
        "Ferris Sweep Colemak-DH and QWERTY layouts.",
      ],
    },
  },
];
