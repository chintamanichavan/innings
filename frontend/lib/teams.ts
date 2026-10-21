import { FLAGS } from "./flags";

// Team colours and short codes. We hold no logos; a coloured roundel with a code is ours to use.
const TEAMS: Record<string, [color: string, code: string]> = {
  // IPL
  "Chennai Super Kings": ["#f9cd05", "CSK"],
  "Mumbai Indians": ["#004ba0", "MI"],
  "Royal Challengers Bengaluru": ["#d1171b", "RCB"],
  "Kolkata Knight Riders": ["#3a225d", "KKR"],
  "Sunrisers Hyderabad": ["#f26522", "SRH"],
  "Delhi Capitals": ["#17479e", "DC"],
  "Punjab Kings": ["#dd1f2d", "PBKS"],
  "Rajasthan Royals": ["#e73895", "RR"],
  "Gujarat Titans": ["#1b2133", "GT"],
  "Lucknow Super Giants": ["#0057e2", "LSG"],
  "Deccan Chargers": ["#2d3e50", "DCH"],
  "Gujarat Lions": ["#e04f16", "GL"],
  "Rising Pune Supergiant": ["#6f2c91", "RPS"],
  "Pune Warriors": ["#2f9be3", "PWI"],
  "Kochi Tuskers Kerala": ["#f15a22", "KTK"],
  // BBL
  "Adelaide Strikers": ["#0084d6", "STR"],
  "Brisbane Heat": ["#00a9a5", "HEA"],
  "Hobart Hurricanes": ["#674398", "HUR"],
  "Melbourne Renegades": ["#e4002b", "REN"],
  "Melbourne Stars": ["#00a651", "STA"],
  "Perth Scorchers": ["#f26f21", "SCO"],
  "Sydney Sixers": ["#d81b78", "SIX"],
  "Sydney Thunder": ["#97d700", "THU"],
  // PSL
  "Islamabad United": ["#e21e26", "ISU"],
  "Karachi Kings": ["#0055a5", "KK"],
  "Lahore Qalandars": ["#3aa935", "LQ"],
  "Multan Sultans": ["#01796f", "MS"],
  "Peshawar Zalmi": ["#f6c800", "PZ"],
  "Quetta Gladiators": ["#4b2e83", "QG"],
  // CPL
  "Barbados Royals": ["#e6007e", "BR"],
  "Guyana Amazon Warriors": ["#00843d", "GAW"],
  "Jamaica Tallawahs": ["#00a550", "JT"],
  "St Kitts and Nevis Patriots": ["#d8232a", "SKN"],
  "St Lucia Kings": ["#00a3e0", "SLK"],
  "Trinbago Knight Riders": ["#5c2d91", "TKR"],
  "Antigua and Barbuda Falcons": ["#f7b500", "ABF"],
  // SA20
  "Durban's Super Giants": ["#0a3d91", "DSG"],
  "Joburg Super Kings": ["#f9cd05", "JSK"],
  "MI Cape Town": ["#004ba0", "MICT"],
  "Paarl Royals": ["#e73895", "PR"],
  "Pretoria Capitals": ["#17479e", "PC"],
  "Sunrisers Eastern Cape": ["#f26522", "SEC"],
  // nations
  India: ["#1c6dd0", "IND"],
  Australia: ["#f4c20d", "AUS"],
  England: ["#1a2f5a", "ENG"],
  Pakistan: ["#0b6b3a", "PAK"],
  "South Africa": ["#007749", "SA"],
  "New Zealand": ["#16181a", "NZ"],
  "Sri Lanka": ["#1f3c88", "SL"],
  "West Indies": ["#7b0041", "WI"],
  Bangladesh: ["#006a4e", "BAN"],
  Afghanistan: ["#0b5fb0", "AFG"],
  Ireland: ["#169b62", "IRE"],
  Zimbabwe: ["#d40000", "ZIM"],
  Netherlands: ["#f36c21", "NED"],
  Scotland: ["#1c3f94", "SCO"],
  Nepal: ["#c8102e", "NEP"],
  "United Arab Emirates": ["#6b6e70", "UAE"],
  "United States of America": ["#002868", "USA"],
  Namibia: ["#003580", "NAM"],
  Oman: ["#c8102e", "OMA"],
  Canada: ["#d52b1e", "CAN"],
};

/** A steady number for a name, so an unknown team always gets the same colour. */
function hash(text: string): number {
  let total = 0;
  for (const char of text) total = (total * 31 + char.charCodeAt(0)) >>> 0;
  return total;
}

/** True when a hex colour is light enough to need dark text on it. */
function isLight(hex: string): boolean {
  const value = parseInt(hex.slice(1), 16);
  const red = value >> 16,
    green = (value >> 8) & 255,
    blue = value & 255;
  return 0.299 * red + 0.587 * green + 0.114 * blue > 160;
}

/** A code for a team we have no entry for: its initials, or its first three letters. */
function makeCode(name: string): string {
  const words = name.split(/\s+/);
  const letters = words.length > 1 ? words.map((word) => word[0]).join("") : name;
  return letters.slice(0, 3).toUpperCase();
}

/** The address of a nation's flag, or null for a club or a side with no flag. */
export function flagOf(team: string): string | null {
  const code = FLAGS[team.replace(/ \(W\)$/, "")];
  return code ? `/flags/${code}.svg` : null;
}

/** A team's colour and short code: { color, code, dark }. `dark` means use dark text on it. */
export interface Identity {
  color: string;
  code: string;
  dark: boolean;
}

export function identity(team: string): Identity {
  const name = team.replace(/ \(W\)$/, ""); // a women's side shares its nation's colours
  const known = TEAMS[name];
  if (known) return { color: known[0], code: known[1], dark: isLight(known[0]) };
  return { color: `hsl(${hash(name) % 360} 42% 34%)`, code: makeCode(name), dark: false };
}
