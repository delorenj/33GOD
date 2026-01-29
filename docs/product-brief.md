# Product Brief: 33GOD Service Registry

**Date:** January 8, 2026
**Author:** Sisyphus (Business Analyst Agent)
**Status:** DRAFT
**Version:** 0.1.0

---

## 1. Executive Summary

The 33GOD Service Registry is a centralized management plane for the 33GOD event-driven microservices ecosystem. As the number of specialized agents and services (like Fireflies transcript processors) grows, manual tracking and management become unsustainable. This project provides a Service Registry API and a "Candybar" visualization dashboard to monitor, manage, and debug the interaction between Bloodbank events and subscriber microservices.

**Key Points:**
- **Problem:** Lack of visibility and management for decentralized event-driven microservices.
- **Solution:** A centralized Service Registry API and "Candybar" dashboard.
- **Target Users:** System Administrators, Developers (Self).
- **Timeline:** Q1 2026 (MVP).

---

## 2. Problem Statement

### The Problem

The 33GOD ecosystem is evolving into a complex network of event-driven microservices communicating via the Bloodbank (RabbitMQ). Currently, there is no single source of truth to:
1.  List all active subscriber services.
2.  Visualize which service listens to which event.
3.  Monitor the health and uptime of these decentralized agents.
4.  Manage their lifecycle (start/stop/restart) from a unified interface.

### Who Experiences This Problem

**Primary Users:**
- **Developer/Architect (Delorenj):** Needs to debug event flows and ensure services are running correctly.

### Current Situation

**How Users Currently Handle This:**
- Manually checking Docker containers or process lists.
- Grepping logs to trace event flows.
- Relying on memory to know which service handles which event.

**Pain Points:**
- **Invisibility:** Hard to know if a specific subscriber is actually online and listening.
- **Debugging Friction:** Tracing an event failure requires checking multiple disconnected logs.
- **Management Overhead:** No centralized way to restart a stuck service.

### Impact & Urgency

**Impact if Unsolved:**
- Increased downtime for critical automations (e.g., Fireflies transcription processing).
- Higher cognitive load when adding new services.
- Difficulty in diagnosing system-wide failures.

**Why Now:**
- The ecosystem is expanding with new agents (Fireflies, Obsidian writers). Immediate visibility is needed to maintain stability.

---

## 3. Target Users

### User Personas

#### Persona 1: The System Architect (Delorenj)
- **Role:** Lead Developer & Operator.
- **Goals:** Maintain a stable, observable, and easily extensible event-driven architecture.
- **Pain Points:** "Black box" behavior of event streams; manual service management.
- **Technical Proficiency:** Expert.
- **Usage Pattern:** Daily monitoring, active debugging during development of new features.

### User Needs

**Must Have:**
- Real-time list of registered services.
- Status indicators (Online/Offline/Error).
- Event subscription mapping (Service -> Events).
- Simple API for services to register/heartbeat.

**Should Have:**
- "Candybar" Dashboard visualization (React/Tauri).
- Control actions (Start/Stop services).

**Nice to Have:**
- Historical uptime metrics.
- Event replay capabilities.

---

## 4. Proposed Solution

### Solution Overview

A lightweight **Service Registry API** (FastAPI) that serves as the source of truth. Microservices will register themselves upon startup and send periodic heartbeats. A companion **"Candybar" Dashboard** (Tauri/React) will consume this API to visualize the system topology and health.

### Key Capabilities

1.  **Service Registration & Heartbeat**
    - Description: API endpoints for services to announce presence and liveness.
    - User Value: Real-time accuracy of what's running.

2.  **Topology Visualization**
    - Description: Graph or list view showing Services connected to Event Topics.
    - User Value: Instant understanding of system dependencies.

3.  **Health Monitoring**
    - Description: Auto-detection of "dead" services (missed heartbeats).
    - User Value: Proactive alerting before automation failures occur.

### Minimum Viable Solution (MVP)

**Core Features for MVP:**
- REST API for Registration/Heartbeat/List.
- BaseSubscriber Python class with auto-registration logic.
- Simple CLI or Basic UI to list active services.

---

## 5. Success Metrics

### Primary Metrics

**System Observability**
- **Metric:** Time to detect a down service.
- **Target:** < 1 minute.

**Debugging Efficiency**
- **Metric:** Time to identify which service handles a specific event.
- **Target:** < 10 seconds.

### Success Criteria

**Must Achieve:**
- All existing microservices (Fireflies, etc.) successfully register.
- Dashboard accurately reflects system state in real-time.

---

## 6. Technical Considerations

### Technical Requirements

**Platform:** Linux (Development Environment), Docker (Deployment).
**Stack:**
- **Backend:** Python (FastAPI).
- **Frontend:** React + Tailwind (ShadCN UI) via Tauri (Candybar).
- **Communication:** HTTP (Registry), RabbitMQ (Events).

**Integrations Required:**
- **Bloodbank (RabbitMQ):** For event monitoring.
- **Existing Services:** Must be updated to use `BaseSubscriber` and register.

### Risks

**Risk: Registry Failure**
- **Impact:** Services keep running but visibility is lost.
- **Mitigation:** Registry failure should NOT stop services from processing events (soft dependency).

---

## 7. Resource Estimates

### Team Requirements
- **1 Developer (Full Stack):** Implementation of API, UI, and Service Refactoring.

### Timeline Estimate
- **Phase 1 (API & Base Class):** 2 Days.
- **Phase 2 (Refactor Services):** 1 Day.
- **Phase 3 (Candybar UI):** 2 Days.
- **Total:** ~1 Week (Complexity Level 2).

---

## 8. Next Steps

### Recommended Next Phase

**Planning (PRD Creation)**

**Immediate Actions:**
1.  Run `/prd` to generate the detailed Product Requirements Document based on this brief.
2.  Define the `BaseSubscriber` interface protocol in detail.

---

**Document Status:** DRAFT
**Last Updated:** January 8, 2026
