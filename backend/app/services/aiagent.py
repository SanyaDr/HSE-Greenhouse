from ollama import chat

def ollamachat():
    try:
        stream = chat(
            model='qwen3.5:cloud',
            messages=[{'role': 'user', 'content': 'Почему небо голубое?'}],
            stream=True,
        )

        response_text = ""
        for chunk in stream:
            if 'message' in chunk and 'content' in chunk['message']:
                response_text += chunk['message']['content']

        return {"response": response_text}

    except Exception as e:
        return {"error": str(e), "details": str(e.__class__.__name__)}

#
# from ollama import chat
#
# def ollamachat():
#     stream = chat(
#         model='qwen3.5:cloud',
#         messages=[{'role': 'user', 'content': 'Why is the sky blue?'}],
#         stream=True,
#     )
#
#     for chunk in stream:
#         print(chunk['message']['content'], end='', flush=True)