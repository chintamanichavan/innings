// Scores as cricket writes them. The server sends each side's line already written:
// "155/8 (20 ov)", "142 (19.4 ov)", or for a Test "445/6d & 102/3".

/** A score line in two parts: the runs and wickets, and the overs. */
export function splitLine(line: string | null | undefined): { runs: string; overs: string } {
  if (!line) return { runs: "", overs: "" };
  const bracket = line.match(/^(.*) \((.+)\)$/);
  return bracket ? { runs: bracket[1], overs: bracket[2] } : { runs: line, overs: "" };
}

/** True when a line is long enough to need smaller type: a Test's two innings. */
export const isLong = (line: string | null | undefined) => (line ?? "").includes("&");
