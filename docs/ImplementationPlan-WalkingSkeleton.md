# Implementation Plan: 33GOD

## Milestone 1: The Walking Skeleton

Version: 1.0

Date: May 25, 2025

Associated PRD: 33GOD - The Agent Corporation Framework (Version 1.1)

Author: Jarad DeLorenzo / delorenj & AI Assistant

## 1. Introduction & Purpose

This document outlines the technical implementation plan for Milestone 1 of Project 33GOD: **The Walking Skeleton**. The goal of this milestone is to establish a minimal, end-to-end functional version of the system, touching all major architectural components. This will validate the core technology choices, integration points, and provide a foundational structure for future development.

The Walking Skeleton will realize the user story defined in `WalkingSkeleton.md`, focusing on a basic dashboard view, a single "cofounder" agent, and CLI interaction to list departments.

## 2. Locked-In Technology Stack (Milestone 1)

- **Backend API:** Python 3.11+ with FastAPI
    
- **Database:** PostgreSQL (latest stable)
    
- **Event Queue:** RabbitMQ (latest stable)
    
- **Web Frontend (Dashboard):**
    
    - Language: TypeScript
        
    - Framework/Library: React (Vite as build tool)
        
    - Node/Canvas Rendering: React Flow
        
    - UI Components: ShadCN/UI
        
    - Styling: Tailwind CSS
        
    - State Management: Zustand
        
- **CLI Frontend:** Python 3.11+ with Typer
    
- **LLM Interaction:** Python `httpx` library to OpenRouter API
    
- **Containerization & Local Orchestration:** Docker & Docker Compose
    

## 3. Milestone 1: Walking Skeleton - Key Goals & User Story

As per `WalkingSkeleton.md`, the primary goal is to achieve the following user experience:

> "I visit my 33GOD dashboard on `http://localhost:3360` and I see an empty avatar root node and my "cofounder" below - an initial dumb test agent with no access to tools or anything - just a simple agent that when invoked with a query will agree with everything you say in an enthusiastic way. Since we're early on in development, we won't have a hiring team yet (which will make the agents for us), we'll have to make them and register them as "employees" at the company... The way that the front end knows about my 1 department (the default "founding members" one) and it's one member (the default co-founder agent) is by hitting the fast API endpoint that print out my company's structure. In addition to invoking it from the frontend I could also use the CLI and run `33god departments list`."

The `33god departments list --detailed` command should output the described JSON structure. The `33god chat [employee_id] "Who should we hire first?"` command should interact with the cofounder agent.

## 4. Component Breakdown & Tasks for Walking Skeleton

### 4.1. Backend (FastAPI)

- **Setup:**
    
    - Initialize FastAPI project structure.
        
    - Integrate Pydantic for data validation.
        
- **API Endpoints (Minimal):**
    
    - `GET /api/v1/company/structure`:
        
        - Responds with the hardcoded/initial company structure (CEO node, "foundingMembers" department, "Tonny Trosk" cofounder agent).
            
        - Data structure should match the example in `WalkingSkeleton.md`.
            
    - `POST /api/v1/agents/{employee_id}/chat`:
        
        - Receives a prompt for the specified `employee_id`.
            
        - For "Tonny Trosk" (ID: 123), it will call the OpenRouter API.
            
        - Returns the LLM's response.
            
- **LLM Integration:**
    
    - Implement a service/function to call the OpenRouter API (`deepseek/deepseek-chat` model) using `httpx`.
        
    - Manage API key securely (e.g., environment variable).
        
- **Database Interaction (Placeholder/Minimal):**
    
    - For MS1, the `/api/v1/company/structure` endpoint might return hardcoded data. Actual DB query can be deferred slightly but the schema should be defined.
        

### 4.2. Database (PostgreSQL)

- **Schema Definition (Minimal):**
    
    - `departments` table (id, name, parent_department_id nullable).
        
    - `agents` table (id, name, role, responsibilities, provider, model, department_id, skills (JSONB), access (JSONB), resume (JSONB)).
        
    - `company` table (id, name) - if needed for top-level company entity.
        
- **Initial Data:**
    
    - Script to insert the "foundingMembers" department and "Tonny Trosk" agent with `employeeId: 123`.
        
    - The `lifetimeCost` can be a hardcoded integer for now.
        
- **Connection:** Ensure FastAPI can connect to the PostgreSQL instance.
    

### 4.3. Event Queue (RabbitMQ)

- **Setup:**
    
    - Include RabbitMQ service in `docker-compose.yml`.
        
- **Verification:**
    
    - Create a simple Python script (or a test endpoint in FastAPI) that publishes a dummy message to a test queue.
        
    - Create a simple Python script that consumes the dummy message from the test queue.
        
    - **No direct integration into the core user story flow for MS1 is required, just proof of connectivity.**
        

### 4.4. Web Frontend (React, React Flow, ShadCN/UI, Zustand, Tailwind)

- **Project Setup:**
    
    - Initialize React project using Vite with TypeScript.
        
    - Install and configure Tailwind CSS.
        
    - Install React Flow, Zustand, ShadCN/UI.
        
- **Basic Layout:**
    
    - Create a main page accessible at `http://localhost:3360`.
        
    - Use ShadCN/UI for basic layout structure if desired (e.g., simple header/content).
        
