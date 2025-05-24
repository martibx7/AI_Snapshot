// fantasy-frontend/src/components/sleeper/SleeperLookupForm.tsx
'use client';

import { useState, FormEvent, useEffect } from 'react';
import { resolveSleeperInput, fetchSleeperLeaguesForYear } from '@/lib/api/sleeper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';


interface SleeperLeague {
  league_id: string;
  name: string;
  season: string;
}

const MY_SLEEPER_ID_OR_USERNAME = 'beastly';
const CURRENT_YEAR = new Date().getFullYear();
const SELECTABLE_YEARS = [CURRENT_YEAR + 1, CURRENT_YEAR, CURRENT_YEAR - 1, CURRENT_YEAR - 2, CURRENT_YEAR - 3, CURRENT_YEAR - 4, CURRENT_YEAR - 5];


export function SleeperLookupForm() {
  const [inputValue, setInputValue] = useState<string>('');
  const [resolvedUserId, setResolvedUserId] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState<string | null>(null);
  const [leagues, setLeagues] = useState<SleeperLeague[]>([]);
  const [selectedLeagueId, setSelectedLeagueId] = useState<string>('');
  const [leagueYear, setLeagueYear] = useState<number>(CURRENT_YEAR);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleApiResponseError = (errorMessage: string | undefined, defaultMessage: string) => {
    setError(errorMessage || defaultMessage);
  };

  const clearPreviousData = () => {
    setError(null);
    setLeagues([]);
    setDisplayName(null);
    setResolvedUserId(null);
    setSelectedLeagueId('');
  };

  const fetchAndSetLeagues = async (userId: string, yearToFetch: number) => {
    const fetchedLeagues = await fetchSleeperLeaguesForYear(userId, yearToFetch);
    setLeagues(fetchedLeagues);
    if (fetchedLeagues.length === 0 && !error) { // only show no leagues if no other error occurred
      // This console log is fine, or a subtle UI message if preferred.
      console.log(`No leagues found for user ${userId} in ${yearToFetch}.`);
    }
  };

  const processSleeperData = async (identifier: string) => {
    setIsLoading(true);
    clearPreviousData();

    const resolvedUser = await resolveSleeperInput(identifier);

    if (resolvedUser && resolvedUser.user_id && !resolvedUser.error) {
      setResolvedUserId(resolvedUser.user_id);
      setDisplayName(resolvedUser.display_name);
      await fetchAndSetLeagues(resolvedUser.user_id, leagueYear);
    } else {
      handleApiResponseError(resolvedUser?.error, 'Could not resolve Sleeper input.');
    }
    setIsLoading(false);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!inputValue.trim()) {
      setError('Please enter a Sleeper Username or ID.');
      return;
    }
    await processSleeperData(inputValue.trim());
  };

  const handleMyIdClick = async () => {
    setInputValue(MY_SLEEPER_ID_OR_USERNAME); // Optional: prefill input
    await processSleeperData(MY_SLEEPER_ID_OR_USERNAME);
  };

  const handleLeagueChange = (leagueId: string) => {
    setSelectedLeagueId(leagueId);
    console.log("Selected League ID:", leagueId);
    // TODO: Fetch and display details for this league
  };

  // Effect to refetch leagues when leagueYear changes and a user is already resolved
  useEffect(() => {
    if (resolvedUserId) {
      setIsLoading(true);
      setError(null); // Clear previous year-specific errors
      fetchAndSetLeagues(resolvedUserId, leagueYear).finally(() => setIsLoading(false));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leagueYear, resolvedUserId]); // Only re-run if leagueYear or resolvedUserId changes


  return (
    <div className="space-y-6 p-4 md:p-6 max-w-lg mx-auto">
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <Label htmlFor="league-year-select" className="text-sm font-medium whitespace-nowrap">
          Fantasy Season:
        </Label>
        <Select
            value={String(leagueYear)}
            onValueChange={(value) => setLeagueYear(Number(value))}
        >
            <SelectTrigger id="league-year-select" className="w-full sm:w-[160px]">
                <SelectValue placeholder="Select Year" />
            </SelectTrigger>
            <SelectContent>
                <SelectGroup>
                    <SelectLabel>Years</SelectLabel>
                    {SELECTABLE_YEARS.map(year => (
                        <SelectItem key={year} value={String(year)}>{year}</SelectItem>
                    ))}
                </SelectGroup>
            </SelectContent>
        </Select>
      </div>

      <form onSubmit={handleSubmit} className="flex items-stretch space-x-2">
        <Input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Enter Sleeper Username or ID"
          className="flex-grow min-w-0"
          disabled={isLoading}
        />
        <Button type="submit" disabled={isLoading} className="whitespace-nowrap">
          {isLoading ? 'Loading...' : 'Go'}
        </Button>
      </form>
      <Button
        onClick={handleMyIdClick}
        variant="outline"
        disabled={isLoading}
        className="w-full"
      >
        Use My Default (beastly)
      </Button>

      {error && <p className="text-red-500 text-center text-sm">{error}</p>}

      {displayName && !isLoading && (
        <p className="text-xl font-semibold text-center my-4">
          User: <span className="text-blue-600 dark:text-blue-400">{displayName}</span>
        </p>
      )}

      {resolvedUserId && leagues.length > 0 && !isLoading && (
        <div className="space-y-2">
          <Label htmlFor="league-select" className="text-md font-medium">
            Select a league for {leagueYear}:
          </Label>
          <Select onValueChange={handleLeagueChange} value={selectedLeagueId} disabled={isLoading}>
            <SelectTrigger id="league-select">
              <SelectValue placeholder="Select a league" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectLabel>Leagues</SelectLabel>
                {leagues.map((league) => (
                  <SelectItem key={league.league_id} value={league.league_id}>
                    {league.name} ({league.season})
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>
      )}

      {resolvedUserId && leagues.length === 0 && !isLoading && !error && (
        <p className="text-center text-gray-500 dark:text-gray-400">
          No leagues found for {displayName || 'this user'} in {leagueYear}.
        </p>
      )}

      {selectedLeagueId && (
        <div className="mt-6 p-4 border rounded-md bg-slate-50 dark:bg-slate-800 shadow">
          <h3 className="text-lg font-semibold mb-2">Selected League Info:</h3>
          <p><span className="font-medium">Name:</span> {leagues.find(l => l.league_id === selectedLeagueId)?.name}</p>
          <p><span className="font-medium">ID:</span> {selectedLeagueId}</p>
          <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
            (Full league details will be fetched and displayed in a dedicated section/page later.)
          </p>
        </div>
      )}
    </div>
  );
}