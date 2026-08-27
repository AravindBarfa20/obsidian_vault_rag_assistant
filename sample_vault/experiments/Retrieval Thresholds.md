---
title: Retrieval Threshold Experiment
tags: [experiment, retrieval, evaluation]
---

# Retrieval Threshold Experiment

The relevance threshold controls whether retrieved candidates count as usable
evidence. A low threshold answers more questions but increases false positives;
a high threshold refuses more often and can hide valid evidence.

## Calibration

I compare the top similarity scores of labelled answerable questions against
clearly unanswerable questions. The useful operating point separates the two
groups with a margin rather than optimizing a single example.

For the Gemini embeddings in this demo, answerable top scores were at least
about 0.72 while the initial negative example peaked near 0.58. I selected 0.65
as the starting threshold, then verified both retrieval recall and no-answer
accuracy. This value is model-specific and must be recalibrated if the embedding
model, dimensions, or vault domain changes.

## Overrides

The API permits a threshold override for experiments, while production queries
use the configured provider default. An override is a diagnostic control, not a
user-facing confidence setting.
