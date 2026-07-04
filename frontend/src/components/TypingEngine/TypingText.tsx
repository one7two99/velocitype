import { Fragment } from "react";
import type { TypingView } from "../../hooks/useTypingEngine";
import "./typing.css";

export function TypingText({ view }: { view: TypingView }) {
  const { words, typed, wordIndex, charIndex, errors, shakeKey } = view;

  return (
    <div className="tf-typing mono" aria-label="lesson text">
      {words.map((word, w) => {
        const typedWord = typed[w] ?? "";
        const extras = typedWord.length > word.length
          ? typedWord.slice(word.length)
          : "";

        return (
          <Fragment key={w}>
            <span className="tf-word">
              {word.split("").map((ch, c) => {
                const key = `${w}:${c}`;
                const isCaret = w === wordIndex && c === charIndex;
                let cls = "tf-char";
                if (errors.has(key)) cls += " tf-char--error";
                else if (
                  w < wordIndex ||
                  (w === wordIndex && c < charIndex)
                ) {
                  cls += " tf-char--correct";
                } else if (w < wordIndex && c >= typedWord.length) {
                  cls += " tf-char--missed";
                } else {
                  cls += " tf-char--pending";
                }
                if (isCaret) cls += " tf-char--caret";
                if (shakeKey === key) cls += " tf-shake";
                return (
                  <span key={c} className={cls}>
                    {ch}
                  </span>
                );
              })}
              {/* Extra characters typed beyond the word length are errors. */}
              {extras.split("").map((ch, i) => (
                <span key={`x${i}`} className="tf-char tf-char--error tf-char--extra">
                  {ch}
                </span>
              ))}
              {/* Caret at end of the current word (nothing left to type). */}
              {w === wordIndex && charIndex >= word.length && (
                <span className="tf-char tf-char--caret tf-char--eol">&nbsp;</span>
              )}
            </span>{" "}
          </Fragment>
        );
      })}
    </div>
  );
}
