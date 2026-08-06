export interface RetrievedTerm {
  term_id: number;
  term_name: string;
  official_definition: string;
  related_terms: string[];
}

export interface TermSuggestion {
  term_id: number;
  term_name: string;
  similarity: number;
  related_terms: string[];
}

export type RetrievalStatus = "answerable" | "suggestions" | "failure";

export interface RetrievalResult {
  status: RetrievalStatus;
  term?: RetrievedTerm;
  suggestions?: TermSuggestion[];
}
