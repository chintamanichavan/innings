// The keyboard tagger. One field at a time: a number key picks a value and moves on, space
// means "could not see", and the last field saves the ball and moves to the next one.
// Pace and angle start from this bowler's last tagged ball, so Enter keeps them.

"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { api } from "@/lib/api";
import { type Sport, link } from "@/lib/sport";
import { store, useStored } from "@/lib/store";
import {
  AFTER_CONTACT,
  FIELD_LABEL,
  type TagBall,
  type TagField,
  type TagMatch,
  type Tags,
  saveTag,
  scored,
} from "@/lib/tagging";

const KEYS = "1234567890";
const CARRIED = ["pace", "angle"];

/** A fresh draft for a ball: its saved tag, or pace and angle from the bowler's last tag. */
function draftFor(balls: TagBall[], at: number, fields: TagField[]): Tags {
  const ball = balls[at];
  if (ball.tag) return { ...ball.tag.tags };
  const draft: Tags = Object.fromEntries(fields.map((field) => [field.name, null]));
  for (let i = at - 1; i >= 0; i--) {
    const before = balls[i];
    if (before.bowler_id === ball.bowler_id && before.tag) {
      for (const name of CARRIED) draft[name] = before.tag.tags[name];
      break;
    }
  }
  return draft;
}

