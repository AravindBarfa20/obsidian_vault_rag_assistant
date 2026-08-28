---
title: Retrieval Evaluation Control
tags: [evaluation, control]
status: reference
---

# Retrieval Evaluation Control

This deliberately unrelated note acts as a negative control for retrieval
testing. It helps verify that ordinary personal content does not become evidence
for questions about RAG architecture, embeddings, or evaluation.

## Household checklist

- oat milk
- bananas
- coffee beans

The assistant should only use this passage when a question is genuinely about
the checklist. It should not surface for technical knowledge-base questions.
