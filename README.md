# AI-Powered Dynamics 365 Test Automation Framework

An end-to-end AI-assisted test automation framework for Microsoft Dynamics 365 Sales that connects requirements, AI-driven test planning, hybrid browser automation, failure analysis, defect creation, reporting, notifications, and Azure DevOps execution.

## Overview

The framework starts with Jira user stories and uses the Groq API / Large Language Model to generate structured test scenarios and classify each requirement into an executable Dynamics 365 workflow plan.

Execution uses a hybrid automation model:

- Known Dynamics 365 operations use reliable predefined Selenium workflows.
- New or unmapped operations can use a dynamic AI execution path.
- Selenium performs the actual browser interaction with Dynamics 365.
- Failures are analyzed before they are treated as automation defects or product defects.
- Qualifying product failures can automatically create a new Jira defect while preserving the original test as failed.
- Results and evidence are published as reports, JSON, screenshots, Slack notifications, and email notifications.
- The complete framework is orchestrated through Azure DevOps using a self-hosted Windows agent.

## End-to-End Flow

1. Retrieve Jira user stories.
2. Generate structured test scenarios with the AI layer.
3. Classify the business intent into a workflow, entity, and runtime test data.
4. Send the AI plan to the hybrid execution dispatcher.
5. Execute a predefined workflow when the operation is already mapped.
6. Use dynamic AI execution when an eligible workflow is not mapped.
7. Drive the real Dynamics 365 Sales UI through Selenium.
8. Capture execution results and screenshots.
9. Analyze failures and classify the failure category.
10. Create a Jira defect when a failure qualifies as a product bug.
11. Publish results through Jira/Zephyr integration where configured.
12. Generate HTML/JSON evidence and screenshots.
13. Send Slack and email execution summaries.
14. Run the lifecycle through an Azure DevOps pipeline on a self-hosted Windows agent.

## Hybrid Execution Model

The central design principle is:

> **Reliable where the workflow is known; dynamic where it is not.**

Predefined workflows provide deterministic execution for common Dynamics 365 business operations.

The dynamic path extends the framework to eligible unmapped operations without requiring every workflow to be hard-coded in advance.

This approach combines the repeatability required for enterprise regression testing with the flexibility of AI-assisted dynamic execution.

## AI Decision Layer

The AI layer is implemented in `ai_agent.py`.

Key responsibilities include:

- `ai_generate_test_cases()` — converts Jira requirements into structured Dynamics 365 test scenarios.
- `ai_decide_workflow()` — interprets business intent and determines the workflow, entity, and required test data.

The AI layer plans and classifies the automation.

**The AI does not directly drive the browser. Selenium performs the actual Dynamics 365 browser interactions.**

## Dynamics 365 Execution Engine

`dynamics_workflows.py` contains the hybrid execution dispatcher and Dynamics 365 workflows.

The dispatcher supports mapped Dynamics 365 operations across entities such as leads, contacts, and accounts, together with qualification, search, update, export, and framework-validation scenarios.

When an eligible AI-classified workflow is not mapped, the dispatcher can route execution to the dynamic path.

## Dynamic Execution Example

A demonstrated dynamic scenario uses the `update_account` workflow:

```text
Jira Story
    ↓
AI classifies: update_account
    ↓
No dedicated mapped workflow
    ↓
Dynamic execution
    ↓
Locate Account Name
    ↓
Update + Save
    ↓
Verify
    ↓
Result
