#!/usr/bin/env python3
from agents.pr_splitter.agent import PRSplitterAgent

def main():
    print("Starting PR splitter analysis...")
    agent = PRSplitterAgent()
    # Here, input_text can be extended to accept arguments; for now, an empty string is used.
    agent.run("")
    print("PR splitter analysis complete.")

if __name__ == "__main__":
    main()
