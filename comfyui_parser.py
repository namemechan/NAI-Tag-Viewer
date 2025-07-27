import json

def get_comfyui_data(info, width, height):
    try:
        prompt_json = json.loads(info.get("prompt", "{}"))
        positive_prompt = ""
        negative_prompt = ""
        options = {}

        for node in prompt_json.values():
            if node["class_type"] == "CLIPTextEncode":
                text = node["inputs"]["text"]
                if "negative" in text.lower() or "embedding:" in text.lower():
                    negative_prompt += text + "\n"
                else:
                    positive_prompt += text + "\n"
            elif "Sampler" in node["class_type"]: # Covers KSampler, SamplerCustom, etc.
                for param_key, param_value in node["inputs"].items():
                    # Exclude node connections and other non-parameter inputs
                    if param_key not in ["positive", "negative", "model", "latent_image", "control_net", "clip", "vae"]:
                        options[param_key] = param_value

        return {
            "prompt": positive_prompt.strip(),
            "negative_prompt": negative_prompt.strip(),
            "option": options,
            "etc": {"workflow": json.loads(info.get("workflow", "{}"))}
        }
    except Exception as e:
        print(f"Error parsing ComfyUI data: {e}")
        return None
