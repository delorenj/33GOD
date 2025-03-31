from smolagents import CodeAgent, LiteLLMModel
from agents.pr_splitter.prompts import SYSTEM_PROMPT

model = LiteLLMModel(model_id="")

class PRSplitterAgent(CodeAgent):
    def __init__(self):
        model = LiteLLMModel()
        model.system_prompt = SYSTEM_PROMPT
        super().__init__(
            tools=[],
            model=model
        )

    def run(self, input_text: str) -> None:
        # Pass empty string if no input is provided
        if not input_text:
            input_text = """Please analyze the current branch and identify potential split points. 
            Consider the dependencies between changes and aim for smaller, reviewable units."""
        
        response = self.chat(input_text)
        print(response)  # For now, just print the LLM's response
