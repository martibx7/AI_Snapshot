// fantasy-frontend/src/app/sleeper-lookup/page.tsx
import { SleeperLookupForm } from '@/components/sleeper/SleeperLookupForm';

export default function SleeperLookupPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <header className="text-center mb-8">
        <h1 className="text-4xl font-bold tracking-tight">Sleeper League Lookup</h1>
        <p className="text-muted-foreground mt-2">
          Enter a Sleeper username or ID to find their leagues.
        </p>
      </header>
      <main className="max-w-2xl mx-auto">
        <div className="bg-card p-6 sm:p-8 rounded-lg shadow-md"> {/* Added a card-like container */}
            <SleeperLookupForm />
        </div>
      </main>
    </div>
  );
}