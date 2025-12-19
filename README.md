Agentic AI – Email-Driven Plan Setup Automation
📌 Overview

This project implements an Agentic AI–based automation system that processes plan setup requests received via email.
It validates incoming documents, manages retries intelligently, communicates with requestors, and escalates failures in a controlled manner — inspired by enterprise RPA systems like Blue Prism.

The system is designed to eliminate manual rework caused by missing data, duplicate submissions, and uncontrolled retries, while providing full visibility and auditability.

🎯 Problem Statement

In real-world operations, plan setup requests often:

Arrive via email with attached documents

Contain missing or invalid information

Get resubmitted multiple times by users

Trigger repeated manual intervention

Lack clear tracking and visibility

Traditional automation struggles with data quality issues and infinite retry loops.

✅ Solution

This project introduces an Agentic AI architecture, where multiple autonomous agents collaborate to handle the end-to-end workflow:

Validate incoming requests

Communicate clearly with requestors

Apply controlled retry logic

Prevent infinite loops

Escalate only when necessary

Provide real-time operational visibility

🧠 Key Features

📥 Email-based request intake

📄 AI-assisted document validation

🔁 Controlled retry mechanism (max 2 retries)

🆔 New internal Plan ID for each retry

🚫 Duplicate request detection

📩 Automated email notifications

🚨 Escalation after repeated failures

📊 Live queue dashboard (Blue Prism–style)

💾 Persistent queue & retry tracking

🧰 Technology Stack

Python – Core orchestration and agents

Agentic Architecture – Modular decision-making

Email Integration – Inbound & outbound communication

JSON Persistence – Queue and retry state

Terminal Dashboard – Real-time monitoring

RPA-style Queue Simulation – Blue Prism inspired

🏗️ Project Structure
.
├── agents/                 # Autonomous agents (core logic)
│   ├── email_monitor_agent.py
│   ├── document_validator_agent.py
│   ├── requestor_interaction_agent.py
│   └── bp_exception_handler.py
│
├── utils/                  # Shared utilities
│   ├── document_parser.py
│   ├── outlook_connector.py
│   └── data_exporter.py
│
├── graph/                  # Workflow orchestration
│   └── workflow.py
│
├── mock_queue/              # Blue Prism-style queue simulation
│   ├── queue_manager.py
│   ├── bp_worker.py
│   └── dashboard.py
│
├── data/                   # Persistent runtime state
│   ├── queue.json
│   └── retry_registry.json
│
├── main.py                 # System orchestrator
├── config.py               # Configuration
├── .env                    # Environment variables
└── README.md

🔄 High-Level Workflow
Incoming Email
     ↓
Email Monitor Agent
     ↓
Document Validator Agent
     ↓
Queue Processing (BP Worker)
     ↓
Retry (max 2) → Escalation
     ↓
Live Dashboard + User Notification

🔁 Retry & Escalation Logic

Each request is allowed a maximum of two retries

Every retry generates a new internal Plan ID

All attempts are tracked in a persistent retry registry

After two failed retries, the request is escalated

Users are notified at key lifecycle events

This ensures no infinite loops and controlled automation.

📊 Dashboard

A terminal-based live dashboard provides:

Real-time queue status

Retry counts

Escalation visibility

Worker (VDI) assignment

The dashboard reads persisted queue state to stay consistent across processes.

▶️ How to Run

Configure environment variables in .env

Start the system:

python main.py


Start the BP worker:

python mock_queue/bp_worker.py


Start the dashboard:

python mock_queue/dashboard.py

🚀 Use Cases

Plan setup & onboarding

Document-driven automation

Email-based request processing

RPA exception handling

Retry & escalation management

📌 Future Enhancements

Configurable retry policies

Web-based dashboard

External system integration

Metrics & analytics

Authentication & role-based access




GDRIVE DEMO VIDEO:
https://drive.google.com/file/d/1DXzboW3A0B3lRNDWF-w5g09Xvv5_ZnuT/view?usp=sharing
