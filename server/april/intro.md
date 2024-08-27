

## Workflow

1. clone volocengine docs
2. receive prompt
3. use openai as a classifier. find all related docs based on the prompt.(not vector database RAG)
4. open related volocengine docs. and tell openai to generate HCL
5. validate HCL by running `tf validate`
6. if validation failed, append error message to prompt, and goto step 2


## Example

```
创建一个vpc和ecs，vpc_name是tf-project-1，cidr_block 是172.16.0.0/16，instance_type是ecs.g1.large，ecs付费类型是后付费，instance name是'acc-test-jxp'，系统valume_type是ESSD_PL0
```
