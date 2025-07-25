Adding other tools#
Now that you've built a capable agent, we hope you're excited about all it can do. The core of expanding agent capabilities is the tools available, and we have good news: LlamaHub from LlamaIndex has hundreds of integrations, including dozens of existing agent tools that you can use right away. We'll show you how to use one of the existing tools, and also how to build and contribute your own.

Using an existing tool from LlamaHub#
For our example, we're going to use the Yahoo Finance tool from LlamaHub. It provides a set of six agent tools that look up a variety of information about stock ticker symbols.

First we need to install the tool:


pip install llama-index-tools-yahoo-finance
Our dependencies are the same as our previous example, we just need to add the Yahoo Finance tools:


from llama_index.tools.yahoo_finance import YahooFinanceToolSpec
To show how you can combine custom tools with LlamaHub tools, we're going to leave the add and multiply functions in place even though we don't need them here. We'll bring in our tools:


finance_tools = YahooFinanceToolSpec().to_tool_list()
A tool list is just an array, so we can use Python's extend method to add our own tools to the mix:


finance_tools.extend([multiply, add])
And we'll ask a different question than last time, necessitating the use of the new tools:


workflow = FunctionAgent(
    name="Agent",
    description="Useful for performing financial operations.",
    llm=OpenAI(model="gpt-4o-mini"),
    tools=finance_tools,
    system_prompt="You are a helpful assistant.",
)


async def main():
    response = await workflow.run(
        user_msg="What's the current stock price of NVIDIA?"
    )
    print(response)
We get this response:


The current stock price of NVIDIA Corporation (NVDA) is $128.41.
(This is cheating a little bit, because our model already knew the ticker symbol for NVIDIA. If it were a less well-known corporation you would need to add a search tool like Tavily to find the ticker symbol.)

And that's it! You can now use any of the tools in LlamaHub in your agents.

As always, you can check the repo to see this code all in one place.

Building and contributing your own tools#
We love open source contributions of new tools! You can see an example of what the code of the Yahoo finance tool looks like: * A class that extends BaseToolSpec * A set of arbitrary Python functions * A spec_functions list that maps the functions to the tool's API

Once you've got a tool working, follow our contributing guide for instructions on correctly setting metadata and submitting a pull request.

Next we'll look at how to maintain state in your agents.