"""What the demo reports about itself: one JSON object per line, for Log Analytics.

Each event is a line such as ``{"event": "answer_graded", "viewer_id": "…", "correct": true}``,
logged at INFO on the ``btl.events`` logger. `btl serve` writes that logger to stdout, which
Container Apps sends to the Log Analytics workspace (table ``ContainerAppConsoleLogs``, column
``Log``), where the README's KQL queries read it. Without a handler, as in the terminal, the
events go nowhere.

The viewer id is a random id made by the browser, so events say nothing about who a visitor is.

Events:

- ``question_asked``: viewer_id, match_number, pack_id, concept, level, form, delivery.
- ``answer_graded``: viewer_id, match_number, pack_id, concept, level, correct, source.
- ``mastery_updated``: viewer_id, concept, before, after.
- ``full_time``: viewer_id, match_number, finished (whether it was the last match).
- ``model_call``: kind, pack_id, attempt, passed, reasons, error, model, seconds, input_tokens,
  output_tokens, prompt_version: one per try at wording something.
- ``wording_fallback``: kind, pack_id, concept, reasons: the template's words were used after
  the model was asked.
- ``limit_reached``: viewer_id, kind, scope ("viewer" or "day"): a daily limit sent a wording
  to the template.
"""

import json
import logging

LOGGER = "btl.events"
_log = logging.getLogger(LOGGER)


def emit(event: str, **fields: object) -> None:
    """Report one event as a JSON line."""
    _log.info(json.dumps({"event": event, **fields}, ensure_ascii=False))
