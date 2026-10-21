// The opening moment. The name "Innings." is spelled with cricket kit: the capital I is a bat,
// the small i wears a helmet for its dot, and a ball is bowled in from close to the eye,
// bounces once, and comes to rest as the full stop. Then the curtain lifts off the page.
//
// The bat, helmet and ball are 3D models made by Blender: see animation/*.py. This file and
// the "intro" rules in globals.css only place and move them. There is no script, so it plays
// from the very first paint. It lives in the root layout, which is drawn once per page load:
// moving between pages does not replay it, and a reader who asks for less motion never sees it.

const NAME = "Innings";
const LETTER_GAP_MS = 45; // each letter rises this long after the one before

/** One letter of the name, or the piece of kit that stands in for it. */
function Letter({ letter, first }: { letter: string; first: boolean }) {
  if (first) return <span className="intro-bat" />; // the capital I
  if (letter !== "i") return letter;
  return (
    <>
      {"\u0131" /* an i with no dot: the helmet is its dot */}
      <i className="intro-helmet" />
    </>
  );
}

export function Intro() {
  return (
    <div className="intro" aria-hidden="true">
      <p className="intro-name">
        {[...NAME].map((letter, index) => (
          <span key={index} style={{ animationDelay: `${index * LETTER_GAP_MS}ms` }}>
            <Letter letter={letter} first={index === 0} />
          </span>
        ))}
        <span className="intro-run">
          <span className="intro-ball">
            <i className="intro-spin" />
          </span>
        </span>
      </p>
    </div>
  );
}
