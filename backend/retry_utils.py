import time
from typing import Generator, Any
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# We'll retry on any Exception that contains "429" or "RESOURCE_EXHAUSTED"
def is_rate_limit(exception: Exception) -> bool:
    msg = str(exception).upper()
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg or "QUOTA" in msg

# Decorator for standard synchronous functions (like llm.invoke)
with_rate_limit_retry = retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=2, min=4, max=15),
    stop=stop_after_attempt(5),
    before_sleep=lambda retry_state: print(f"[Rate Limit] Retrying in {retry_state.next_action.sleep}s...") if is_rate_limit(retry_state.outcome.exception()) else False
)

def stream_with_retry(llm_stream_func, *args, **kwargs) -> Generator[Any, None, None]:
    """
    Helper to retry a streaming generator.
    The 429 error usually triggers on the FIRST yield when the network request is actually made.
    """
    max_attempts = 5
    attempt = 1
    wait_time = 4

    while attempt <= max_attempts:
        try:
            gen = llm_stream_func(*args, **kwargs)
            # Try to get the first chunk to trigger the network request
            first_chunk = next(gen)
            yield first_chunk
            # If we get here, the request succeeded, yield the rest normally
            yield from gen
            return
        except StopIteration:
            return
        except Exception as e:
            if is_rate_limit(e) and attempt < max_attempts:
                print(f"[Rate Limit] Streaming hit 429. Retrying in {wait_time}s... (Attempt {attempt}/{max_attempts})")
                time.sleep(wait_time)
                attempt += 1
                wait_time *= 2  # exponential backoff
            else:
                # If it's not a rate limit error, or we ran out of retries, raise it
                raise
