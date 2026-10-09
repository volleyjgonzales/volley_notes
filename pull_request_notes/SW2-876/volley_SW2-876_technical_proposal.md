# SW2-876: analysis guide

The analysis has been decomposed into two documents:

- [Background and existing execution](SW2-876-background.md): terminology, source-reading guide, entry paths, transport verification, lifecycle behavior, and current pause/recovery behavior.
- [Problem description and proposed solution](SW2-876-problem-and-solution.md): firmware race, policy, shared 200 ms guard, proposed code changes, regression tests, risks, and rollout criteria.

## VS Code diagram compatibility

Both diagrams now display through relative PNG links. Keep the Markdown and companion images in the same directory, or extract the supplied ZIP and open that folder. Editable Mermaid source is retained in `text` fences; Markdown preview no longer needs to generate an SVG for these diagrams. Companion SVG files use ordinary vector paths/text and contain no HTML `foreignObject` labels.

The original attachment contains two Mermaid blocks and no inline SVG. The specific VS Code extension/version and error were not supplied, so the original rendering failure has not been reproduced. The static fallback avoids that rendering dependency. It does not require relaxing VS Code preview security or installing an extension.

## Test requirement

The solution requires a new helper regression test for early FINISHED reporting, a full 200 ms guard after slow completion, and cancellation, plus an extension to the existing state-predicate test for Idle traversal completion. Test interfaces are grounded in the newly attached repo export. Proposed C++ tests have not been run.
