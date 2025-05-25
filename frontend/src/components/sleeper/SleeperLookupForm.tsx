// frontend/src/components/sleeper/SleeperLookupForm.tsx
'use client';

import { useState, FormEvent, useEffect } from 'react';
import {
  resolveSleeperInput,
  fetchSleeperLeaguesForYear,
  fetchSleeperLeagueDetails
} from '@/lib/api/sleeper';
import type {
  LeagueDetails,
  BasicSleeperLeague,
  SleeperResolvedUser
} from '@/types/sleeper';
import { getDisplayableScoringSettings, FormattedScoringSetting } from '@/lib/scoringUtils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';

const MY_SLEEPER_ID_OR_USERNAME = 'beastly';
const CURRENT_YEAR = new Date().getFullYear();
const SELECTABLE_YEARS = [CURRENT_YEAR + 1, CURRENT_YEAR, CURRENT_YEAR - 1, CURRENT_YEAR - 2, CURRENT_YEAR - 3, CURRENT_YEAR - 4, CURRENT_YEAR - 5];

export function SleeperLookupForm() {
  const [inputValue, setInputValue] = useState<string>('');
  const [resolvedUser, setResolvedUser] = useState<SleeperResolvedUser | null>(null);
  const [displayName, setDisplayName] = useState<string | null>(null);
  const [leagues, setLeagues] = useState<BasicSleeperLeague[]>([]);
  const [selectedLeagueId, setSelectedLeagueId] = useState<string>('');
  const [selectedLeagueDetails, setSelectedLeagueDetails] = useState<LeagueDetails | null>(null);
  const [leagueYear, setLeagueYear] = useState<number>(CURRENT_YEAR);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [leagueDetailsError, setLeagueDetailsError] = useState<string | null>(null);
  const [displayableScoring, setDisplayableScoring] = useState<FormattedScoringSetting[]>([]);

  const handleApiResponseError = (errorMessage: string | undefined, defaultMessage: string, isDetailError: boolean = false) => {
    if (isDetailError) {
      setLeagueDetailsError(errorMessage || defaultMessage);
    } else {
      setError(errorMessage || defaultMessage);
    }
  };

  const clearPreviousData = (clearInput: boolean = false) => {
    setError(null);
    setLeagueDetailsError(null);
    setLeagues([]);
    setDisplayName(null);
    setResolvedUser(null);
    setSelectedLeagueId('');
    setSelectedLeagueDetails(null);
    setDisplayableScoring([]);
    if (clearInput) {
      setInputValue('');
    }
  };

  const fetchAndSetLeagues = async (userId: string, yearToFetch: number) => {
    setLeagues([]);
    setSelectedLeagueId('');
    setSelectedLeagueDetails(null);
    setDisplayableScoring([]);
    try {
      const fetchedLeagues = await fetchSleeperLeaguesForYear(userId, yearToFetch);
      setLeagues(fetchedLeagues);
      if (fetchedLeagues.length === 0 && !error) {
        console.log(`No leagues found for user ${userId} in ${yearToFetch}.`);
      }
    } catch (e: any) {
      handleApiResponseError(e.message, "Failed to fetch leagues.");
    }
  };

  const processSleeperData = async (identifier: string) => {
    setIsLoading(true);
    clearPreviousData();

    try {
      const resolvedUserData = await resolveSleeperInput(identifier);
      if (resolvedUserData && resolvedUserData.user_id && !resolvedUserData.error) {
        setResolvedUser(resolvedUserData);
        setDisplayName(resolvedUserData.display_name);
        await fetchAndSetLeagues(resolvedUserData.user_id, leagueYear);
      } else {
        handleApiResponseError(resolvedUserData?.error, 'Could not resolve Sleeper input.');
        setDisplayName(null);
        setResolvedUser(null);
      }
    } catch (e: any) {
      handleApiResponseError(e.message, 'An error occurred while resolving user.');
      setDisplayName(null);
      setResolvedUser(null);
    } finally {
      setIsLoading(false);
    }
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
    setInputValue(MY_SLEEPER_ID_OR_USERNAME);
    await processSleeperData(MY_SLEEPER_ID_OR_USERNAME);
  };

  const handleLeagueChange = async (leagueId: string) => {
    setSelectedLeagueId(leagueId);
    setLeagueDetailsError(null);
    setSelectedLeagueDetails(null);
    setDisplayableScoring([]);

    if (leagueId) {
      setIsLoadingDetails(true);
      try {
        const details = await fetchSleeperLeagueDetails(leagueId);
        if (details) {
          setSelectedLeagueDetails(details);
          setDisplayableScoring(getDisplayableScoringSettings(details.scoring_settings));
        } else {
          handleApiResponseError(undefined, "Could not fetch details for the selected league.", true);
        }
      } catch (e: any) {
        handleApiResponseError(e.message, "An error occurred while fetching league details.", true);
      } finally {
        setIsLoadingDetails(false);
      }
    }
  };

  useEffect(() => {
    if (resolvedUser && resolvedUser.user_id) {
      setIsLoading(true);
      setError(null);
      setLeagueDetailsError(null);
      fetchAndSetLeagues(resolvedUser.user_id, leagueYear).finally(() => {
        setIsLoading(false);
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leagueYear, resolvedUser?.user_id]);

  return (
    <div className="space-y-6 p-4 md:p-6 max-w-xl mx-auto">
      {/* Year Selector */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <Label htmlFor="league-year-select" className="text-sm font-medium whitespace-nowrap">
          Fantasy Season:
        </Label>
        <Select
          value={String(leagueYear)}
          onValueChange={(value) => {
            setLeagueYear(Number(value));
            setSelectedLeagueId('');
            setSelectedLeagueDetails(null);
            setDisplayableScoring([]);
          }}
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

      {/* User Input Form */}
      <form onSubmit={handleSubmit} className="flex items-stretch space-x-2">
        <Input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Enter Sleeper Username or ID"
          className="flex-grow min-w-0"
          disabled={isLoading || isLoadingDetails}
        />
        <Button type="submit" disabled={isLoading || isLoadingDetails} className="whitespace-nowrap">
          {isLoading ? 'Loading User...' : 'Go'}
        </Button>
      </form>
      <Button
        onClick={handleMyIdClick}
        variant="outline"
        disabled={isLoading || isLoadingDetails}
        className="w-full"
      >
        Use My Default ({MY_SLEEPER_ID_OR_USERNAME})
      </Button>

      {/* General Error Display */}
      {error && <p className="text-red-500 text-center text-sm py-2">{error}</p>}

      {/* Display Name */}
      {displayName && !isLoading && (
        <p className="text-xl font-semibold text-center my-4">
          User: <span className="text-blue-600 dark:text-blue-400">{displayName}</span>
        </p>
      )}

      {/* League Selector Dropdown */}
      {resolvedUser && leagues.length > 0 && !isLoading && (
        <div className="space-y-2">
          <Label htmlFor="league-select" className="text-md font-medium">
            Select a league for {leagueYear}:
          </Label>
          <Select onValueChange={handleLeagueChange} value={selectedLeagueId} disabled={isLoadingDetails}>
            <SelectTrigger id="league-select" className="w-full">
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

      {/* No Leagues Found Message */}
      {resolvedUser && leagues.length === 0 && !isLoading && !error && (
        <p className="text-center text-gray-500 dark:text-gray-400 py-2">
          No leagues found for {displayName || 'this user'} in {leagueYear}.
        </p>
      )}

      {/* Loading Indicator for League Details */}
      {isLoadingDetails && <p className="text-center text-blue-500 py-2">Loading league details...</p>}

      {/* Error Message for League Details */}
      {leagueDetailsError && <p className="text-red-500 text-center text-sm py-2">{leagueDetailsError}</p>}

      {/* Display Selected League Details */}
      {selectedLeagueDetails && !isLoadingDetails && (
        <div className="mt-6 p-4 border rounded-md bg-card shadow-lg">
          <h3 className="text-xl font-bold mb-3 text-primary dark:text-primary-foreground">
            {selectedLeagueDetails.name} ({selectedLeagueDetails.season})
          </h3>
          <div className="space-y-2 text-sm">
            <p><span className="font-semibold">League ID:</span> {selectedLeagueDetails.league_id}</p>
            <p><span className="font-semibold">Status:</span> {selectedLeagueDetails.status}</p>
            <p><span className="font-semibold">Total Rosters:</span> {selectedLeagueDetails.total_rosters}</p>

            {selectedLeagueDetails.settings && (
              <>
                <p><span className="font-semibold">League Type:</span> {
                  selectedLeagueDetails.settings.type === 0 ? 'Redraft' :
                  selectedLeagueDetails.settings.type === 1 ? 'Keeper' :
                  selectedLeagueDetails.settings.type === 2 ? 'Dynasty' :
                  selectedLeagueDetails.settings.type !== null && selectedLeagueDetails.settings.type !== undefined ? `Unknown (${selectedLeagueDetails.settings.type})` : 'N/A'
                }</p>
                <p><span className="font-semibold">Playoff Start Week:</span> {selectedLeagueDetails.settings.playoff_week_start || 'N/A'}</p>
              </>
            )}

            <div>
              <h4 className="text-md font-semibold mt-3 mb-1">Roster Positions:</h4>
              <p className="text-xs bg-muted dark:bg-muted/50 p-2 rounded">
                {selectedLeagueDetails.roster_positions ? selectedLeagueDetails.roster_positions.join(', ') : 'N/A'}
              </p>
            </div>

            {/* Updated Scoring Settings Display */}
            <div>
              <h4 className="text-md font-semibold mt-3 mb-1">Key Scoring Settings:</h4>
              {displayableScoring.length > 0 ? (
                <ul className="list-disc list-inside pl-1 text-xs space-y-0.5 bg-muted dark:bg-muted/50 p-3 rounded max-h-48 overflow-y-auto">
                  {displayableScoring.map(setting => (
                    <li key={setting.label}>
                      <span className="font-medium">{setting.label}:</span> {setting.value}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs p-2 bg-muted dark:bg-muted/50 rounded">
                  No distinctive scoring settings found (or all are zero/default).
                </p>
              )}
            </div>

            <div>
              <h4 className="text-md font-semibold mt-3 mb-1">Managers & Rosters ({selectedLeagueDetails.rosters.length}):</h4>
              {selectedLeagueDetails.rosters.length > 0 ? (
                <ul className="list-none pl-0 space-y-1 max-h-60 overflow-y-auto">
                  {selectedLeagueDetails.rosters.sort((a, b) => (b.fpts ?? 0) - (a.fpts ?? 0)).map(roster => (
                    <li key={roster.roster_id} className="text-xs p-2 border-b border-border last:border-b-0">
                      <strong>{roster.owner_display_name || `Roster ID: ${roster.roster_id}`}</strong>
                      <br />
                      Record: ({roster.wins || 0}-{roster.losses || 0}{roster.ties ? `-${roster.ties}` : ''})
                      - PTS: {roster.fpts?.toFixed(2) || '0.00'}
                    </li>
                  ))}
                </ul>
              ) : <p className="text-xs">No rosters found.</p>}
            </div>

            <p className="mt-4 text-xs text-muted-foreground">
              (Full player lists, draft picks, and detailed views can be added next.)
            </p>
          </div>
        </div>
      )}
    </div>
  );
}