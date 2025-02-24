# List all available commands
default:
    @just --choose

# Run the PR splitter agent
split-pr:
    pr-split
