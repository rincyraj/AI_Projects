from huggingface_hub import InferenceClient

HF_TOKEN = os.getenv("HF_TOKEN")

client = InferenceClient(
    provider="hf-inference",
    api_key=HF_TOKEN
)

# Try these models instead
models_to_try = [
    "google/gemma-2-2b-it",  # Recommended in docs [citation:3]
    "microsoft/phi-2",       # Small but powerful
    "HuggingFaceH4/zephyr-7b-beta"  # But use chat completion, not text_generation
]

for model in models_to_try:
    try:
        print(f"Trying model: {model}")
        
        # For chat models, use chat completions
        if "zephyr" in model or "gemma" in model:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hello world!"}],
                max_tokens=50
            )
            print(f"✅ Success with {model}: {response.choices[0].message.content}")
        else:
            # For text generation models
            output = client.text_generation(
                "Hello world!",
                model=model,
                max_new_tokens=50
            )
            print(f"✅ Success with {model}: {output}")
        break
    except Exception as e:
        print(f"❌ Failed with {model}: {e}")