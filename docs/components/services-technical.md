# Services - Technical Implementation Guide

## Overview

The Services directory contains microservices and workflow automation services for the 33GOD ecosystem. These include Node-RED flow orchestrators, event processors, and specialized consumers that integrate various components through Bloodbank.

## Implementation Details

**Language**: Python (FastAPI), Node.js (Node-RED)
**Architecture**: Microservices consuming Bloodbank events
**Deployment**: Docker containers, independent scaling
**Pattern**: Event-driven, single-responsibility services

### Key Services

1. **Tonny Service**: Voice assistant orchestration (Node-RED + ElevenLabs)
2. **Candystore Service**: Event storage microservice
3. **Agent Feedback Router**: Routes agent feedback to appropriate handlers
4. **Node-RED Flow Orchestrator**: Workflow automation engine
5. **TheBoard Meeting Trigger**: Automated meeting creation
6. **Fireflies Transcript Processor**: Meeting transcript analysis

## Architecture & Design Patterns

### Generic Service Template

```python
# services/templates/generic-consumer/main.py
from fastapi import FastAPI
from bloodbank import Subscriber
import asyncio

app = FastAPI()

class EventConsumer:
    def __init__(self, routing_key: str):
        self.routing_key = routing_key

    async def start(self):
        subscriber = Subscriber(binding_key=self.routing_key)
        await subscriber.start(callback=self.handle_event)

    async def handle_event(self, message: dict):
        """Process incoming event"""
        event_type = message["event_type"]

        # Route to specific handler
        handlers = {
            "specific.event.type": self.handle_specific_event,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(message)

    async def handle_specific_event(self, message: dict):
        """Implement business logic here"""
        print(f"Processing: {message['data']}")

@app.on_event("startup")
async def startup():
    consumer = EventConsumer(routing_key="service.specific.*")
    asyncio.create_task(consumer.start())

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

### Node-RED Flow Orchestrator

```javascript
// services/node-red-flow-orchestrator/flows/transcription-to-response.json
[
    {
        "id": "transcription-input",
        "type": "bloodbank-subscriber",
        "name": "Transcription Events",
        "topic": "transcription.voice.completed",
        "wires": [["process-transcription"]]
    },
    {
        "id": "process-transcription",
        "type": "function",
        "name": "Extract Intent",
        "func": "const text = msg.payload.data.text;\n\n// Simple intent extraction\nlet intent = 'unknown';\nif (text.includes('weather')) intent = 'weather';\nif (text.includes('reminder')) intent = 'reminder';\n\nmsg.payload.intent = intent;\nreturn msg;",
        "wires": [["route-intent"]]
    },
    {
        "id": "route-intent",
        "type": "switch",
        "name": "Route by Intent",
        "property": "payload.intent",
        "rules": [
            { "t": "eq", "v": "weather", "vt": "str" },
            { "t": "eq", "v": "reminder", "vt": "str" },
            { "t": "else" }
        ],
        "wires": [["weather-handler"], ["reminder-handler"], ["default-handler"]]
    },
    {
        "id": "weather-handler",
        "type": "http request",
        "name": "Fetch Weather",
        "method": "GET",
        "url": "https://api.openweathermap.org/data/2.5/weather",
        "wires": [["generate-response"]]
    },
    {
        "id": "generate-response",
        "type": "elevenlabs-tts",
        "name": "Generate Voice Response",
        "voiceId": "21m00Tcm4TlvDq8ikWAM",
        "wires": [["publish-response"]]
    },
    {
        "id": "publish-response",
        "type": "bloodbank-publisher",
        "name": "Publish Response",
        "topic": "tonny.response.ready",
        "wires": []
    }
]
```

### TheBoard Meeting Trigger

```python
# services/theboard-meeting-trigger/main.py
from bloodbank import Subscriber
from theboard import MeetingService
import asyncio

class MeetingTrigger:
    """Automatically create TheBoard meetings from calendar events"""

    async def start(self):
        subscriber = Subscriber(binding_key="calendar.event.created")
        await subscriber.start(callback=self.handle_calendar_event)

    async def handle_calendar_event(self, message: dict):
        """Create meeting when calendar event with 'brainstorm' tag"""
        event_data = message["data"]

        # Check if this is a brainstorming session
        if "brainstorm" not in event_data.get("tags", []):
            return

        # Extract topic from event summary/description
        topic = event_data.get("summary", "General brainstorming")
        participant_count = min(len(event_data.get("attendees", [])), 10)

        # Create TheBoard meeting
        meeting_service = MeetingService()
        meeting = await meeting_service.create_meeting(
            topic=topic,
            participant_count=participant_count,
            scheduled_time=event_data["start_time"]
        )

        print(f"Created meeting {meeting.id} for '{topic}'")

        # Optionally send calendar update with meeting link
        await self.send_calendar_update(
            event_data["event_id"],
            meeting_link=f"https://holocene.delo.sh/meetings/{meeting.id}"
        )
