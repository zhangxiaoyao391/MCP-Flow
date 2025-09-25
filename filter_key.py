import os
import json


input_folder = "mcp_config/smithery"

# output_folder = "processed_json_folder"
# os.makedirs(output_folder, exist_ok=True)

def replace_placeholders(obj):

    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            new_obj[k] = replace_placeholders(v)
        return new_obj
    elif isinstance(obj, list):
        return [replace_placeholders(item) for item in obj]
    elif isinstance(obj, str):
        # 如果字符串本身是 key 值或 profile
        if obj.lower().startswith("f") and len(obj) == 36:  # 粗略UUID判断
            return "your key"
        if obj.lower() == "profile":
            return "your profile"
        return obj
    else:
        return obj

def process_args(args):

    new_args = []
    skip_next = False
    for i, val in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if val == "--key":
            new_args.extend(["--key", "your key"])
            skip_next = True
        elif val == "--profile":
            new_args.extend(["--profile", "your profile"])
            skip_next = True
        else:
            new_args.append(val)
    return new_args


for filename in os.listdir(input_folder):
    if filename.endswith(".json"):
        file_path = os.path.join(input_folder, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            for server_name, server_data in data.get("mcpServers", {}).items():
                if "args" in server_data:
                    server_data["args"] = process_args(server_data["args"])


        data = replace_placeholders(data)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"Processed: {filename}")
