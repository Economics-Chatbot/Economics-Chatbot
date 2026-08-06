export type ScreenState =
  | "home-idle"
  | "home-typing"
  | "query-transition"
  | "searching"
  | "answer-streaming"
  | "answer-done"
  | "suggestions"
  | "failure"
  | "error";

export type CharacterState = "default" | "blink" | "thinking" | "error";
