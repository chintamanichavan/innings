// Our own club badges. Each is one shared shield in the club's colour, with a simple symbol
// taken from the plain meaning of the club's NAME (a crown for Kings, a sun for Sunrisers).
// Nothing here is drawn from a club's official badge: those are trademarks we may not use.

/** A symbol drawn in a 24 by 24 box. `line` symbols are stroked, the rest are filled. */
export interface Symbol {
  path: string;
  line?: boolean;
}

export const SYMBOLS = {
  crown: { path: "M4 18 3 8l5 4 4-7 4 7 5-4-1 10z" },
  gem: { path: "M7 4h10l4 5-9 11L3 9z" },
  sun: { path: "M5 18a7 7 0 0 1 14 0zM12 4v3.5M4.2 9l2.4 2.2M19.8 9l-2.4 2.2M2 18h20", line: true },
  star: { path: "M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6-5.4-3-5.4 3 1.2-6-4.5-4.2 6.1-.7z" },
  bolt: { path: "M13.5 2 5 13h5l-1.5 9L18 10h-5z" },
  flame: {
    path:
      "M12 2c1 4 5.5 5.6 5.5 10.6a5.5 5.5 0 0 1-11 0c0-2.2 1-3.4 2.2-4.2" +
      ".1 1.7.8 2.5 1.6 2.8C10 8 10.8 4.6 12 2z",
  },
  wave: {
    path: "M2 9c2.5-3 5-3 7.5 0s5 3 7.5 0 3.5-2 5-1M2 16c2.5-3 5-3 7.5 0s5 3 7.5 0 3.5-2 5-1",
    line: true,
  },
  mountain: { path: "M2 19 9 6l4 6.5 2.5-3.5L22 19z" },
  sword: { path: "M12 2l2.2 3.2V14H9.8V5.2zM7 14h10v2.2H7zM10.9 16.2h2.2V21h-2.2z" },
  // Two and a quarter even turns out from the centre, as a run of short straight lines.
  spiral: {
    path:
      "M13.2 12.0 13.3 12.4 13.3 12.9 13.0 13.4 12.6 13.8 12.0 14.1 11.3 14.1 10.6 14.0 9.9 " +
      "13.5 9.4 12.9 9.1 12.0 9.0 11.0 9.3 10.1 10.0 9.2 10.9 8.6 12.0 8.2 13.2 8.2 14.4 " +
      "8.6 15.5 9.5 16.3 10.6 16.7 12.0 16.6 13.5 16.1 14.9 15.0 16.2 13.7 17.1 12.0 17.5 " +
      "10.2 17.4 8.5 16.8 7.1 15.6 6.1 13.9 5.6 12.0 5.7 10.0 6.5 8.0 7.9 6.4 9.8 5.3 12.0 " +
      "4.7 14.3 4.9 16.5 5.8 18.3 7.4 19.6 9.5 20.1 12.0 19.9 14.6 18.9 17.0 17.1 19.0 14.7 " +
      "20.4 12.0 21.0",
    line: true,
  },
  pillars: {
    path: "M4 8l8-4 8 4v1.6H4zM6 11h2.4v6H6zM10.8 11h2.4v6h-2.4zM15.6 11H18v6h-2.4zM4 18.4h16V20H4z",
  },
  arrow: { path: "M12 3l7 8h-4.5v9h-5v-9H5z" },
  six: { path: "M15.5 5.5C11 5 8 8.5 8 13a4 4 0 1 0 4-4c-1.6 0-3 .8-3.8 2", line: true },
} satisfies Record<string, Symbol>;

export type SymbolName = keyof typeof SYMBOLS;

// The word in a club's name that picks its symbol. The first word found wins, so the more
// telling word comes first: a "Knight Rider" is a sword before a "Rider" is anything else.
const SYMBOL_FOR_WORD: [word: string, symbol: SymbolName][] = [
  ["Sunrisers", "sun"],
  ["Scorchers", "sun"],
  ["Kings", "crown"],
  ["Sultans", "crown"],
  ["Royals", "gem"],
  ["Knight", "sword"],
  ["Gladiators", "sword"],
  ["Warriors", "sword"],
  ["Heat", "flame"],
  ["Challengers", "flame"],
  ["Lions", "flame"],
  ["Tallawahs", "flame"],
  ["Thunder", "bolt"],
  ["Strikers", "bolt"],
  ["Chargers", "bolt"],
  ["Hurricanes", "spiral"],
  ["Qalandars", "spiral"],
  ["Capitals", "pillars"],
  ["Titans", "mountain"],
  ["Giants", "mountain"],
  ["Supergiant", "mountain"],
  ["Stars", "star"],
  ["United", "star"],
  ["Patriots", "star"],
  ["Tuskers", "star"],
  ["Renegades", "arrow"],
  ["Falcons", "arrow"],
  ["Zalmi", "arrow"],
  ["Sixers", "six"],
  ["Mumbai", "wave"],
  ["MI", "wave"], // a city on the sea
];

/** The symbol for a club, or null when its name suggests none. */
export function symbolOf(team: string): SymbolName | null {
  const words = team.split(/[\s']+/);
  return SYMBOL_FOR_WORD.find(([word]) => words.includes(word))?.[1] ?? null;
}
