AI-Powered Dynamics 365 Test Automation Framework
An end-to-end AI-assisted test automation framework for Microsoft Dynamics 365 Sales that connects requirements, AI-driven test planning, hybrid browser automation, failure analysis, defect creation, reporting, notifications, and Azure DevOps execution.
Overview
The framework starts with Jira user stories and uses the Groq API / Large Language Model to generate structured test scenarios and classify each requirement into an executable Dynamics 365 workflow plan.
Execution uses a hybrid automation model:
•	Known Dynamics 365 operations use reliable predefined Selenium workflows.
•	New or unmapped operations can use a dynamic AI execution path.
•	Selenium performs the actual browser interaction with Dynamics 365.
•	Failures are analyzed before they are treated as automation defects or product defects.
•	Qualifying product failures can automatically create a new Jira defect while preserving the original test as failed.
•	Results and evidence are published as reports, JSON, screenshots, Slack notifications, and email notifications.
•	The complete framework is orchestrated through Azure DevOps using a self-hosted Windows agent.
End-to-End Flow
1.	Retrieve Jira user stories.
2.	Generate structured test scenarios with the AI layer.
3.	Classify the business intent into a workflow, entity, and runtime test data.
4.	Send the AI plan to the hybrid execution dispatcher.
5.	Execute a predefined workflow when the operation is already mapped.
6.	Use dynamic AI execution when an eligible workflow is not mapped.
7.	Drive the real Dynamics 365 Sales UI through Selenium.
8.	Capture execution results and screenshots.
9.	Analyze failures and classify the failure category.
10.	Create a Jira defect when a failure qualifies as a product bug.
11.	Publish results through Jira/Zephyr integration where configured.
12.	Generate HTML/JSON evidence and screenshots.
13.	Send Slack and email execution summaries.
14.	Run the same lifecycle through an Azure DevOps pipeline on a self-hosted Windows agent.
Hybrid Execution Model
The central design principle is:
Reliable where the workflow is known; dynamic where it is not.
Predefined workflows provide deterministic execution for common Dynamics 365 business operations. The dynamic path extends the framework to eligible unmapped operations without requiring every workflow to be hard-coded in advance.
AI Decision Layer
The AI layer is implemented in ai_agent.py.
Key responsibilities include:
•	ai_generate_test_cases() — converts Jira requirements into structured Dynamics 365 test scenarios.
•	ai_decide_workflow() — interprets business intent and determines the workflow, entity, and required test data.
The AI layer plans and classifies the automation. Selenium performs the browser interactions.
Dynamics 365 Execution Engine
dynamics_workflows.py contains the hybrid execution dispatcher and Dynamics 365 workflows.
The dispatcher supports mapped Dynamics 365 operations across entities such as leads, contacts, and accounts, together with qualification, search, update, export, and framework-validation scenarios.
When an eligible AI-classified workflow is not mapped, the dispatcher can route execution to the dynamic path.
Dynamic Execution Example
A demonstrated dynamic scenario uses the update_account workflow:
Jira Story → update_account → No dedicated mapped workflow → Dynamic execution → Locate Account Name → Update + Save → Verify → Result
This demonstrates that the framework is not limited to a fixed list of hard-coded business operations.
AI Failure Analysis
A failed Selenium test is not automatically assumed to be an automation-script problem.
The failure-analysis layer evaluates execution evidence and classifies failures into categories such as locator, timing, environment, product, test-data, authentication, or unknown issues.
For a qualifying product failure:
Test Failure → AI Failure Analysis → PRODUCT_BUG → create_bug = true → Create NEW Jira Defect
The original application test remains FAILED. Defect creation does not convert a genuine failure into a passing test.
The framework also contains intentional failure-handling validation scenarios. These validate that failure detection and analysis work correctly without creating an unnecessary product defect.
Jira and Zephyr Integration
Jira acts as the requirements source for the automation framework.
The framework can use:
•	Story summary
•	Description
•	Acceptance criteria
•	AI-generated test scenarios
•	Execution results
•	Failure-analysis information
•	Automatically created defects for qualifying failures
Zephyr Scale integration is optional. When it is unavailable or disabled, the framework can fall back to Jira-based result publishing.
Reporting and Evidence
Execution can produce:
•	HTML test report
•	JSON results
•	Screenshots
•	Jira/Zephyr execution evidence
•	Slack execution summary
•	Email test report/summary
•	Azure DevOps pipeline artifacts
These artifacts provide both human-readable and machine-readable evidence after browser execution completes.
Azure DevOps Execution
The framework can be triggered through Azure DevOps Pipelines and executed on a self-hosted Windows agent.
The self-hosted agent allows the pipeline to launch the Python automation framework, which uses Chrome and Selenium to execute against Dynamics 365 Sales.
Pipeline completion status and application-test status are treated separately by the current implementation. The generated test report should be used to evaluate the actual functional test results.
Project Structure
dynamics-ai-agent/
|
|-- ai_agent.py
|-- config.py
|-- dynamics_workflows.py
|-- email_service.py
|-- failure_analysis_service.py
|-- jira_service.py
|-- report_generator.py
|-- selenium_helpers.py
|-- slack_service.py
|-- story_change_service.py
|-- test_orchestrator.py
|-- zephyr_service.py
|-- requirements.txt
|-- README.md
|-- screenshots/
|-- reports/
`-- azure-pipelines.yml
Main Components
Component	Responsibility
test_orchestrator.py	Coordinates the complete test lifecycle
ai_agent.py	AI test generation and workflow classification
dynamics_workflows.py	Hybrid D365 workflow dispatcher and execution
failure_analysis_service.py	Failure classification and analysis
jira_service.py	Jira requirements and issue integration
zephyr_service.py	Optional Zephyr Scale publishing
report_generator.py	Test report generation
slack_service.py	Slack notifications
email_service.py	Email notifications
config.py	Environment/configuration loading
Configuration
Keep credentials and environment-specific values outside source control.
Example environment configuration:
Jira
JIRA_URL=
JIRA_EMAIL=
JIRA_API_TOKEN=
PROJECT_KEY=
AI
GROQ_API_KEY=
GROQ_MODEL=
Dynamics 365
DYNAMICS_URL=
DYNAMICS_USERNAME=
DYNAMICS_PASSWORD=
Notifications
SLACK_WEBHOOK_URL=
Optional integrations
ZEPHYR_ENABLED=
ZEPHYR_API_TOKEN=
Never commit .env, API keys, passwords, tokens, MFA information, or webhook secrets to GitHub.
Installation
git clone <your-repository-url>
cd dynamics-ai-agent
python -m venv .venv
pip install -r requirements.txt
Configure the required environment variables locally before execution.
Running the Framework
For the primary CI/CD workflow, trigger the configured Azure DevOps pipeline. The self-hosted Windows agent executes the Python framework and launches Selenium against Dynamics 365.
For development and troubleshooting, the orchestrator can also be executed directly:
python test_orchestrator.py
Current Capabilities
•	Jira-driven automation requirements
•	AI-generated test scenarios
•	AI workflow classification
•	Hybrid deterministic + dynamic execution
•	Selenium-based Dynamics 365 browser automation
•	Runtime test-data support
•	Resilient/dynamic locator mechanisms
•	AI-assisted failure analysis
•	Conditional Jira defect creation
•	Jira/optional Zephyr result integration
•	HTML and JSON reporting
•	Screenshot evidence
•	Slack notifications
•	Email notifications
•	Azure DevOps pipeline execution
•	Self-hosted Windows automation agent
Current Scope and Limitations
•	The current proof of concept uses a focused set of Jira stories selected to demonstrate different automation patterns, including predefined workflows, dynamic execution, locator recovery, and failure analysis.
•	The current scenario set is intended to demonstrate the framework architecture and capabilities rather than represent complete Dynamics 365 Sales functional coverage.
•	The framework is not described as universally self-healing. It provides resilient locator recovery and dynamic locator/execution mechanisms.
•	Dynamic execution depends on the available AI plan, application state, and supported action model.
•	Functional test failures do not necessarily fail the Azure pipeline under the current pipeline behavior.
•	Zephyr integration is optional and environment dependent.
•	Live Dynamics 365 authentication and MFA can require environment-specific handling.
Roadmap
Potential enhancements include:
•	Acceptance-criteria-to-test traceability
•	BDD/Gherkin generation
•	Enhanced coverage reporting
•	Broader Dynamics 365 workflow and entity coverage
•	Additional execution engines such as Playwright
•	Expanded self-healing/resilient locator strategies
•	Richer approval and audit workflows
•	Additional API-level validation
Security
Before publishing this repository:
•	Remove all passwords and API keys.
•	Never commit .env.
•	Add .env to .gitignore.
•	Mask credentials in pipeline logs.
•	Do not commit MFA codes or authentication cookies.
•	Review screenshots for personal or confidential information.
•	Use Azure DevOps secret variables for pipeline credentials.
Technology Stack
•	Python
•	Selenium WebDriver
•	Microsoft Dynamics 365 Sales
•	Groq API / Large Language Model
•	Jira
•	Zephyr Scale (optional)
•	Azure DevOps Pipelines
•	Git / GitHub
•	Slack
•	Email / Microsoft 365 integration
•	HTML / JSON reporting
Purpose
This project demonstrates how AI can be integrated into an enterprise QA automation lifecycle without requiring AI to directly control every browser interaction. The architecture combines AI-based requirement interpretation and failure analysis with deterministic automation where reliability is important, while retaining a dynamic path for new or unmappe
