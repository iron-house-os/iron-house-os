# Guided MVP workflow

## Purpose

The MVP Workflow page is the operational starting point for customer work. It replaces the former static module list with a live, read-only work queue derived from Customer Quotes, Projects, awarded-job launch summaries, and owner-scoped unfinished forms.

## Quote-to-job stages

1. Capture the verbal request as a durable Customer Quote and linked opportunity.
2. Finish the quote, record that it was sent, and record the customer's decision.
3. Management acceptance records the evidence, awards the linked project, and creates the permanent job number.
4. Complete the awarded-job start controls and handoffs for estimate, budget, purchase orders, safety, and documents.
5. Continue the ready job through Project Operations and field delivery.

The work queue derives one next action for each active item:

- draft quote: finish and send the quote;
- sent quote: record acceptance, decline, expiry, or a revised scope;
- awarded job with incomplete controls: open the Project Workspace and complete the launch checklist;
- launch-ready job: begin Project Operations;
- construction job: continue Project Operations; and
- tender or unquoted opportunity: open the Project Workspace and choose the correct workflow.

An active quote and its automatically created opportunity appear as one queue item, not duplicates.

## Project context

Queue links carry both the project ID and name. Project Operations, Finance, PO Requests, Safety Operations, and Documents open in that project context. New project-linked safety controls persist the project ID, and the PO and Finance modules preselect the routed job.

A requested durable draft remains authoritative when a `draftId` is present. Otherwise, an explicit project link takes priority over a device recovery buffer when the PO form opens.

## Partial availability

Customer Quotes, Projects, workflow drafts, and each awarded-job launch summary load independently. If one source is temporarily unavailable, IHOS identifies the missing status and keeps the successfully loaded work usable. A single failed request must not blank the workflow page.

## Controls

The queue does not send a quote, record customer acceptance, award work, approve a budget or PO, create safety evidence, or deploy software. It routes the user to the existing controlled action. Quote decline and expiry require explicit confirmation, and reopening either state requires a new quote revision.

The formal tender tools remain available separately for document, takeoff, estimating, RFQ, and bid-package work.
