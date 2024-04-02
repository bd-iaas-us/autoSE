start vllm  
it will occupy first 4 CUDAs
```
python -m vllm.entrypoints.api_server --model HuggingFaceH4/zephyr-7b-beta --dtype float16 --tensor-parallel-size 4 --enforce-eager --max-model-len 4096
```


```
CUDA_VISIBLE_DEVICES=4,5,6,7 python3 demo.py
```

