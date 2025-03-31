# Short Term Plan: Minimal PR Splitter Agent

## Objective
Implement a minimal viable PR splitter agent system that works as a stand-alone tool. This agent will operate on a local Git clone and is designed to later integrate into a larger agent collection. For the MVP, the agent will:
- Detect the currently checked-out branch (assumed to be the branch to split/merge).
- Assume that the target base branch is "staging" (your company’s default merge branch).
- Simulate the PR splitting process by acknowledging the request, "creating" a new branch, and outputting a high-level summarized change report.

## Implementation Plan
1. **Agent Implementation:**
   - Use the smolagents framework to create a PR splitter agent.
   - The agent (currently implemented as `ManagerAgent`) will be initialized with the necessary model (using `HfApiModel`) and will not include any additional tools for now.
   - The CLI command will be invoked locally (e.g., via a command such as “pr-split”) and will operate on the current Git checkout.

2. **Local Environment Assumptions:**
   - The agent will assume it is being run inside a local Git clone.
   - The branch to be split/merged is the currently checked-out branch (detected via a Git command like `git rev-parse --abbrev-ref HEAD` in a future iteration).
   - The base branch is hard-coded as “staging.”

3. **CLI Behavior:**
   - When the PR splitter command is run, the agent will:
     - Acknowledge that the PR splitting request has been received.
     - Determine and print the current branch name.
     - Simulate branch creation (e.g., by naming it something like “pr-splitting-branch”).
     - Output a summarized change report detailing key differences (e.g., “Feature X added; Bugfix Y applied”).
   
4. **Future Enhancements:**
   - In addition to the current MVP, future development will integrate this PR splitter into a larger system of agent discovery and delegation, eventually forming part of the overall 33God agent framework.
   - Improve detection of the current branch by integrating with Git commands.
   - Enhance the change reporting mechanism with more detailed diffs and validations.

## Acceptance Criteria (MVP)
- The PR splitter agent is invoked from the CLI, assumed to be running on a local clone.
- The agent detects the current branch (initially hard-coded or simulated) and assumes “staging” as the merge target.
- It outputs:
  - An acknowledgement of receiving the PR splitting request.
  - The name of the branch that it “creates” as part of the splitting process.
  - A high-level change report summarizing the modifications (e.g., “Feature X added; Bugfix Y applied”).

This plan reflects the updated vision for the minimal viable PR splitter as a stand-alone agent, forming a part of a future collection of agent systems.
