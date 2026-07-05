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
    version: "0.20.3",
    date: "2026-07-05",
    sections: {
      fixed: [
        "Session Complete: the Next Lesson / Try Again / Dashboard buttons now always stay on one row (Dashboard no longer wraps).",
      ],
    },
  },
  {
    version: "0.20.2",
    date: "2026-07-05",
    sections: {
      fixed: [
        "The Ferris Sweep keyboard now shows the correct 2 thumb keys per hand (was 3 on the left, 2 on the right).",
      ],
    },
  },
  {
    version: "0.20.1",
    date: "2026-07-05",
    sections: {
      changed: [
        "Dashboard and Analysis data are refreshed reliably right after a session is saved.",
      ],
    },
  },
  {
    version: "0.20.0",
    date: "2026-07-05",
    sections: {
      added: [
        "Recent Sessions on the Dashboard now tag AI coaching drills with an 'AI Drill' badge.",
      ],
    },
  },
  {
    version: "0.19.1",
    date: "2026-07-05",
    sections: {
      changed: [
        "The version badge now sits next to the TypeForge logo (top-left) for better visibility.",
      ],
    },
  },
  {
    version: "0.19.0",
    date: "2026-07-05",
    sections: {
      added: [
        "WPM slider on the Analysis page: drag a target speed to see which keys already reach it (green) and which don't (red), with a live count.",
      ],
    },
  },
  {
    version: "0.18.0",
    date: "2026-07-05",
    sections: {
      added: [
        "Coach drill mode: once started, every Trainer session generates a fresh drill targeting your current weak keys — until you switch back to adaptive.",
        "The Coach page now shows exactly the metrics it uses (weak keys, avg WPM, accuracy, best WPM).",
      ],
      changed: [
        "Generated drills are now verified to actually over-represent your weak keys; if the model's output doesn't, it falls back to the deterministic generator.",
      ],
    },
  },
  {
    version: "0.17.0",
    date: "2026-07-05",
    sections: {
      added: [
        "A thin session progress line on the Trainer: it runs down as your time elapses in timed mode, and fills up with lesson progress in word-count mode.",
      ],
    },
  },
  {
    version: "0.16.0",
    date: "2026-07-05",
    sections: {
      added: [
        "Live pace indicator on the Trainer: a calm meter showing how your rolling 10-second speed compares to your session average (±WPM).",
      ],
    },
  },
  {
    version: "0.15.0",
    date: "2026-07-05",
    sections: {
      changed: [
        "Settings is back in the main navigation; the user menu (top-right) now holds Profile and Log out.",
      ],
    },
  },
  {
    version: "0.14.0",
    date: "2026-07-05",
    sections: {
      changed: [
        "Account menu: your name in the top-right corner now opens a dropdown with Profile, Settings and Log out.",
        "The main navigation is slimmer (Trainer, Dashboard, Analysis, Coach) — Profile and Settings moved into the user menu.",
      ],
    },
  },
  {
    version: "0.13.0",
    date: "2026-07-05",
    sections: {
      added: [
        "New Profile page (nav item, hotkey 'p') for changing your password or email and deleting your account.",
      ],
      changed: [
        "Account settings moved out of Settings into the dedicated Profile page; Settings keeps appearance, training, and API keys.",
      ],
    },
  },
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