```

### Fireflies Transcript Processor

```python
# services/fireflies-transcript-processor/main.py
class TranscriptProcessor:
    """Process Fireflies.ai meeting transcripts"""

    async def handle_transcript(self, message: dict):
        """Extract insights from meeting transcript"""
        transcript_url = message["data"]["transcript_url"]

        # Download transcript
        transcript = await self.download_transcript(transcript_url)

        # Extract action items with LLM
        action_items = await self.extract_action_items(transcript)

        # Create tasks in project management system
        for item in action_items:
            await self.create_task(
                title=item["title"],
                assignee=item["assignee"],
                due_date=item["due_date"]
            )

        # Publish summary event
        await bloodbank.publish(
            "fireflies.transcript.processed",
            {
                "transcript_id": message["data"]["id"],
                "action_items": len(action_items),
                "summary": await self.generate_summary(transcript)
            }
        )

    async def extract_action_items(self, transcript: str) -> List[dict]:
        """Use LLM to extract action items"""
        from anthropic import Client

        client = Client()

        prompt = f"""
        Extract action items from this meeting transcript:

        {transcript}

        For each action item, provide:
        - title (what needs to be done)
        - assignee (who is responsible)
        - due_date (when it's due)

        Output as JSON array.
        """

        response = client.messages.create(
            model="claude-sonnet-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )

        return json.loads(response.content[0].text)
```

### Agent Feedback Router

```python
# services/agent-feedback-router/main.py
class FeedbackRouter:
    """Route agent feedback to appropriate handlers"""

    async def handle_agent_feedback(self, message: dict):
        """Route feedback based on type"""
        feedback_type = message["data"]["feedback_type"]
        agent_id = message["data"]["agent_id"]

        routes = {
            "error": self.route_to_error_handler,
            "suggestion": self.route_to_improvement_queue,
            "completion": self.route_to_review_queue,
            "question": self.route_to_human_queue,
        }

        handler = routes.get(feedback_type)
        if handler:
            await handler(agent_id, message["data"])

    async def route_to_human_queue(self, agent_id: str, data: dict):
        """Send to human for response"""
        await bloodbank.publish(
            "human.input.required",
            {
                "agent_id": agent_id,
                "question": data["content"],
                "context": data.get("context", {}),
                "priority": "high" if "critical" in data.get("tags", []) else "normal"
            }
        )
```

## Configuration

```yaml
# services/docker-compose.yml
version: '3.8'

services:
  tonny-service:
    build: ./tonny
    environment:
      BLOODBANK_URL: amqp://rabbitmq:5672/
      ELEVENLABS_API_KEY: ${ELEVENLABS_API_KEY}
    depends_on:
      - rabbitmq

  meeting-trigger:
    build: ./theboard-meeting-trigger
    environment:
      BLOODBANK_URL: amqp://rabbitmq:5672/
      THEBOARD_API_URL: http://theboard:8000

  transcript-processor:
    build: ./fireflies-transcript-processor
    environment:
      BLOODBANK_URL: amqp://rabbitmq:5672/
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}

  feedback-router:
    build: ./agent-feedback-router
    environment:
      BLOODBANK_URL: amqp://rabbitmq:5672/

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
```

## Integration Points

### Cookiecutter Template

```bash
# Create new service from template
cookiecutter services/templates/generic-consumer

# Prompts:
# service_name: my-new-service
# routing_key: my.events.*
# description: Processes my events
```

## Deployment

```bash
# Deploy all services
cd services
docker-compose up -d

# Deploy single service
docker-compose up -d tonny-service

# View logs
docker-compose logs -f tonny-service
```

## Related Components

- **Bloodbank**: Event source for all services
- **Holyfields**: Event schema definitions
- **Candystore**: Central event storage

---

**Quick Reference**:
- Location: `services/`
- Templates: `services/templates/`
- Deployment: Docker Compose
