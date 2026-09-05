# Model Router v2

## Roadmap

Final Implementation Roadmap #16 — AI Model Selection / Model Router (P1).

## Contract

`build_model_route()` selects a provider/model from an injected provider registry. The Core layer owns routing policy and deterministic selection; it does not own provider SDKs, credentials, or external API calls.

### Supported tasks

- `research`
- `drafting`
- `revision`
- `editorial`

### Supported policies

- `fast`
- `balanced`
- `quality`

Task defaults remain deterministic:

- research → balanced
- drafting → quality
- revision → balanced
- editorial → fast

### Provider types

The registry explicitly supports:

- `openai`
- `anthropic`
- `other`

A registry entry provides provider identity, provider type, model identity, adapter identity, capabilities, availability, and selection priority.

## Selection semantics

1. Validate task and requested policy.
2. Deep-copy and validate the injected registry.
3. Search the requested capability first.
4. If unavailable, follow the deterministic fallback chain for the requested policy.
5. Select the lowest priority value; ties are broken deterministically by provider type, provider, model, and registry key.
6. Emit the effective policy and whether fallback was used.

## Provider boundary

The returned `adapter` is metadata identifying the adapter that a higher layer may invoke. Model Router v2 does **not** instantiate an adapter, read credentials, or call a provider.

Intended architecture:

`Core → Model Router → Provider Adapter → External API`

## Invariants

- No implicit network access.
- No provider SDK dependency in Core.
- No credential access in Core.
- No mutation of the supplied registry.
- Provider/model selection is deterministic for the same inputs.
- Unavailable models are never selected.
- Unsupported provider types, policies, tasks, capabilities, and malformed registry entries are rejected.
- The route schema is strict (`additionalProperties: false`).
