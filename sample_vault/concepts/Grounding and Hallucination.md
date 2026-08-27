---
title: Grounding and Hallucination
tags: [ai, safety, generation]
---

# Grounding and Hallucination

Grounding means every factual claim in an answer is supported by retrieved
evidence. In this assistant, the vault is the source of truth; the language
model's memorized knowledge is not accepted as evidence. See [[RAG Evaluation]].

## Two layers of protection

The first protection is a relevance gate before generation. If no passage
clears the threshold, the service returns a fixed no-answer response and never
calls the LLM. The second protection is a generation prompt that allows only
the numbered sources and requires inline citations such as `[S1]`.

## What the gate does not guarantee

A high similarity score is not proof that a passage answers the question. An
irrelevant passage can occasionally cross the threshold, so negative test
questions and threshold calibration remain necessary. Citation presence also
does not automatically prove that every claim is entailed by its source.

## Preferred failure behaviour

A trustworthy assistant should say that the vault lacks enough information
instead of completing an answer from general knowledge. Partial evidence should
produce a qualified answer that separates supported facts from missing details.
