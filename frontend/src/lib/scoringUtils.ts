// frontend/src/lib/scoringUtils.ts

export interface FormattedScoringSetting {
  label: string;
  value: number;
}

interface ScoringRule {
  key: string;
  label: string;
  threshold?: number; // From your old scoring_settings.js
}

// Populated from your scoring_settings.js
// I've processed the list to ensure unique keys, preferring the first label encountered.
export const ALL_SCORING_RULES: ScoringRule[] = [
  { key: 'pass_td', label: 'Pass TD' },
  { key: 'pass_yd', label: 'Pass Yards', threshold: 0.04 },
  { key: 'rec', label: 'PPR' },
  { key: 'rush_td', label: 'Rush TD' },
  { key: 'rec_td', label: 'Rec TD' },
  { key: 'bonus_rec_te', label: 'TEP' },
  { key: 'sack', label: 'Sack' }, // Note: Ambiguity - could be D/ST sack or QB sacked. Assuming D/ST based on general context.
                                  // Sleeper's API might use 'pass_sack' for QB sacked points.
  { key: 'idp_tkl_ast', label: 'IDP Assisted Tackles' },
  { key: 'st_ff', label: 'Special Teams Forced Fumbles' },
  { key: 'idp_ff', label: 'IDP Forced Fumbles' },
  { key: 'pts_allow_7_13', label: 'Points Allowed (7-13)' },
  { key: 'pass_inc', label: 'Incomplete Passes' },
  { key: 'def_st_ff', label: 'Defensive Special Teams Forced Fumbles' },
  { key: 'fum_ret_yd', label: 'Fumble Return Yards' },
  { key: 'bonus_fd_rb', label: 'Bonus RB First Downs' },
  { key: 'bonus_fd_te', label: 'Bonus TE First Downs' },
  { key: 'rush_td_40p', label: 'Rush TD 40+' },
  { key: 'rec_yd', label: 'Receiving Yards' }, // Note: 'pass_yd' and 'rush_yd' are also in your list.
                                            // Sleeper API keys are distinct for these.
  { key: 'fum_rec_td', label: 'Fumble Recovery TD' },
  { key: 'bonus_rush_rec_yd_200', label: 'Bonus 200+ Rush/Rec Yards' },
  { key: 'pts_allow_35p', label: 'Points Allowed (35+)' },
  { key: 'pts_allow_28_34', label: 'Points Allowed (28-34)' },
  { key: 'fum', label: 'Fumbles' }, // Total fumbles, distinct from fum_lost
  { key: 'pr_yd', label: 'Punt Return Yards' },
  { key: 'rush_40p', label: 'Rush 40+' },
  { key: 'bonus_rec_rb', label: 'Bonus RB Receptions' },
  { key: 'yds_allow_0_100', label: 'Yards Allowed (0-100)' },
  { key: 'rush_yd', label: 'Rushing Yards' }, // This is a duplicate key from your list. Taking first label.
  { key: 'bonus_fd_qb', label: 'Bonus QB First Downs' },
  { key: 'idp_qb_hit', label: 'IDP QB Hits' },
  { key: 'bonus_def_int_td_50p', label: 'Bonus 50+ Def Int TD' },
  { key: 'yds_allow_100_199', label: 'Yards Allowed (100-199)' },
  { key: 'bonus_rush_att_20', label: 'Bonus 20+ Rush Att' },
  { key: 'tkl_solo', label: 'Solo Tackles' }, // Generic, could be IDP or D/ST. Assume IDP from context.
  { key: 'blk_kick', label: 'Blocked Kicks' },
  { key: 'rec_td_50p', label: 'Rec TD 50+' },
  { key: 'fgmiss_40_49', label: 'Missed FG 40-49' },
  { key: 'safe', label: 'Safeties' },
  { key: 'bonus_rush_yd_200', label: 'Bonus 200+ Rush Yards' },
  { key: 'rec_td_40p', label: 'Rec TD 40+' },
  { key: 'pass_fd', label: 'Passing First Downs' },
  { key: 'idp_fum_rec', label: 'IDP Fumble Recoveries' },
  { key: 'def_td', label: 'Defensive TD' }, // Team Defense TD
  { key: 'bonus_tkl_10p', label: 'Bonus 10+ Tackles' },
  { key: 'fgm_50p', label: 'FG Made 50+' },
  { key: 'pass_cmp_40p', label: 'Pass Comp 40+' },
  { key: 'tkl', label: 'Tackles' }, // Generic tackle
  { key: 'def_st_td', label: 'Def ST TD' },
  { key: 'bonus_rec_yd_200', label: 'Bonus 200+ Rec Yards' },
  { key: 'rec_10_19', label: 'Rec 10-19' }, // Category for reception length
  { key: 'idp_pass_def', label: 'IDP Pass Def' },
  { key: 'fum_rec', label: 'Fumble Recoveries' }, // Generic fumble recovery
  { key: 'yds_allow_300_349', label: 'Yards Allowed (300-349)' },
  { key: 'def_pass_def', label: 'Def Pass Def' }, // Team pass defended
  { key: 'rush_2pt', label: 'Rush 2PT' },
  { key: 'tkl_loss', label: 'Tackles for Loss' }, // Generic
  { key: 'pass_cmp', label: 'Pass Completions' },
  { key: 'fgmiss_0_19', label: 'Missed FG 0-19' },
  { key: 'def_3_and_out', label: 'Def 3 and Out' },
  { key: 'rec_40p', label: 'Rec 40+' },
  { key: 'pass_sack', label: 'Pass Sacks' }, // This IS likely QB Sacked (negative points usually)
  { key: 'pass_td_50p', label: 'Pass TD 50+' },
  { key: 'xpm', label: 'XP Made' },
  { key: 'bonus_pass_yd_300', label: 'Bonus 300+ Pass Yards' },
  { key: 'bonus_rec_wr', label: 'Bonus WR Rec' },
  { key: 'pts_allow_21_27', label: 'Points Allowed (21-27)' },
  { key: 'yds_allow_500_549', label: 'Yards Allowed (500-549)' },
  { key: 'fgm_20_29', label: 'FG Made 20-29' },
  { key: 'idp_sack', label: 'IDP Sacks' },
  { key: 'rec_5_9', label: 'Rec 5-9' },
  { key: 'yds_allow', label: 'Yards Allowed' }, // Generic, specific ranges are more common
  { key: 'st_tkl_solo', label: 'ST Solo Tackles' },
  { key: 'rush_att', label: 'Rush Attempts' }, // Points for attempt (rare) or just a stat? Assume stat.
  { key: 'fgmiss_20_29', label: 'Missed FG 20-29' },
  { key: 'kr_yd', label: 'Kick Return Yards' },
  { key: 'rec_fd', label: 'Receiving First Downs' },
  { key: 'pts_allow_1_6', label: 'Points Allowed (1-6)' },
  { key: 'fum_lost', label: 'Fumbles Lost' },
  { key: 'def_st_fum_rec', label: 'Def ST Fum Rec' },
  { key: 'int', label: ' Def Interceptions' }, // Team defense interception
  { key: 'idp_pass_def_3p', label: 'IDP Pass Def 3+' },
  { key: 'idp_def_td', label: 'IDP Def TD' },
  { key: 'fgm_0_19', label: 'FG Made 0-19' },
  { key: 'def_2pt', label: 'Def 2PT' }, // Defensive 2PT return
  { key: 'pts_allow_14_20', label: 'Points Allowed (14-20)' },
  { key: 'idp_safe', label: 'IDP Safety' },
  { key: 'idp_int_ret_yd', label: 'IDP Int Ret Yards' },
  { key: 'yds_allow_200_299', label: 'Yards Allowed (200-299)' },
  // { key: 'rec', label: 'Receptions' }, // Already added
  { key: 'fgmiss_30_39', label: 'Missed FG 30-39' },
  { key: 'bonus_sack_2p', label: 'Bonus 2+ Sacks' },
  { key: 'idp_int', label: 'IDP Interceptions' },
  { key: 'ff', label: 'Forced Fumbles' }, // Generic Forced Fumble
  { key: 'bonus_def_fum_td_50p', label: 'Bonus 50+ Def Fum TD' },
  { key: 'fgmiss', label: 'Missed FG' },
  { key: 'st_fum_rec', label: 'ST Fum Rec' },
  { key: 'pass_att', label: 'Pass Attempts' }, // Points for attempt (rare)
  { key: 'idp_tkl_solo', label: 'IDP Solo Tackles' },
  { key: 'int_ret_yd', label: 'Int Ret Yards' }, // Team INT return yards
  { key: 'pass_int_td', label: 'Pass Int TD' }, // Pick 6 thrown by QB
  { key: 'rush_fd', label: 'Rush First Downs' },
  { key: 'idp_tkl_loss', label: 'IDP Tkl Loss' },
  { key: 'bonus_pass_cmp_25', label: 'Bonus 25+ Pass Comp' },
  { key: 'rec_2pt', label: 'Rec 2PT' },
  { key: 'bonus_rush_rec_yd_100', label: 'Bonus 100+ Rush/Rec Yards' },
  { key: 'idp_sack_yd', label: 'IDP Sack Yards' },
  { key: 'fgm', label: 'Field Goals Made' }, // Generic, specific yardages are better
  { key: 'yds_allow_350_399', label: 'Yards Allowed (350-399)' },
  { key: 'def_st_tkl_solo', label: 'Def ST Solo Tackles' },
  { key: 'pass_td_40p', label: 'Pass TD 40+' },
  { key: 'yds_allow_550p', label: 'Yards Allowed (550+)' },
  { key: 'idp_tkl', label: 'IDP Tackles' },
  { key: 'fg_ret_yd', label: 'FG Ret Yards' },
  { key: 'def_4_and_stop', label: 'Def 4th Down Stops' },
  { key: 'pts_allow', label: 'Points Allowed' }, // Generic
  { key: 'bonus_fd_wr', label: 'Bonus WR First Downs' },
  { key: 'def_kr_yd', label: 'Def KR Yards' },
  { key: 'rush_td_50p', label: 'Rush TD 50+' },
  { key: 'xpmiss', label: 'Missed XP' },
  { key: 'idp_fum_ret_yd', label: 'IDP Fum Ret Yards' },
  { key: 'fgm_30_39', label: 'FG Made 30-39' },
  { key: 'idp_blk_kick', label: 'IDP Blocked Kicks' },
  { key: 'rec_20_29', label: 'Rec 20-29' },
  { key: 'tkl_ast', label: 'Assisted Tackles' }, // Generic
  { key: 'yds_allow_400_449', label: 'Yards Allowed (400-449)' },
  { key: 'fgm_yds_over_30', label: 'FG Yards Over 30' },
  { key: 'sack_yd', label: 'Sack Yards' }, // Team sack yards gained by D/ST
  { key: 'rec_30_39', label: 'Rec 30-39' },
  { key: 'def_pr_yd', label: 'Def PR Yards' },
  { key: 'st_td', label: 'ST TD' }, // Special Teams Player TD (not D/ST TD)
  { key: 'blk_kick_ret_yd', label: 'Blocked Kick Ret Yards' },
  { key: 'yds_allow_450_499', label: 'Yards Allowed (450-499)' },
  { key: 'rec_0_4', label: 'Rec 0-4' },
  { key: 'pass_2pt', label: 'Pass 2PT' },
  { key: 'bonus_pass_yd_400', label: 'Bonus 400+ Pass Yards' },
  { key: 'pts_allow_0', label: 'Points Allowed (0)' },
  { key: 'fgmiss_50p', label: 'Missed FG 50+' },
  // { key: 'pass_int', label: 'Pass Int' }, // Already present
  // { key: 'bonus_rush_yd_100', label: 'Bonus 100+ Rush Yards' }, // Already present
  // { key: 'bonus_rec_yd_100', label: 'Bonus 100+ Rec Yards' }, // Already present
  { key: 'def_forced_punts', label: 'Def Forced Punts' },
  { key: 'fgm_yds', label: 'FG Yards' }, // Total FG yards for points (e.g. 0.1 per yard)
  // { key: 'bonus_rec_te', label: 'Bonus TE Rec' }, // Already present as TEP
  { key: 'fgm_40_49', label: 'FG Made 40-49' },
  { key: 'qb_hit', label: 'QB Hits' }, // Usually IDP
  // { key: 'sack', label: 'Sacks' } // Already present
];

