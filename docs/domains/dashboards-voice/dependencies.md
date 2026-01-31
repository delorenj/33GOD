# Dashboards & Voice Domain - Dependencies

## Component Dependencies

```mermaid
graph TB
    subgraph Voice
        TalkyTonny[TalkyTonny<br/>Voice Service]
        TonnyTray[TonnyTray<br/>Desktop App]
    end

    subgraph Dashboards
        Candybar[Candybar<br/>Service Registry]
        Holocene[Holocene<br/>Agent Observability]
        Jelmore[Jelmore Dashboard<br/>Sessions]
    end

    subgraph AI
        Whisper[Whisper AI]
        ElevenLabs[ElevenLabs TTS]
        N8N[n8n Workflows]
    end

    subgraph Infrastructure
        RMQ[RabbitMQ]
        Postgres[PostgreSQL]
        Redis[Redis]
    end

    TonnyTray --> TalkyTonny
    TalkyTonny --> Whisper
    TalkyTonny --> ElevenLabs
    TalkyTonny --> N8N
    TalkyTonny --> RMQ

    Candybar --> RMQ
    Candybar --> Postgres
    Holocene --> RMQ
    Holocene --> Postgres
    Jelmore --> Redis

    style RMQ fill:#f96
    style Whisper fill:#9cf
```

---
**Version**: 1.0.0 | **Updated**: 2026-01-29
