"""
Example: using ff-kit with the Anthropic SDK.

Prerequisites:
    pip install anthropic ff-kit
    export ANTHROPIC_API_KEY=sk-ant-...

This script sends a user message asking to extract audio,
lets Claude call the ffkit_extract_audio tool, then executes it.
"""

import json
import anthropic
from ff_kit.schemas.anthropic import anthropic_tools
from ff_kit.dispatch import dispatch

client = anthropic.Anthropic()
tools = anthropic_tools()

messages = [
    {
        "role": "user",
        "content": "Extract the audio from video.mp4 as a 16kHz mono WAV for speech recognition.",
    },
]

# 1. Ask Claude — it should return a tool_use block
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system=(
        "You are a video editing assistant. Use the ffkit tools "
        "to perform media operations the user requests."
    ),
    tools=tools,
    messages=messages,
)

for block in response.content:
    if block.type == "tool_use":
        print(f"Tool call: {block.name}")
        print(f"Arguments: {json.dumps(block.input, indent=2)}")

        # 2. Execute the tool
        result = dispatch(block.name, block.input)
        print(f"Result: {json.dumps(result, indent=2)}")

        # 3. Feed result back to Claude
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                }
            ],
        })

        # 4. Get the final response
        final = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )
        for b in final.content:
            if hasattr(b, "text"):
                print(f"\nAssistant: {b.text}")

    elif hasattr(block, "text"):
        print(f"Assistant: {block.text}")
