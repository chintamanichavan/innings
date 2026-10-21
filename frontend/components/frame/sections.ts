// The site's sections: what the header menu and the phone tab bar list.

export const SECTIONS: [page: string, name: string][] = [
  ["front", "Front page"],
  ["scores", "Scores"],
  ["news", "News"],
  ["forecasts", "Forecasts"],
  ["lab", "The lab"],
  ["stream", "The stream"],
  ["puzzles", "Puzzles"],
  ["players", "Players"],
  ["teams", "Teams"],
  ["matches", "Matches"],
  ["records", "Records"],
  ["following", "Following"],
  ["methods", "How it works"],
];

export const TABS: [page: string, name: string][] = [
  ["front", "Front"],
  ["scores", "Scores"],
  ["forecasts", "Forecasts"],
  ["lab", "Lab"],
  ["sections", "More"],
];

// A page that is not itself in the menus lights up the section it belongs to.
const SECTION_OF: Record<string, string> = {
  player: "players",
  team: "teams",
  match: "matches",
  replay: "matches",
  venue: "sections",
  venues: "sections",
  compare: "sections",
};
const TAB_OF: Record<string, string> = {
  front: "front",
  scores: "scores",
  forecasts: "forecasts",
  lab: "lab",
};

export const sectionOf = (page: string) => SECTION_OF[page] ?? page;
export const tabOf = (page: string) => TAB_OF[page] ?? "sections";
