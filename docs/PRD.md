# 33GOD
> A powerful mixture-of-experts framework for building sophisticated AI agents

## User Story

**Background**: Deployed behind my reverse-proxy, the root agent 33GOD is listening for requests.

My pull request is too large and I have to split it into multiple smaller ones. I decide once and for all that I will create an agentic system that is specialized in the splitting of pull requests into smaller ones.

This is my first agentic system for Github, so. I create a new domain where I'll put all my Github actions. As more domains become necessary, I add them as needed. This is where new agent actions in those domains will be registered and become discoverable to the 33GOD root agent.

I begin my development of the PR splitter by creating a Smolagent manager and think about the tools he's going to need. I split it up into a few steps, the first being analyzing the pr for semantic context and high level purpose so I can find the logical split points (AGENT: split-analyzer). It's also important that these agents have on their refactoring hats, meaning no new features at all. Their task is to split with 100 percent parity. They can add more tests if needed, but the underlying code must remain the same. If they uncover bugs during their analysis, they should be stored in a document that can be addressed after the splitting is complete.

The agents must adhere to the strict rules of 100 percent parity with the base pr, as well as a few other rules. Each commit must Not exceed 1000 source lines of code, give or take a hundred or so lines (AGENT: code-reviewer).

There should be a specialized coder agent that does the actual refactoring. Since there should be no new code, his tool belt should consist of analyzing diffs through commit SHA, Cherry picking individual commits, and if necessary, reapplying changes manually that were spread amongst multiple commits. The plan will be thoroughly codified by the split-analyzer agent and handed to the coder agent to kick off his refactoring task. Upon completion, the coder agent will notify the code-reviewer agent to ensure his branches adhere to all the PR rules (TOOL: check-code-adheres-to-rules). One of the rules is a 100 percent parity rule. The reviewer agent runs the tests and if they pass (TOOL: run-tests). The line count is 890 lines (branch 1), and 330 lines (branch 2) (TOOL: sloc-count). There Should be zero code from a future PR that is present in an earlier PR (TOOL: progressive-consistency-check). For instance, if a PR contains authentication. authentication and. a new NAV bar feature. and the first printer should contain authentication feature Then there should be zero code related to the NAV bar feature which was added later and will appear in the second pr of the stack.

If the rules didn't pass The reviewer agent will pass the results to the split analyzer. where they'll come up with the next plan. The plan is passed to the branch-manager who is responsible for maintaining, creating, rebasing the stack's branches. He creates a new branch structure compatible with the new plan and the splitter agent hands it down to the coder agent again. This process will continue until all rules pass.

If the rules do pass Then it's passed back to the manager who then Notifies the pr managerwho creates the  pr documentation by applying the team's pull request template to the high-level description of this particular portion as first planned and described by the split-analyzer.
