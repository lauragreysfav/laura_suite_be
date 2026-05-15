import asyncio
import httpx

STASHDB_URL = "https://stashdb.org/graphql"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiIwMTllMTM4Ni1jMzA4LTc2ZjYtOGFhNS1kODUzMmQ0NzRkOTciLCJzdWIiOiJBUElLZXkiLCJpYXQiOjE3Nzg0NDQwNTl9.w19mHtKbaz1x5aYnCOsXXVAnwe7rjbMS1L7t0Ow6DLY"

SCENES_QUERY = """
query PerformerScenes($input: SceneQueryInput!) {
  queryScenes(input: $input) {
    count
    scenes {
      id title release_date
      studio { id name }
      performers { performer { id name } }
    }
  }
}
"""

async def test():
    async with httpx.AsyncClient() as client:
        # Testing with performer ID '9f70dd88-c7f9-4744-8a71-696262835c9e' (first one in checkpoint)
        variables = {
            "input": {
                "performers": {"value": ["9f70dd88-c7f9-4744-8a71-696262835c9e"], "modifier": "INCLUDES"},
                "page": 1,
                "per_page": 10
            }
        }
        r = await client.post(
            STASHDB_URL,
            json={"query": SCENES_QUERY, "variables": variables},
            headers={"ApiKey": API_KEY}
        )
        print(f"Status: {r.status_code}")
        print(f"Body: {r.text}")

if __name__ == "__main__":
    asyncio.run(test())
