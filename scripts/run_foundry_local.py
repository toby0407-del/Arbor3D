"""Run an actual Microsoft Phi model using the official Foundry Local SDK.

Install foundry-local-sdk-winml on Windows in a dedicated environment first.
This is a local model service, not a rule-based replacement for inference.
"""
import argparse
import json
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="phi-4-mini")
    parser.add_argument("--port", type=int, default=5273)
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--cache", type=Path, default=Path.home()/".cache/arbor3d/models")
    parser.add_argument("--status", type=Path, default=Path(__file__).resolve().parents[1]/".runtime/foundry-status.json")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    from foundry_local_sdk import Configuration, FoundryLocalManager
    endpoint = f"http://127.0.0.1:{args.port}"
    FoundryLocalManager.initialize(Configuration(app_name="Arbor3D", model_cache_dir=str(args.cache),
        web=Configuration.WebService(urls=endpoint)))
    manager = FoundryLocalManager.instance
    if not args.cpu:
        available = {e.name:e for e in manager.discover_eps()}
        name = "WebGpuExecutionProvider"
        if name in available and not available[name].is_registered:
            print("Preparing Microsoft WebGPU execution provider", flush=True)
            result = manager.download_and_register_eps([name])
            print(json.dumps({"execution_provider_ready":result.success,"status":str(result.status)}), flush=True)
    model = manager.catalog.get_model(args.model)
    if model is None:
        raise RuntimeError("Requested model is absent from the Foundry catalog")
    print(json.dumps({"model_id":model.id,"cached":model.is_cached}), flush=True)
    if not model.is_cached:
        last = [-1]
        def progress(p):
            bucket = int(p)//5*5
            if bucket != last[0]:
                last[0] = bucket
                print(f"Model download: {bucket}%", flush=True)
        model.download(progress)
    print("Loading model", flush=True)
    model.load()
    client = model.get_chat_client()
    client.settings.max_tokens = 24
    client.settings.temperature = 0.0
    result = client.complete_chat([{"role":"user","content":"Reply with only: Arbor3D connected"}])
    answer = result.choices[0].message.content
    if not answer or not answer.strip():
        raise RuntimeError("Actual model returned no output")
    manager.start_web_service()
    status = {"provider":"phi4","model_id":model.id,"endpoint":endpoint,
              "verified_at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"inference_verified":True,
              "probe_answer":answer,"urls":str(manager.urls)}
    args.status.parent.mkdir(parents=True, exist_ok=True)
    args.status.write_text(json.dumps(status,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(status,ensure_ascii=False),flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop_web_service()
        model.unload()


if __name__ == "__main__":
    main()
