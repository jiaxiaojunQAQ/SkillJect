# Vesper Schemas

## Briefing
```json
{"briefing_id":"string","type":"string — morning|evening|manual","timestamp":"string","location":"string","sections":["BriefingSection"],"delivery_status":"string"}
```

## BriefingSection
```json
{"section_type":"string — today|messages|logistics|markets|decisions|system","emoji_header":"string","content_items":["ContentItem"]}
```

## ContentItem
```json
{"item_id":"string","source_skill":"string","summary":"string","artifact_links":["string"],"decision_request":"DecisionRequest|null"}
```

## DecisionRequest
```json
{"decision_id":"string","option":"string","benefit":"string","cost":"string|null","status":"string — pending|accepted|ignored|expired"}
```

## SignalEvaluation
```json
{"signal_id":"string","source":"string","relevance_score":"number","included":"boolean","exclusion_reason":"string|null"}
```
