import { keyFigures } from "@/lib/format";

/** A sentence with its key figures set in bold. */
export function Marked({ text }: { text: string }) {
  return (
    <>
      {keyFigures(text).map((piece, index) =>
        piece.key ? <mark key={index}>{piece.text}</mark> : piece.text,
      )}
    </>
  );
}
