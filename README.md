[![codecov](https://codecov.io/github/zinchse/hbo_bench/graph/badge.svg?token=JQIXTUX0R6)](https://codecov.io/github/zinchse/hbo_bench)

**`TL;DR`** This is a platform (data + wrappers) that allows us to run tens of thousands of experiments for query optimisation via using so-called hints in a *few minutes* on a laptop. 
The idea is that almost all the required calculations have been cached (~`2W` of compute, `60K`+ plans), and instead of execution we actually do simple *look-up*.

**Contribution:** were collected cached query execution results with different sets of hints, and implemented `torch`-like `Dataset` and `DataLoader`, vectorisation procedure 
for query execution plans and local search procedure for efficient exploration of parameter space.
 
# 💡 Idea behind this benchmark

**H**int-**B**ased query **O**ptimisation (HBO) is an approach to optimising the query execution time that allows accelerating the workload execution without changing a single line of DBMS kernel code.
This is achieved by selecting the planner hyperparameters (*hints*) influencing the construction of the query execution plan. Despite the fact that this approach
can speed up query execution many times over (*check it!*), it is associated with a fundamental complexity - the search space **is exponential**, and the cost of exploring a "point" in it **depends on its execution time**.


# 🧐 Why is it useful? 

**Adding parallelism.** 
This dataset is not only the first of its kind but also enables the exploration of query acceleration strategies through the use of hints and control over parallelism. 
By expanding the search space, queries can be further accelerated by an *additional* `30%`!

<img src="https://github.com/user-attachments/assets/96fc53a0-31ba-4720-afdc-c0953c931349" alt="image" width="600"/>

**Efficient search for quick exploration strategies.** 
However, as the search space grows, the challenge of finding good solutions within it becomes more *pressing*. The second goal of this project is to enable quick testing of various strategies for exploring the hint space. As shown, the local search algorithm significantly accelerates exploration time, reducing it by an order of magnitude! This reduction in search space is asymptotic — the local search algorithm shifts the complexity from exponential to *linear*, with minimal performance loss. To find this configuration we went through more than 10 thousand different algorithms.

<img src="https://github.com/user-attachments/assets/bfb2ebe4-45fb-4c8c-bd30-59683815b59b" alt="image" width="600"/>

# 📦 Setup 

```shell
python -m pip install --upgrade pip
python3 -v venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo apt-get install -y p7zip-full
7za x data/raw/raw_data.7z -odata/raw
python3 process_raw_data.py
pytest || [ $? -eq 5 ]
```

# 🗂️ Data Structure & Execution Workflow

The `raw_data.7z` archive contains the results of running the following pseudocode (all queries were executed sequentially on an free server, with the cache warmed up beforehand):

```python
for dop in [1, 16, 64]:
    for benchmark in ["JOB", "sample_queries", "tpch_10gb"]:
        for query in benchmark_queries:
            for hintset in HINTSETS:
                ...
                # 1. Plan the query and save the result and planning time
                #    using the `EXPLAIN` command (fields `hs_to_explain_plan`, 
                #    `hs_to_planning_time`).
                # 2. Execute the query and save the actual cardinalities and
                #    execution time using the `EXPLAIN ANALYZE (format json)`
                #    command. If the plan had already been executed, the results
                #    were reused. To avoid long wait times when there is
                #    significant degradation due to hint sets, a timeout was set
                #    to twice the execution time without any hints. This nuance
                #    requires special handling later because the execution time
                #    becomes effectively unknown.
```


# 🚀 How To 

The key object that allows emulation of DBMS operation is `Oracle` (terminology is taken from maths, no connection with @Oracle). The simplest examples of using its functionality are presented in `example.ipynb` 

[![example.ipynb](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/zinchse/hbo_bench/blob/main/example.ipynb)

**Example.** How to access the stored data _directly_:
```python
import json
dop = 1
benchmark_name = "JOB"
with open(f"data/raw/dop{dop}/{benchmark_name}.json", "r") as f:
    data = json.load(f)
    query_data = data["1b.sql"]
    explain_plan = query_data["hs_to_explain_plan"]["42"]
    explain_analyze_plan = query_data["explain_plan_to_explain_analyze_plan"][json.dumps(explain_plan)]
    planning_time = query_data["hs_to_planning_time"]["42"]
    execution_time = explain_analyze_plan["Total Runtime"]
```


# 🔗 Details

<details>
  <summary>Server's Settings</summary>

  All data were obtained on @OpenGauss RDBMS on the server with the following settings:

  | Parameter                          | Value          |
  |------------------------------------|----------------|
  | `max_process_memory`               | 200GB          |
  | `cstore_buffers`                   | 100GB          |
  | `work_mem`                         | 80GB           |
  | `effective_cache_size`             | 32GB           |
  | `standby_shared_buffers_fraction`  | 0.1            |
  | `shared_buffers`                   | 160GB          |

  | Parameter                          | Value          |
  |------------------------------------|----------------|
  | Architecture                       | aarch64        |
  | CPU op-mode(s)                     | 64-bit         |
  | Byte Order                         | Little Endian  |
  | CPU(s)                             | 128            |
  | On-line CPU(s) list                | 0-127          |
  | Thread(s) per core                 | 1              |
  | Core(s) per socket                 | 64             |
  | Socket(s)                          | 2              |
  | NUMA node(s)                       | 4              |
  | Vendor ID                          | HiSilicon      |
  | Model                              | 0              |
  | Model name                         | Kunpeng-920    |
  | Stepping                           | 0x1            |
  | CPU MHz                            | 2600.000       |
  | CPU max MHz                        | 2600.0000      |

</details>


<details>
  <summary>Hints</summary>
  
  We used the following list of hints, which are controlled by the corresponding global user configuration parameters (`GUC`s):
  
  ```python
  HINTS: "List[Hint]" = [
      "Nested Loop",
      "Merge",
      "Hash",
      "Bitmap",
      "Index Only Scan",
      "Index Scan",
      "Seq Scan",
  ]

  GUCS: "List[GUC]" = [
      "nestloop",
      "mergejoin",
      "hashjoin",
      "bitmapscan",
      "indexonlyscan",
      "indexscan",
      "seqscan",
  ]
  ```

  To enumerate all combinations of such hints, we simply use **bit masks** corresponding to the above order (the high bit is responsible for "Nested Loop", the low bit for "Seq Scan").
  
</details>

<details>
  <summary>Hint-based optimisation approach</summary>

 Due to errors during planning, not the most optimal operators / order of their application are chosen. In order to 
 help the optimiser to correct these errors you can tell it something like "don't use `operator_X`" using the `set enable_operator_X to off;` command. The planner will then assume
 that any use of this operator is much more expensive than it thought before (a _hardcoded_ constant is added), and will _probably_ prefer it to another operator.
 
</details>

<details>
  <summary>Exploration strategies</summary>
 <br>

 
   <b>Exhaustive Search</b>. 
   When searching for the best set of hints, the problem of exploring all possible combinations inevitably arises. The basic approach of examining every possible combination is quite computationally expensive. Below is a visualisation of such an algorithm for 4 hints (the set of hints is represented by a _bitmask_, where green shows useful combinations of hints and red shows bad ones. During optimisation by exhaustive algorithm we are obliged to explore all states.
  </p>

  <div style="text-align: center;">
    <figure style="display: inline-block;">
      <img src="https://github.com/zinchse/hbo_bench/blob/main/images/exhaustive_search.svg" alt="Exhaustive search" width="400"/>
    </figure>
  </div>

  <b>Greedy Search.</b> 
  Instead of exhaustive algorithm, **greedy** one can be employed. The essence of this approach is to iteratively expand the set of applied hints by adding one new hint that provides the greatest improvement to the current set. It reduces search space from exponential to quadratic. However, there are some **drawbacks** to the greedy algorithm. Firstly, it may not always lead to the optimal solution (purple star) due to greedy nature. Secondly, it is difficult to parallelize since it requires a sequential execution of several iterations.

  <div style="text-align: center;">
    <figure style="display: inline-block;">
      <img src="https://github.com/zinchse/hbo_bench/blob/main/images/greedy_search.svg" alt="Local Search" width="400"/>
    </figure>
  </div>

  <b>Local Search.</b> 
  The **local search** algorithm differs primarily in that it takes into account the specificity of hintsets and proposes to use additional transitions (dotted green line, we call it **shortcut**). As a result, it reaches the optimum much more a) **often** and b) **faster**.
  </p>

  <div style="text-align: center;">
    <figure style="display: inline-block;">
      <img src="https://github.com/zinchse/hbo_bench/blob/main/images/local_search.svg" alt="Local Search" width="400"/>
    </figure>
  </div>
</details>


# 📚 References

There are 2 main papers about the hint-based query optimisation approach.

1. [Marcus, Ryan, et al. "Bao: Making learned query optimization practical." *Proceedings of the 2021 International Conference on Management of Data*, 2021, pp. 1275-1288.](https://people.csail.mit.edu/hongzi/content/publications/BAO-Sigmod21.pdf)

2. [Anneser, Christoph, et al. "Autosteer: Learned query optimization for any SQL database." *Proceedings of the VLDB Endowment*, vol. 16, no. 12, 2023, pp. 3515-3527.](https://vldb.org/pvldb/vol16/p3515-anneser.pdf)
