                              ┌──────────────────────────────────────┐
                              │          User / Client               │
                              │ chatbot UI, web app, curl, future    │
                              │ mobile / WhatsApp / frontend         │
                              └──────────────────┬───────────────────┘
                                                 │
                                                 ▼
                              ┌──────────────────────────────────────┐
                              │        Chatbot Service API           │
                              │ /health                              │
                              │ /sessions/start                      │
                              │ /sessions/{id}                       │
                              │ /sessions/{id}/message               │
                              │ /sessions/{id}/attachments           │
                              │ /sessions/{id}/submit               │
                              └──────────────────┬───────────────────┘
                                                 │
                      ┌──────────────────────────┼──────────────────────────┐
                      │                          │                          │
                      ▼                          ▼                          ▼
        ┌────────────────────────┐   ┌────────────────────────┐   ┌────────────────────────┐
        │  Session Service       │   │ Message Ingestion      │   │ Attachment Service     │
        │ create / track chat    │   │ update intake state,   │   │ save image / voice /   │
        │ sessions + lifecycle   │   │ call graph-core, ask   │   │ video metadata         │
        │                        │   │ next question          │   │                        │
        └─────────────┬──────────┘   └─────────────┬──────────┘   └─────────────┬──────────┘
                      │                            │                            │
                      ▼                            ▼                            ▼
        ┌────────────────────────┐   ┌────────────────────────┐   ┌────────────────────────┐
        │ Intake State Service   │   │ Question Planner       │   │ Response Assembly      │
        │ collected fields,      │   │ next missing field /   │   │ safe conversational    │
        │ missing fields,        │   │ next bot question      │   │ response formatting    │
        │ provisional state      │   │                        │   │                        │
        └─────────────┬──────────┘   └─────────────┬──────────┘   └─────────────┬──────────┘
                      │                            │                            │
                      └──────────────┬─────────────┴──────────────┬─────────────┘
                                     │                            │
                                     ▼                            ▼
                    ┌──────────────────────────────────────┐   ┌──────────────────────────┐
                    │     Chatbot Service PostgreSQL       │   │     File Storage         │
                    │ chat_sessions                        │   │ image / voice / video    │
                    │ chat_messages                        │   │ attachments              │
                    │ chat_attachments                     │   │                          │
                    └──────────────────┬───────────────────┘   └──────────────────────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────────────┐
                    │        Graph-Core FastAPI API        │
                    │ /health                              │
                    │ /graph/*                             │
                    │ /search, /search/semantic            │
                    │ /intake/assess                       │
                    │ /triage/assess                       │
                    │ /cases/intake                        │
                    └──────────────────┬───────────────────┘
                                       │
             ┌─────────────────────────┼─────────────────────────┐
             │                         │                         │
             ▼                         ▼                         ▼
┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
│     Graph Service      │  │     Search Service     │  │     Intake Service     │
│ nodes, edges,          │  │ keyword + semantic     │  │ parse free text into   │
│ neighbors, support     │  │ search over documents  │  │ location / needs /     │
│ options, case graph    │  │ and embeddings         │  │ barriers               │
└─────────────┬──────────┘  └─────────────┬──────────┘  └─────────────┬──────────┘
              │                           │                           │
              │                           │                           ▼
              │                           │              ┌────────────────────────┐
              │                           │              │     Triage Service     │
              │                           │              │ urgency, safety risk,  │
              │                           │              │ incident classification│
              │                           │              └─────────────┬──────────┘
              │                           │                            │
              │                           │                            ▼
              │                           │              ┌────────────────────────┐
              │                           │              │   Escalation Services   │
              │                           │              │ escalation decision +   │
              │                           │              │ destination resolver    │
              │                           │              └─────────────┬──────────┘
              │                           │                            │
              │                           │                            ▼
              │                           │              ┌────────────────────────┐
              │                           │              │ Recommendation Service │
              │                           │              │ combine graph matches  │
              │                           │              │ + semantic results     │
              │                           │              └─────────────┬──────────┘
              │                           │                            │
              │                           │                            ▼
              │                           │              ┌────────────────────────┐
              │                           │              │ Case Orchestration     │
              │                           │              │ create survivor / case │
              │                           │              │ assessment / referrals │
              │                           │              └─────────────┬──────────┘
              │                           │                            │
              └──────────────┬────────────┴──────────────┬─────────────┘
                             │                           │
                             ▼                           ▼
               ┌────────────────────────┐   ┌────────────────────────────┐
               │  Graph Data Layer      │   │   Search Document Layer    │
               │ nodes / edges          │   │ searchable support docs    │
               │ taxonomy / live cases  │   │ built from graph views     │
               │ resources / helpers    │   │ + stored embeddings        │
               │ assessments / referrals│   │                            │
               └─────────────┬──────────┘   └─────────────┬──────────────┘
                             │                            │
                             └──────────────┬─────────────┘
                                            ▼
                              ┌───────────────────────────┐
                              │     Graph-Core Postgres   │
                              │ graph tables              │
                              │ search_documents          │
                              │ JSON/metadata             │
                              │ vector embeddings         │
                              └─────────────┬─────────────┘
                                            │
                                            ▼
                         ┌──────────────────────────────────────┐
                         │     Seeded Source-of-Truth Layer     │
                         │ reference taxonomies                 │
                         │ locations / organizations            │
                         │ resources / statuses                 │
                         │ scenario YAML seeds + generated      │
                         │ scenarios for coverage testing       │
                         └──────────────────────────────────────┘