- **State Management (Zustand):**
    
    - Set up a simple store to hold the company structure data.
        
- **API Integration:**
    
    - Fetch company structure from `GET /api/v1/company/structure` on page load.
        
    - Store the response in the Zustand store.
        
- **Canvas Rendering (React Flow):**
    
    - Render a CEO node (e.g., simple circle or avatar placeholder).
        
    - Render the "cofounder" agent ("Tonny Trosk") as a node below the CEO, displaying its name and role.
        
    - Nodes should be based on data fetched from the API.
        
- **Agent Interaction (Placeholder/Minimal):**
    
    - Clicking on "Tonny Trosk" node could open a very simple modal (using ShadCN/UI Dialog).
        
    - Modal contains an input field and a submit button.
        
    - Submitting a message calls `POST /api/v1/agents/123/chat`.
        
    - Display the agent's response in the modal.
        

### 4.5. CLI Frontend (Typer)

- **Project Setup:**
    
    - Initialize Typer application structure.
        
- **Commands:**
    
    - `33god departments list [--detailed]`:
        
        - Makes an HTTP GET request to the FastAPI backend (`/api/v1/company/structure`).
            
        - Prints the JSON response, formatted nicely.
            
    - `33god chat <employee_id> "<prompt_string>"`:
        
        - Makes an HTTP POST request to the FastAPI backend (`/api/v1/agents/{employee_id}/chat`) with the prompt.
            
        - Prints the agent's response.
            
- **Configuration:** Method to specify backend API URL (e.g., environment variable or config file, default to `http://localhost:8000/api/v1`).
    

### 4.6. Containerization (Docker & Docker Compose)

- **Dockerfile for FastAPI Backend.**
    
- **Dockerfile for React Frontend (multi-stage build for serving static assets, e.g., with Nginx).**
    
- **`docker-compose.yml`:**
    
    - Defines services for:
        
        - FastAPI backend
            
        - PostgreSQL database (with volume for data persistence)
            
        - RabbitMQ
            
        - React frontend (Nginx)
            
    - Manages networking between services.
        
    - Sets up environment variables.
        

## 5. Key Interfaces/APIs for Walking Skeleton

- **Backend API (FastAPI):**
    
    - `GET /api/v1/company/structure`
        
        - Response Body (JSON): Matches `WalkingSkeleton.md` example.
            
    - `POST /api/v1/agents/{employee_id}/chat`
        
        - Request Body (JSON): `{ "prompt": "string" }`
            
        - Response Body (JSON): `{ "response": "string" }`
            

## 6. Setup & Prerequisites

- Docker and Docker Compose installed.
    
- Node.js (for frontend development, Vite requires it).
    
- Python 3.11+ (for backend & CLI development).
    
- OpenRouter API Key.
    
- Git repository initialized.
    

## 7. Timeline/Phasing (High-Level for Milestone 1)

A suggested order of operations:

1. **Foundation (Parallel):**
    
    - Setup Docker Compose with PostgreSQL and RabbitMQ services. Verify basic connectivity.
        
    - Initialize FastAPI project, create basic Dockerfile.
        
    - Initialize React (Vite) project, create basic Dockerfile.
        
    - Initialize Typer CLI project.
        
2. **Backend - API Core:**
    
    - Implement the `GET /api/v1/company/structure` endpoint in FastAPI (initially with hardcoded data).
        
    - Implement the PostgreSQL schema and seed data for the cofounder.
        
    - Modify `/api/v1/company/structure` to fetch from DB (optional for strict MS1, but good to do early).
        
3. **Backend - Agent Chat Logic:**
    
    - Implement the OpenRouter API call service.
        
    - Implement the `POST /api/v1/agents/{employee_id}/chat` endpoint.
        
4. **CLI Implementation:**
    
    - Implement `33god departments list` command.
        
    - Implement `33god chat` command.
        
5. **Web Frontend Implementation:**
    
    - Basic layout and API call to fetch company structure.
        
    - Render CEO and cofounder nodes using React Flow.
        
    - Implement basic chat modal and interaction with the chat API.
        
6. **Integration & Testing:**
    
    - Ensure all components work together within Docker Compose.
        
    - Test the full user story end-to-end.
        

## 8. Definition of Done for Milestone 1

Milestone 1 is considered complete when:

1. All components (Backend API, PostgreSQL, RabbitMQ, Web Frontend, CLI) are containerized using Docker and orchestrated with Docker Compose.
    
2. The Web Dashboard at `http://localhost:3360` successfully:
    
    - Fetches and displays the CEO node and the "Tonny Trosk" cofounder agent node using data from the backend API.
        
    - Allows a user to send a message to "Tonny Trosk" via a simple UI element and displays its enthusiastic agreement (response from OpenRouter via the backend).
        
3. The CLI command `33god departments list [--detailed]` successfully fetches and displays the company structure (matching `WalkingSkeleton.md`) from the backend API.
    
4. The CLI command `33god chat 123 "Test prompt"` successfully interacts with "Tonny Trosk" via the backend and prints its response.
    
5. RabbitMQ service is running and a basic publish/subscribe test (outside the main user flow) is successful.
    
6. Basic project structure and READMEs are in place for each component.
    
