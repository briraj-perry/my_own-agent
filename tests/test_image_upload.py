"""Test for Image Upload handling in NeoAgentCore and Server payload formats."""
import asyncio
from agent.core import NeoAgentCore

async def test_image_stream():
    agent = NeoAgentCore()
    # Dummy base64 1x1 image pixel
    dummy_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    events = []
    # Test stream_response with attached image
    async for event in agent.stream_response("What is in this image?", images=[dummy_b64]):
        events.append(event)
        if len(events) >= 5:
            break
            
    print(f"✅ Generated {len(events)} events with image attached.")
    log_events = [e for e in events if e.get("type") == "execution_log"]
    assert len(log_events) > 0, "Expected execution_log event for user image"
    print("✅ Image attachment test passed!")

if __name__ == "__main__":
    asyncio.run(test_image_stream())
