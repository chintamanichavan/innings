// What the value columns of a slice mean, in plain words.

export function SliceNotes({ role }: { role: "bat" | "bowl" }) {
  return (
    <p className="note">
      <b>RAE</b> is runs added above an average {role === "bat" ? "batter" : "bowler"} in the same match
      situation, counting the cost of a wicket. <b>WPA</b> is win chance added: +1.00 is one whole
      match.
      {role === "bowl" && (
        <>
          {" "}
          <b>xW</b> is the wickets an average bowler would take on the same balls (same format, over and
          wickets down). <b>W+</b> is wickets taken above that.
        </>
      )}
    </p>
  );
}
