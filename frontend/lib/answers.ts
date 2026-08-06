import type {
  AnswerDoneData,
  AnswerEventName,
  AnswerStreamEvent,
  AnswerStartData,
  DeltaData,
  DoneData,
  ErrorData,
  FailureData,
  SuggestionsData,
} from "../types/answers";

export class AnswerNetworkError extends Error {
  constructor() {
    super("네트워크 오류가 발생했어요.");
    this.name = "AnswerNetworkError";
  }
}

export class AnswerResponseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AnswerResponseError";
  }
}

export type StreamHandlers = {
  onAnswerStart: (data: AnswerStartData) => void;
  onDelta: (data: DeltaData) => void;
  onAnswerDone: (data: AnswerDoneData) => void;
  onSuggestions: (data: SuggestionsData) => void;
  onFailure: (data: FailureData) => void;
  onError: (data: ErrorData) => void;
  onDone: (data: DoneData) => void;
};

function parseBlock(block: string): { event: AnswerEventName; data: unknown } | null {
  let event: AnswerEventName | undefined;
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice(7) as AnswerEventName;
    if (line.startsWith("data: ")) data.push(line.slice(6));
  }
  if (!event || data.length === 0) return null;
  return { event, data: JSON.parse(data.join("\n")) };
}

export function parseSseBuffer(buffer: string): {
  events: AnswerStreamEvent[];
  remainder: string;
} {
  const blocks = buffer.split("\n\n");
  const remainder = blocks.pop() ?? "";
  const events = blocks
    .map(parseBlock)
    .filter((event): event is AnswerStreamEvent => event !== null);
  return { events, remainder };
}

export async function streamAnswers(
  query: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  return streamAnswerRequest("/api/answers", { query }, handlers, signal);
}

export async function streamTermAnswer(
  termName: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  return streamAnswerRequest("/api/answers/term", { term_name: termName }, handlers, signal);
}

async function streamAnswerRequest(
  path: string,
  body: Record<string, string>,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(
      `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"}${path}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal,
      },
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new AnswerNetworkError();
  }
  if (!response.ok) throw new AnswerResponseError(`답변 요청 실패 (${response.status})`);
  const contentType = response.headers.get("content-type")?.split(";", 1)[0].trim();
  if (contentType !== "text/event-stream") {
    throw new AnswerResponseError("스트리밍 응답 형식이 아닙니다.");
  }
  if (!response.body) throw new AnswerResponseError("스트리밍 응답을 읽을 수 없습니다.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const handle = (event: AnswerStreamEvent) => {
    switch (event.event) {
      case "answer_start": return handlers.onAnswerStart(event.data as AnswerStartData);
      case "delta": return handlers.onDelta(event.data as DeltaData);
      case "answer_done": return handlers.onAnswerDone(event.data as AnswerDoneData);
      case "suggestions": return handlers.onSuggestions(event.data as SuggestionsData);
      case "failure": return handlers.onFailure(event.data as FailureData);
      case "error": return handlers.onError(event.data as ErrorData);
      case "done": return handlers.onDone(event.data as DoneData);
    }
  };

  while (true) {
    let result: ReadableStreamReadResult<Uint8Array>;
    try {
      result = await reader.read();
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") throw error;
      throw new AnswerNetworkError();
    }
    const { value, done } = result;
    buffer += decoder.decode(value, { stream: !done });
    const parsed = parseSseBuffer(buffer);
    buffer = parsed.remainder;
    parsed.events.forEach(handle);
    if (done) break;
  }
  if (buffer.trim()) parseSseBuffer(`${buffer}\n\n`).events.forEach(handle);
}
