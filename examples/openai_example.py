"""
Example: using ff-kit with the OpenAI SDK.

Prerequisites:
    pip install openai ff-kit
    export OPENAI_API_KEY=sk-...

This script sends a user message asking to clip a video,
lets the model call the ffkit_clip tool, then executes it.
"""

import json
from openai import OpenAI
from ff_kit.schemas.openai import openai_tools
from ff_kit.dispatch import dispatch

client = OpenAI()
tools = openai_tools()

messages = [
    {
        "role": "system",
        "content": (
            "You are a video editing assistant. Use the ffkit tools "
            "to perform media operations the user requests."
        ),
    },
    {
        "role": "user",
        "content": "Clip the first 30 seconds from input.mp4 and save it as intro.mp4",
    },
]

# 1. Ask the model — it should return a tool call
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools,
)

msg = response.choices[0].message

if msg.tool_calls:
    for tc in msg.tool_calls:
        print(f"Tool call: {tc.function.name}")
        print(f"Arguments: {tc.function.arguments}")

        # 2. Execute the tool
        args = json.loads(tc.function.arguments)
        result = dispatch(tc.function.name, args)
        print(f"Result: {json.dumps(result, indent=2)}")

        # 3. Feed result back to the model
        messages.append(msg.model_dump())
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(result),
        })

    # 4. Get the final response
    final = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
    )
    print(f"\nAssistant: {final.choices[0].message.content}")
else:
    print(f"Assistant: {msg.content}")