export function Tagger({ sport, matchId }: { sport: Sport; matchId: string }) {
  const tagger = useStored("tagger", "");
  const deathOnly = useStored("tag.death", true);
  const [match, setMatch] = useState<TagMatch | null>(null);
  const [fields, setFields] = useState<TagField[]>([]);
  const [at, setAt] = useState(-1);
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<Tags>({});
  const [clock, setClock] = useState("");
  const [differs, setDiffers] = useState(false);
  const [problem, setProblem] = useState("");
  const [session, setSession] = useState({ count: 0, started: 0 });
  const clockInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!tagger) return;
    Promise.all([api<TagMatch>(`tag/match/${matchId}`, { tagger }), api<TagField[]>("tag/fields")])
      .then(([loaded, known]) => {
        setMatch(loaded);
        setFields(known);
      })
      .catch((error: Error) => setProblem(error.message));
  }, [matchId, tagger]);

  const shown = useMemo(
    () =>
      match ? match.balls.flatMap((ball, i) => (!deathOnly || ball.phase === "death" ? [i] : [])) : [],
    [match, deathOnly],
  );

  const open = useCallback(
    (index: number) => {
      if (!match) return;
      setAt(index);
      setStep(0);
      setDraft(draftFor(match.balls, index, fields));
      setClock(match.balls[index].tag?.clock ?? "");
      setDiffers(match.balls[index].tag?.differs ?? false);
      setProblem("");
    },
    [match, fields],
  );

  // Start at the first shown ball not yet tagged.
  useEffect(() => {
    if (!match || !fields.length || (at >= 0 && shown.includes(at))) return;
    const first = shown.find((i) => !match.balls[i].tag) ?? shown[0];
    if (first !== undefined) open(first);
  }, [match, fields, shown, at, open]);

  const move = useCallback(
    (by: number) => {
      const place = shown.indexOf(at);
      const next = shown[place + by];
      if (next !== undefined) open(next);
    },
    [shown, at, open],
  );

  const save = useCallback(
    async (tags: Tags) => {
      if (!match || at < 0) return;
      const ball = match.balls[at];
      try {
        const tag = await saveTag({
          tagger,
          match_id: matchId,
          innings: ball.innings,
          over: ball.over,
          ball: ball.ball,
          tags,
          clock: clock || null,
          differs,
        });
        const balls = match.balls.map((b, i) => (i === at ? { ...b, tag } : b));
        setMatch({ ...match, balls });
        setSession((s) => ({ count: s.count + 1, started: s.started || Date.now() }));
        const place = shown.indexOf(at);
        const next = shown[place + 1];
        if (next === undefined) {
          setDraft(tags);
          setStep(fields.length);
        } else {
          setAt(next);
          setStep(0);
          setDraft(draftFor(balls, next, fields));
          setClock(balls[next].tag?.clock ?? "");
          setDiffers(balls[next].tag?.differs ?? false);
        }
      } catch (error) {
        setProblem((error as Error).message);
      }
    },
    [match, at, tagger, matchId, clock, differs, shown, fields],
  );

  const choose = useCallback(
    (value: string | null) => {
      const field = fields[step];
      if (!field) return;
      const tags = { ...draft, [field.name]: value };
      // Nothing touched the bat: the fields about contact and where it went do not apply.
      const missed =
        (field.name === "shot" && (value === "leave" || value === "missed")) ||
        (field.name === "contact" && value === "missed");
      if (missed) {
        for (const name of AFTER_CONTACT) tags[name] = null;
        if (field.name === "shot" && value === "missed") tags.contact = "missed";
      }
      setDraft(tags);
      if (missed || step + 1 >= fields.length) void save(tags);
      else setStep(step + 1);
    },
    [fields, step, draft, save],
  );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement) {
        if (event.key === "Enter" || event.key === "Escape") event.target.blur();
        return;
      }
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      const field = fields[step];
      const number = KEYS.indexOf(event.key);
      if (field && number >= 0 && number < field.values.length) choose(field.values[number]);
      else if (event.key === " ") choose(null);
      else if (event.key === "Enter") void save(draft);
      else if (event.key === "Backspace") setStep((s) => Math.max(0, s - 1));
      else if (event.key === "ArrowRight") move(1);
      else if (event.key === "ArrowLeft") move(-1);
      else if (event.key === "d") setDiffers((d) => !d);
      else if (event.key === "c") clockInput.current?.focus();
      else return;
      event.preventDefault();
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [fields, step, draft, choose, save, move]);

  if (!tagger)
    return (
      <p className="note">
        Choose a tagger name on <Link href={link(sport, "tag")}>the tagging page</Link> first.
      </p>
    );
  if (!match || at < 0) return <p className="note">{problem || "Loading the match..."}</p>;

  const ball = match.balls[at];
  const done = shown.filter((i) => match.balls[i].tag).length;
  const minutes = session.started ? (Date.now() - session.started) / 60000 : 0;
  return (
    <>
      <p className="kicker">
        <Link href={link(sport, "tag")}>Ball tagging</Link>
        <span className="sep">{match.date}</span>
        <span className="sep">tagging as {tagger}</span>
      </p>
      <h1 className="page">
        {match.team1} v {match.team2}
      </h1>
      <div className="filters">
        <label>
          <input
            type="checkbox"
            checked={deathOnly}
            onChange={(event) => store.set("tag.death", event.target.checked)}
          />
          Death overs only
        </label>
        <span className="note">
          {done} of {shown.length} balls tagged
          {session.count > 1 &&
            minutes > 0 &&
            ` · this session ${((session.count - 1) / minutes).toFixed(1)} a minute`}
        </span>
      </div>

      <section className="tagger">
        <div className="tag-ball">
          <p className="tag-where">
            Innings {ball.innings} ·{" "}
            <b>
              {ball.over}.{ball.ball}
            </b>{" "}
            · {ball.bowler} to {ball.batter}
          </p>
          <p className="tag-scored">
            Scorecard: <b>{scored(ball)}</b>
            {ball.tag && <span className="chip">tagged</span>}
            {differs && <span className="chip warn">I saw something different (d)</span>}
          </p>
          <label className="tag-clock">
            Video time (c){" "}
            <input
              ref={clockInput}
              value={clock}
              placeholder="1:02:03"
              onChange={(event) => setClock(event.target.value.trim())}
            />
          </label>
        </div>

        <div className="tag-fields">
          {fields.map((field, index) => (
            <div key={field.name} className={`tag-field${index === step ? " on" : ""}`}>
              <button type="button" className="tag-name" onClick={() => setStep(index)}>
                {FIELD_LABEL[field.name] ?? field.name}
              </button>
              <div className="tag-values">
                {field.values.map((value, i) => (
                  <button
                    type="button"
                    key={value}
                    className={draft[field.name] === value ? "chip on" : "chip"}
                    onClick={() => {
                      setStep(index);
                      setDraft({ ...draft, [field.name]: value });
                    }}
                  >
                    {index === step && <kbd>{KEYS[i]}</kbd>}
                    {value}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
        {problem && <p className="note warn">{problem}</p>}
        <p className="note">
          <kbd>1</kbd>–<kbd>0</kbd> pick · <kbd>space</kbd> could not see · <kbd>Enter</kbd> save now ·{" "}
          <kbd>Backspace</kbd> back a field · <kbd>←</kbd> <kbd>→</kbd> ball · <kbd>d</kbd> what I saw
          differs from the scorecard · <kbd>c</kbd> video time. Line is from the batter&apos;s side:
          &quot;wide of off&quot; is not a wide. Zones are the batter&apos;s, so they flip for a
          left-hander.
        </p>
      </section>

      <div className="tag-strip">
        {shown.map((i) => {
          const b = match.balls[i];
          return (
            <button
              type="button"
              key={i}
              className={`tag-dot${b.tag ? " done" : ""}${i === at ? " here" : ""}`}
              title={`${b.innings}: ${b.over}.${b.ball} ${scored(b)}`}
              onClick={() => open(i)}
            >
              {b.wicket ? "W" : b.runs}
            </button>
          );
        })}
      </div>
    </>
  );
}
