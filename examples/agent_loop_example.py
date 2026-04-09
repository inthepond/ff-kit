"""
Example: a minimal agent loop with ff-kit — no framework needed.

This shows how to build a simple tool-calling loop using ff-kit's
dispatch() and schema system. Works with OpenAI, but the pattern
is the same for any provider.

    export OPENAI_API_KEY=sk-...
    python examples/agent_loop_example.py
"""

from __future__ import annotations

import json
from openai import OpenAI
from ff_kit.schemas.openai import openai_tools
from ff_kit.dispatch import dispatch

client = OpenAI()
tools = openai_tools()

SYSTEM = (
    "You are a video editing assistant. You have access to ffkit tools "
    "for clipping, merging, extracting audio, adding subtitles, and "
    "transcoding media files. When the user asks for a media operation, "
    "call the appropriate tool. You can chain multiple tools for complex "
    "workflows (e.g., extract audio then transcode it)."
)


def run_agent(user_message: str, max_turns: int = 5) -> str:
    """
    Run a simple tool-calling agent loop.

    The LLM can call multiple tools across multiple turns.
    Returns the final text response.
    """
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_message},
    ]

    for turn in range(max_turns):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
        )
        msg = response.choices[0].message

        # If no tool calls, we're done
        if not msg.tool_calls:
            return msg.content or ""

        # Execute each tool call
        messages.append(msg.model_dump())
        for tc in msg.tool_calls:
            print(f"  [Turn {turn + 1}] Calling {tc.function.name}...")
            args = json.loads(tc.function.arguments)
            result = dispatch(tc.function.name, args)
            print(f"  [Turn {turn + 1}] Result: {result['status']}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

    return "Agent reached max turns without a final response."


if __name__ == "__main__":
    # Try some real-world prompts:
    prompts = [
        "Extract the audio from meeting.mp4 as a 16kHz mono WAV file for transcription.",
        "Clip the first 60 seconds of raw_footage.mp4 and transcode it to 720p WebM.",
        "Merge intro.mp4, main.mp4, and outro.mp4 into final_video.mp4",
    ]

    for prompt in prompts:
        print(f"\nUser: {prompt}")
        print("-" * 60)
        answer = run_agent(prompt)
        print(f"Assistant: {answer}\n")
