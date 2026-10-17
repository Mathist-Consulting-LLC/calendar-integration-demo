# Case study: a safer calendar reconciliation slice

This is a self-initiated portfolio demonstration by Mathist Consulting. It is derived from engineering patterns in an internal calendar automation project, then rewritten as a small standalone example with fictional data.

## The problem

Calendar integrations look simple until two systems disagree. A missing identifier can create duplicates, a stale field can overwrite good data, and a timed-out create can leave the caller unsure whether the provider accepted it.

## The approach

The demo separates planning from mutation. It validates and normalizes a fictional source feed, matches destination records by stable source ID, and produces explicit create, update, skip, or review decisions. Dry-run is the default. Apply requires an explicit approval for each write type and can change only generated local JSON state.

## What runs

The mapping, timezone conversion, reconciliation, simulated create/update behavior, uncertainty marker, reports, reset guard, and automated tests all run locally. No credentials or network access are used.

## What is simulated

All destination-provider reads, writes, failures, IDs, and uncertain responses are deterministic simulations. This repository does not verify compatibility with Meetup, Eventbrite, Google Calendar, or any other live provider.

## Why it matters

The example shows the kind of bounded backend integration work Mathist Consulting can deliver: clear ownership rules, reviewable plans, conservative failure behavior, tests, and a written handoff without a frontend or ongoing service requirement.
