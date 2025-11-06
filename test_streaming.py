import asyncio
import json


async def test_streaming():
    """Test what chunks we're actually sending."""
    from app.openai_compat.streaming import StreamChunkBuilder

    builder = StreamChunkBuilder(model="test-model")

    # Simulate the sequence we send
    chunks = []

    # 1. Role chunk first
    role_chunk = builder.build_role_chunk()
    chunks.append(builder.format_sse(role_chunk))
    print("=== ROLE CHUNK ===")
    print(chunks[-1])

    # 2. First content
    content1 = builder.build_content_chunk("I")
    chunks.append(builder.format_sse(content1))
    print("=== FIRST CONTENT CHUNK ===")
    print(chunks[-1])

    # 3. Second content
    content2 = builder.build_content_chunk(" couldn't")
    chunks.append(builder.format_sse(content2))
    print("=== SECOND CONTENT CHUNK ===")
    print(chunks[-1])

    # Parse to verify
    for i, chunk in enumerate(chunks):
        data = json.loads(chunk.replace("data: ", "").strip())
        print(f"\nChunk {i}: delta = {data['choices'][0]['delta']}")

asyncio.run(test_streaming())
