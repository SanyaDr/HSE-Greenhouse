from ollama import chat

def ollamachat():
    stream = chat(
    model='gwen3.5:cloud',
    messages=[{'role': 'user', 'content': 'Why is the sky blue?'}],
    stream=True,
    )

    for chunk in stream:
        print(chunk['message']['content'], end='', flush=True)