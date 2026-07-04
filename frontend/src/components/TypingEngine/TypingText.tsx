import { Fragment } from "react";
import type { TypingView } from "../../hooks/useTypingEngine";
import "./typing.css";

export function TypingText({ view }: { view: TypingView }) {
  const { words, typed, wordIndex, charIndex, errors, shakeKey } = view;

  return (
    <div className="tf-typing mono" aria-label="lesson text">
      {words.map((word, w) => {
        const typedWord = typed[w] ?? "";
        const extras =
          typedWord.length > word.length ? typedWord.slice(word.length) : "";
        const isCurrent = w === wordIndex;
        // Caret sits after the last typed glyph. When the word is fully typed it
        // rides on the last glyph as a right-side bar (::after) so it never adds
        // layout width and the following words don't jitter.
        const caretAtEnd = isCurrent && charIndex >= word.length;
        const extraChars = extras.split("");
        const wordChars = word.split("");

        return (
          <Fragment key={w}>
            <span className="tf-word">
              {wordChars.map((ch, c) => {
                const key = `${w}:${c}`;
                let cls = "tf-char";
                if (errors.has(key)) cls += " tf-char--error";
                else if (w < wordIndex && c >= typedWord.length)
                  cls += " tf-char--missed";
                else if (w < wordIndex || (isCurrent && c < charIndex))
                  cls += " tf-char--correct";
                else cls += " tf-char--pending";

                // Left beam before the character currently under the cursor.
                if (isCurrent && c === charIndex && charIndex < word.length)
                  cls += " tf-char--caret";
                // Right beam on the final character once the word is complete
                // (no extra characters trailing).
                if (
                  caretAtEnd &&
                  extras.length === 0 &&
                  c === wordChars.length - 1
                )
                  cls += " tf-char--caret-end";
                if (shakeKey === key) cls += " tf-shake";

                return (
                  <span key={c} className={cls}>
                    {ch}
                  </span>
                );
              })}

              {/* Extra characters typed beyond the word length are errors. */}
              {extraChars.map((ch, i) => {
                let cls = "tf-char tf-char--error tf-char--extra";
                if (caretAtEnd && i === extraChars.length - 1)
                  cls += " tf-char--caret-end";
                return (
                  <span key={`x${i}`} className={cls}>
                    {ch}
                  </span>
                );
              })}
            </span>{" "}
          </Fragment>
        );
      })}
    </div>
  );
}
