export type DoneStatus =
  | "completed"
  | "partial"
  | "suggestions"
  | "failed"
  | "error";

export type AnswerCardStatus = "streaming" | "completed" | "failure" | "error";
export type StreamUiStatus = "idle" | "loading" | DoneStatus | "cancelled";

export type AnswerEventName =
  | "answer_start"
  | "delta"
  | "answer_done"
  | "suggestions"
  | "failure"
  | "error"
  | "done";

export type Source = { title: string; url?: string | null };
export type AnswerSection = "one_line_definition" | "easy_explanation" | "example";

export interface RetrievedTerm {
  term_id: number;
  term_name: string;
  official_definition: string;
  related_terms: string[];
}

export type Answer = {
  term: string;
  one_line_definition: string;
  easy_explanation: string;
  example: string;
  related_keywords: string[];
  sources: Source[];
};

export type AnswerCard = {
  index: number;
  term: string;
  text: string;
  answer?: Answer;
  status: AnswerCardStatus;
  message?: string;
};

export type AnswerStreamState = {
  status: StreamUiStatus;
  cardsByIndex: Record<number, AnswerCard>;
  suggestions: SuggestionsData[];
  message: string;
};

export type AnswerStartData = {
  index: number;
  term: string;
  related_keywords: string[];
};

export type DeltaData = {
  index: number;
  section: AnswerSection;
  text: string;
};

export type AnswerDoneData = { index: number; answer: Answer };

export type Suggestion = {
  term_id: number;
  term: string;
  query: string;
  summary: string;
  reason?: string | null;
};

export type TermSuggestion = Suggestion;

export type SuggestionsData = {
  version: 1;
  status: "candidates";
  index: number;
  query: string;
  count: number;
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