// To ensure unique keys in ALL_SCORING_RULES, as your source file has duplicates
const uniqueScoringRules = (): ScoringRule[] => {
  const seenKeys = new Set<string>();
  return ALL_SCORING_RULES.filter(rule => {
    if (seenKeys.has(rule.key)) {
      return false;
    }
    seenKeys.add(rule.key);
    return true;
  });
};
export const UNIQUE_SCORING_RULES = uniqueScoringRules();


// Keys from your old script's displayKeys array, defining what's "important"
const EXPLICIT_DISPLAY_KEYS = ['rec', 'pass_td', 'bonus_rec_te', 'pass_sack'];

export function getDisplayableScoringSettings(
  apiSettings: Record<string, any> | null | undefined
): FormattedScoringSetting[] {
  if (!apiSettings) {
    return [];
  }

  const displaySettings: FormattedScoringSetting[] = [];
  const processedKeys = new Set<string>();

  // Use the processed unique list for lookups and iteration
  UNIQUE_SCORING_RULES.forEach(rule => {
    const settingKey = rule.key;

    if (apiSettings.hasOwnProperty(settingKey) && !processedKeys.has(settingKey)) {
      const value = apiSettings[settingKey];

      if (typeof value === 'number' && value !== 0) {
        const isExplicit = EXPLICIT_DISPLAY_KEYS.includes(settingKey);
        const isBonus = settingKey.startsWith('bonus_');

        if (isExplicit || isBonus) {
          displaySettings.push({
            label: rule.label,
            value: value,
          });
          processedKeys.add(settingKey);
        }
      }
    }
  });

  // Fallback for any "bonus_" keys in apiSettings that might not be in our UNIQUE_SCORING_RULES
  // (e.g., if Sleeper adds a new one)
  for (const apiKey in apiSettings) {
    if (apiSettings.hasOwnProperty(apiKey) && !processedKeys.has(apiKey) && apiKey.startsWith('bonus_')) {
        const value = apiSettings[apiKey];
        if (typeof value === 'number' && value !== 0) {
            const knownRule = UNIQUE_SCORING_RULES.find(r => r.key === apiKey);
            displaySettings.push({
                label: knownRule ? knownRule.label : apiKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                value: value,
            });
            // processedKeys.add(apiKey); // Not strictly needed here as we iterate all apiKeys once
        }
    }
  }

  displaySettings.sort((a, b) => a.label.localeCompare(b.label));
  return displaySettings;
}