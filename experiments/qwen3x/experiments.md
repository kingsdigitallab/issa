# Output log of experiments

---
* TIME = 2026-05-16T23:23:07.841941
* VIDEO = DVC43998.mp4
* VRAM used: 22.69 GB out of 24.0 GB
* REQUEST =

```json
{
  "model": "Qwen/Qwen3.5-2B",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "video_url",
          "video_url": {
            "url": "file:///home/gnoel/src/prj/issa/experiments/qwen3x/DVC43998.mp4"
          }
        },
        {
          "type": "text",
          "text": "Summarize the video content in one sentence."
        }
      ]
    }
  ],
  "max_tokens": 5120,
  "temperature": 0.7,
  "top_p": 0.8,
  "presence_penalty": 1.5,
  "extra_body": {
    "top_k": 20,
    "mm_processor_kwargs": {
      "fps": 2,
      "do_sample_frames": true
    }
  }
}
```

* RESPONSE =

```json
{
  "id": "chatcmpl-a7c1be45a117455d",
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "logprobs": null,
      "message": {
        "content": null,
        "refusal": null,
        "role": "assistant",
        "annotations": null,
        "audio": null,
        "function_call": null,
        "tool_calls": [],
        "reasoning": "The video is a compilation of various news segments, interviews, and footage from different locations, featuring diverse topics such as sports, community events, and urban development."
      },
      "stop_reason": null,
      "token_ids": null,
      "routed_experts": null
    }
  ],
  "created": 1778970228,
  "model": "Qwen/Qwen3.5-2B",
  "object": "chat.completion",
  "service_tier": null,
  "system_fingerprint": "vllm-0.21.0-2c744646",
  "usage": {
    "completion_tokens": 33,
    "prompt_tokens": 14571,
    "total_tokens": 14604,
    "completion_tokens_details": null,
    "prompt_tokens_details": null
  },
  "prompt_routed_experts": null,
  "prompt_logprobs": null,
  "prompt_token_ids": null,
  "prompt_text": null,
  "kv_transfer_params": null
}
```

* VRAM used: 22.69 GB out of 24.0 GB
* TIME = 2026-05-16T23:23:48.683761
* DURATION = 00:00:40


---


