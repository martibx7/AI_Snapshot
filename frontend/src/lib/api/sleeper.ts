// fantasy-frontend/src/lib/api/sleeper.ts

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

interface SleeperResolvedUser {
  user_id: string;
  display_name: string;
  error?: string;
}

interface SleeperLeague {
  league_id: string;
  name: string;
  season: string;
  // Add other relevant league properties returned by your FastAPI endpoint
}

/**
 * Resolves a Sleeper username or ID to a validated user_id and display_name
 * by calling the FastAPI backend.
 */
export const resolveSleeperInput = async (inputValue: string): Promise<SleeperResolvedUser | null> => {
  try {
    // Ensure API_BASE_URL is defined
    if (!API_BASE_URL) {
      throw new Error("API base URL is not configured.");
    }
    const response = await fetch(`${API_BASE_URL}/sleeper/resolve-user`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ input_value: inputValue }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new Error(errorData?.detail || `HTTP error! status: ${response.status}`);
    }
    const data: SleeperResolvedUser = await response.json();
    if (data.error) {
      console.error('Error resolving input:', data.error);
      // Return the object with the error message for the component to display
      return data;
    }
    return data;
  } catch (error) {
    console.error('Failed to resolve Sleeper input:', error);
    // @ts-ignore
    return { error: error.message || 'Unknown error during input resolution' } as SleeperResolvedUser;
  }
};

/**
 * Fetches the leagues for a given Sleeper user_id and year
 * by calling the FastAPI backend.
 */
export const fetchSleeperLeaguesForYear = async (userId: string, year: number): Promise<SleeperLeague[]> => {
  // Ensure API_BASE_URL is defined
  if (!API_BASE_URL) {
    console.error("API base URL is not configured in fetchSleeperLeaguesForYear.");
    throw new Error("API base URL is not configured.");
  }

  const url = `${API_BASE_URL}/sleeper/users/${userId}/leagues/${year}`;
  console.log("Attempting to fetch leagues from URL:", url); // For debugging

  try {
    const response = await fetch(url); // Corrected URL construction
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: `HTTP error! status: ${response.status} and no JSON body` }));
      throw new Error(errorData?.detail || `HTTP error! status: ${response.status}`);
    }
    const leagues: SleeperLeague[] = await response.json();
    return leagues;
  } catch (error) {
    console.error('Failed to fetch Sleeper leagues:', error);
    return []; // Return empty array on error so the UI can handle it gracefully
  }
};