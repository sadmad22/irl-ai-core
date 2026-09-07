# YouTube Videos v1

## Roadmap position

Roadmap item #20 — YouTube Videos (P2). The Final Implementation Roadmap identifies YouTube API as the external discovery source.

## Audit conclusion

No existing YouTube video contract was found in the Core. Article Draft remains responsible for article sections/claims/evidence, while YouTube is introduced as a separate downstream editorial-media contract. The Core must not perform live YouTube API calls during deterministic contract construction.

## Architecture

```text
Outline Editor
    ↓
YouTube API discovery / verification (upstream integration)
    ↓
YouTube Videos Contract
    ↓
Editorial / publication formatter
```

## Contract

```text
youtube_videos
├── enabled
├── required
├── max_videos
├── placement
├── source_requirement
└── videos[]
    ├── youtube_video_id
    ├── url
    ├── title
    ├── channel_title
    ├── published_at
    ├── duration_seconds
    ├── thumbnail_url
    ├── relevance_score
    └── source
```

## Final invariants

1. Upstream Outline Editor must be `outline_editor_ready`.
2. Required lineage identifiers must be present and preserved.
3. `required=true` requires `enabled=true`.
4. `enabled=false` requires `max_videos=0` and produces no selected videos.
5. `enabled=true` requires `max_videos >= 1`.
6. Required YouTube videos require at least one verified candidate.
7. Candidate IDs must be unique.
8. Candidate source must be `youtube_api`.
9. Candidate URLs must be canonical `https://www.youtube.com/watch?v=...` URLs.
10. Relevance scores must be numeric values from 0 to 1.
11. Selection is deterministic: relevance descending, then video ID ascending.
12. Unknown candidate/settings fields are rejected.
13. The engine does not invent video metadata.

## Architectural boundary

The contract consumes already discovered/verified API candidates. It does not call YouTube, generate metadata, insert iframe/HTML markup, rewrite article prose, publish to WordPress, or select an LLM/provider.

## Out of scope

- YouTube API transport implementation
- live search credentials or secrets
- iframe/HTML rendering
- WordPress publication
- External Linking (#21)
- Internal Linking (#22)
- LLM-based video selection
- SEO keyword stuffing
