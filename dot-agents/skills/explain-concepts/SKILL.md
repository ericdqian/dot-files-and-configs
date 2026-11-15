---
name: explain-concepts
description: Explain a concept, subsystem, PR or piece of code so the user can build a precise mental model. Use whenever the user asks what something is, how or why it works, what a PR or change does, how pieces relate, or asks a clarifying follow-up ("wait, so…", "X vs Y?", "where does this come from?"). Focuses on ordering concepts by dependency and keeping terminology unambiguous.
---

# Explain Concepts

Two things matter most when explaining to this user:

1. **Order**: introduce each concept only after everything it depends on, starting
   from its purpose.
2. **Unambiguous terminology**: every term has been introduced before it is used,
   refers to exactly one thing, and leaves only one plausible reading.

Most of the user's confusion in past sessions came from breaking one of these:
a term used before it was explained, a new component appearing mid-answer, a
word that shifted meaning between answers, or similar names defined separately
without their relationship.

Keep the planning implicit. Don't narrate the order you are about to follow;
just explain in that order.

## Order concepts by dependency

- **Find the dependencies first.** Before writing, work out which concepts the
  answer needs and which of them depend on which. Explain in that order.
- **Start from purpose.** Open with the earliest concept that makes the topic
  meaningful: the problem it solves or the situation that needs it. Say what each
  concept is for before describing its fields, states or mechanics.
- **Motivate before introducing, recursively.** This applies to every supporting
  concept, not just the topic. A concept that appears inside another explanation
  still needs its reason to exist.
- **Prerequisites before use.** Never rely on a concept in reasoning before you
  have explained it. Defining it later, in a parenthesis, or in a closing glossary
  does not repair the earlier use.
- **Depth-first.** When a prerequisite needs explaining, explain it fully at the
  point it is needed, then return. Don't leave a reader holding an unexplained
  term while the explanation moves on.
- **Whole before parts.** For a flow, pipeline or data structure, first walk one
  concrete case from its entry point to its result, so the direction of data and
  the starting point are clear. Then explain the parts in the order they act.
- **Before, then after.** For a change or PR, establish how things worked before,
  then what the change adds, removes or replaces.
- **Necessity in order.** When a part is introduced, say what would break without
  it and why the simpler alternative doesn't work, before going into detail.

## Keep terminology unambiguous

- **Earn every term.** Describe the thing or distinction in plain language first,
  then give its name. This applies to domain labels, acronyms, code identifiers,
  and specialized verbs.
- **No unannounced names.** Every component, system, field or file you mention
  needs a short statement of what it is and where it comes from, the first time it
  appears.
- **One term, one referent.** Use each term for exactly one thing, across the
  whole conversation. Don't switch between synonyms for the same thing, and don't
  use one word for two things.
- **Separate the layers.** Distinguish an entity from its identifier, from the
  data that represents it, and from the references that connect it to other
  entities, whenever the difference affects the model. "The path", "the file",
  "the file ID" and "the reference to the file" are different things.
- **Pin down actions.** For an operation, say who performs it, on which entity,
  with what inputs, and what it changes or leaves unchanged.
- **State cardinality and scope.** Say whether a relationship is one-to-one,
  one-to-many or many-to-many, and whether something is per run, per entity,
  per request or global. Don't let an example imply uniqueness.
- **Contrast similar names together.** When several similarly named things coexist
  (for example `kind`, `record_type` and `extraction_type`), explain them in one
  place by how they relate: what each identifies, who sets it, who reads it, and
  which one the reader's question is about. A list of separate definitions is not
  enough.
- **Map code names to concepts.** When naming a code identifier, put it in
  backticks and say which concept it implements, for example "`bind`, the step
  that picks which existing entity a record belongs to". If a name is misleading
  about what the code does, say so.
- **Flag simplifications.** If you simplify, say so. When a later answer refines
  an earlier one, say "more precisely…" and state what changed, so the refinement
  doesn't read as a contradiction.

## Follow-up questions

- Answer at the scope asked. Don't restart the explanation.
- If the question is ambiguous, answer the likeliest reading and name the
  assumption in a few words.
- When the user restates their understanding, confirm it or correct exactly the
  part that's wrong.
- If a follow-up reveals that an earlier answer used a term loosely or out of
  order, correct that explicitly instead of quietly using the term differently.

## Check before sending

- Every term is introduced before its first use, in words the user already has.
- No concept is used in reasoning before it is explained.
- No new name appears without saying what it is.
- Each term means the same thing everywhere it appears.
- Similar names are contrasted together, with their relationship.
- Cardinality is stated wherever it affects the model.
- Refinements of earlier answers are flagged as refinements.

## Related

For generating standalone concept documents rather than chat answers, the
`~/learning` toolkit's `prompts/` hold the fuller teaching prompt. This skill is
the conversational version of its ordering and terminology rules.
