
# Fantasy Sports Platform - Frontend

This is the Next.js frontend for the Fantasy Sports Platform. It provides the user interface for interacting with fantasy leagues, players, projections, and other platform features, powered by the [Fantasy Backend API](#).

---

## Tech Stack 🚀

The frontend is built using modern, efficient technologies to ensure a responsive and engaging user experience:

- **Framework:** [Next.js](https://nextjs.org/) (using App Router)  
  *Role:* Primary web framework for building the UI  
  *Rationale:* File-based routing, SSR/SSG/CSR flexibility, API routes, and image/code optimization.

- **Language:** [TypeScript](https://www.typescriptlang.org/)  
  *Role:* Superset of JavaScript adding static type checking  
  *Rationale:* Improves code quality, maintainability, and developer experience.

- **Styling:** [Tailwind CSS](https://tailwindcss.com/)  
  *Role:* Utility-first CSS framework  
  *Rationale:* Enables rapid, consistent styling with minimal custom CSS.

- **UI Components (Foundation):** [ShadCN UI](https://ui.shadcn.com/)  
  *Role:* Accessible, unstyled React components using Tailwind  
  *Rationale:* Full control over styling, accessibility-first.

- **State Management (Client-Side):**
  - [Zustand](https://zustand-demo.pmnd.rs/): for dynamic/global UI state.
  - [React Context](https://react.dev/learn/passing-data-deeply-with-context): for static/global data like themes or login state.

- **Server State & Data Fetching:** [React Query (TanStack Query)](https://tanstack.com/query/latest)  
  *Role:* Handles fetching/caching/syncing backend data  
  *Rationale:* Simplifies server-state logic with background and optimistic updates.

- **HTTP Client:** Native Fetch API (currently), [Axios](https://axios-http.com/) can be added if needed.

- **Charting/Data Visualization:** [Plotly.js](https://plotly.com/javascript/) via `react-plotly.js`  
  *Role:* Rich charts and visualizations  
  *Rationale:* Balances interactivity with flexibility for fantasy-related stats.

---

## Project Structure Overview

```text
fantasy-frontend/
├── public/                        # Static assets (images, fonts, etc.)
├── src/
│   ├── app/
│   │   └── sleeper-lookup/
│   │       └── page.tsx          # Page for Sleeper user/league lookup
│   ├── components/
│   │   ├── sleeper/
│   │   │   └── SleeperLookupForm.tsx
│   │   └── ui/                   # ShadCN UI components
│   ├── hooks/                    # Custom React hooks
│   ├── lib/
│   │   └── api/
│   │       └── sleeper.ts        # API utils for backend
│   └── store/                    # Zustand stores (if any)
├── .env.local                    # Local env vars (ignored by Git)
├── .eslintrc.json
├── .gitignore
├── components.json               # ShadCN UI config
├── next.config.mjs               # Next.js config
├── package.json
├── postcss.config.js
├── tailwind.config.ts
├── tsconfig.json
└── README.md
```

---

## Getting Started 🛠️

### Prerequisites

- Node.js (LTS recommended — v18, v20, or v22)
- Git
- [Fantasy Backend API](#) running locally (typically at `http://127.0.0.1:8000`)

### Setup Steps

1. **Clone the Repository**

```bash
git clone <URL_of_your_fantasy-frontend_repo>
cd fantasy-frontend
```

2. **Install Dependencies**

```bash
npm install
\`\`\`

> If you hit peer dependency issues (especially with React 19), try:  
> `npm install --legacy-peer-deps`

3. **Set Up Environment Variables**

Create `.env.local` in the project root:

```env
# .env.local
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

> Restart the dev server if you change this file.

4. **Initialize ShadCN UI (if first-time setup)**

```bash
npx shadcn@latest init
```

5. **Add Required ShadCN Components**

```bash
npx shadcn@latest add button
npx shadcn@latest add input
npx shadcn@latest add select
npx shadcn@latest add label
```

> If prompted about peer deps, use `--legacy-peer-deps`.

6. **Run the Dev Server**

```bash
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)  
Try navigating to `/sleeper-lookup` to test the current feature.

---

## Development Workflow

- **Current Feature:**  
  `/sleeper-lookup` allows user to input a Sleeper username, validates, and fetches leagues.

- **Pages & Layouts:**  
  Go in `src/app/`.

- **Reusable Components:**  
  Go in `src/components/` — ShadCN UI in `components/ui/`.

- **Styling:**  
  Use Tailwind utility classes.

- **Data Fetching:**  
  API functions live in `src/lib/api/` — will use React Query going forward.

- **Global State:**  
  Currently just `useState`. Will use Zustand or Context as needed.

---

## TODO / Future Enhancements 📝

**Current Focus:**

- Implement detailed League View (rosters, draft picks, player DB data).

**UI & App Development:**

- Build pages: Dashboard, League views, Player detail, Standings.
- Implement user profile + settings.

**Components & Design:**

- Integrate more ShadCN UI components.
- Implement dark mode theming.

**Authentication:**

- Add registration, login, logout flows.
- Protect routes via auth.

**Data Visualization:**

- Add dynamic charts for player stats & projections via Plotly.js.

…and more from the backend's shared TODO roadmap.
```
