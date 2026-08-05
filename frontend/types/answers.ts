export type DoneStatus =
  | "completed"
  | "partial"
  | "suggestions"
  | "failed"
  | "error";

export type AnswerEventName =
  | "answer_start"
  | "delta"
  | "answer_done"
  | "suggestions"
  | "failure"
  | "error"
  | "done";

export type Source = { title: string; url?: string | null };
export type Answer = {
  term: string;
  one_line_definition: string;
  easy_explanation: string;
  example: string;
  related_keywords: string[];
  sources: Source[];
};
export type AnswerStartData = { index: number; term: string };
export type DeltaData = { index: number; text: string };
export type AnswerDoneData = { index: number; answer: Answer };
export type Suggestion = { term: string; reason?: string | null };
export type SuggestionsData = {
  index: number;
  term: string;
  suggestions: Suggestion[];
};
export type FailureData = {
  index: number;
  term: string;
  reason: "not_found" | "low_quality" | "not_economic";
  message: string;
};
export type ErrorData = {
  index: number | null;
  code: string;
  message: string;
  retryable: boolean;
};
export type DoneData = {
  status: DoneStatus;
  completed_indices: number[];
  failed_indices: number[];
  message?: string | null;
};

export type AnswerStreamEvent = {
  event: AnswerEventName;
  data:
    | AnswerStartData
    | DeltaData
    | AnswerDoneData
    | SuggestionsData
    | FailureData
    | ErrorData
    | DoneData;
};
