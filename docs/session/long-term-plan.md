# Long-Term Plan

Create an autonomous Agentic PR splitter

## User Story

- [ ] agent finds the optimal logical split points
- [ ] sum_of_features[basePR] === sum[br1, br2,..,brX]
- [ ] The final result can be quantifiably proven to have 100% parity with the base branch
- [ ] bugs uncovered during analysis should be stored in a document that can be addressed after the splitting is complete
- [ ] Each commit must Not exceed 1000 source lines of code, give or take a hundred or so lines
- [ ] There Should be zero code from a future PR that is present in an earlier PR 
    - For instance, if a PR contains 3 features, the stacked PRs should each feature must be progressively introduced throughout the stack in a way that does not violate temporality.
- [ ] pr documentation is created befored being turned into a PR on github.

