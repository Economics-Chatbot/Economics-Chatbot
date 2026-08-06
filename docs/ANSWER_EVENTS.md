# Answer SSE Events

`POST /api/answers` returns `text/event-stream`. A request body uses the existing query shape.

```json
{
  "query": "interest"
}
```

## Direct Answer

When retrieval resolves one answerable term, the existing stream shape is preserved. The backend calls the LLM only in this branch.

```text
event: answer_start
event: delta
event: answer_done
event: done
```

`delta.data.section` remains one of `one_line_definition`, `easy_explanation`, or `example`.

## Suggestions

When retrieval cannot decide a single term but has valid candidates, the backend does not call the LLM and does not send `answer_start`, `delta`, or `answer_done`. It sends a structured `suggestions` event followed by `done`.

```text
event: suggestions
data: {
  "version": 1,
  "status": "candidates",
  "index": 0,
  "query": "interest",
  "count": 1,
  "suggestions": [
    {
      "term_id": 12,
      "term": "interest futures",
      "query": "interest futures",
      "reason": null
    }
  ]
}

event: done
data: {
  "status": "suggestions",
  "completed_indices": [],
  "failed_indices": [],
  "message": null
}
```

The frontend should render `suggestions[]` directly as buttons, chips, or cards. When a user selects an item, send the item's `query` back to `POST /api/answers`. `term_id` is included for stable keys, logging, and analytics.

## Failure

When retrieval has neither an answerable term nor candidates, the backend does not call the LLM and sends the existing `failure` event followed by `done`.

```text
event: failure
event: done
```

Suggestion text must not be embedded in `delta.text` or Markdown strings. Actual answer text is streamed only through `delta`; clickable candidates are sent only through `suggestions`.

## Event Order

Matched:

```text
answer_start
delta
answer_done
done
```

Candidates:

```text
suggestions
done
```

Not found:

```text
failure
done
```

Retrieval or generation error:

```text
error
done
```
