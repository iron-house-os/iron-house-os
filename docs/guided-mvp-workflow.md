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

An active quote and its automatically created opportunity appear as one queue item, not duplicates. Deduplication applies only while the linked project is still an opportunity; an awarded or construction job always remains visible.

## Project context

Queue links carry both the project ID and name. Project Operations, Finance, PO Requests, Safety Operations, and Documents open in that project context. New project-linked safety controls persist the project ID, and the PO and Finance modules preselect the routed job.

A requested durable draft remains authoritative when a `draftId` is present. Otherwise, an explicit project link takes priority over a device recovery buffer when the PO form opens. Finance, PO Requests, and Safety Operations react when the routed project changes without requiring a page reload.

A direct quote-edit link is also authoritative over an unrelated device recovery buffer. Declined and expired quotes expose **Start new revision**; saving that revision returns the quote to draft without exposing send, acceptance, or close controls before the revision is saved. Accepted quotes remain immutable.

## Partial availability

Customer Quotes, Projects, workflow drafts, and each awarded-job launch summary load independently. The base queue renders as soon as its three registers settle, without waiting for launch summaries. Launch status is then requested for every awarded job that has a permanent job number, including legacy jobs without a recorded workspace root. IHOS limits launch requests to three at a time and abandons each request after eight seconds. If one source is temporarily unavailable, IHOS identifies the missing status and keeps the successfully loaded work usable. A single failed request must not blank the workflow page.

## Controls

The queue does not send a quote, record customer acceptance, award work, approve a budget or PO, create safety evidence, or deploy software. It routes the user to the existing controlled action. Quote decline and expiry require explicit confirmation, and reopening either state requires a new quote revision.

The formal tender tools remain available separately for document, takeoff, estimating, RFQ, and bid-package work.
