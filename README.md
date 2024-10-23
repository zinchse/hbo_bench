**`TL;DR`** This is a reusable platform (data + wrappers) that allows running tens of thousands of experiments for query optimization using so-called hints in just *a few minutes* on a laptop. The idea is that almost all necessary calculations have been cached (~`2W` of compute, `60K`+ plans), and instead of real query execution, we simply perform look-up operation in the table.

**Contribution:**
- Collected cached query execution results using different sets of hints.
- Implemented `torch`-like `Dataset` and `DataLoader` objects for efficient data handling.

# 💡 Idea Behind This Benchmark

**H**int-**B**ased query **O**ptimization (HBO) is an approach to optimizing query execution time that accelerates workload execution without changing a single line of the DBMS kernel code. This is achieved by selecting planner hyperparameters (*hints*) that influence the construction of the query execution plan. Although this approach can greatly speed up query execution, it faces a fundamental challenge — the search space is **exponential**, and the cost of exploring a "point" within it **depends on its execution time**.

# 🧐 Why Is This Benchmark Useful?

<div style="display: flex; justify-content: center; align-items: center; gap: 20px;">
    <img src="https://github.com/user-attachments/assets/af13aa42-b01b-44eb-9670-747fc59dce7d" alt="image" width="600"/>
</div>

Our benchmark provides a reusable platform that enables rapid experimentation with various query optimization algorithms. By leveraging this benchmark, we developed a new Local Search algorithm that significantly outperforms existing approaches. A key innovation is the expansion of the operation-related parameter space. By introducing parallelism control, we extended the traditional optimization space to include dop. 
```math
\Theta = \underbrace{\Theta_{scans} \times \Theta_{joins}}_{\Theta_{ops}} \times \textcolor{Maroon}{\mathbf{\Theta_{dop}}}.
```
This expansion allowed us to achieve a 3x acceleration in query performance, compared to the previous 2x, setting a **new standard** for hint-based optimization. While expanding the search space offers more optimization opportunities, it also makes finding optimal solutions more complex. We tackled this challenge by developing a highly efficient Local Search algorithm. This algorithm incorporates multiple optimizations, allowing it to navigate the expanded search space **(a)** quickly and **(b)** effectively, providing fast convergence to solutions that were previously unattainable.

<div style="display: flex; justify-content: space-between; align-items: center;">
    <img src="https://github.com/user-attachments/assets/e1ca29c4-518a-4e66-949e-097da11fcd14" alt="image1" style="height: 250px;"/>
    <img src="https://github.com/user-attachments/assets/82cc8d8a-2b04-4d5d-9077-7aede5951fe7" alt="image2" style="height: 250px;"/>
</div>

# 📦 Setup

```shell
python -m pip install --upgrade pip
python3 -v venv venv
source venv/bin/activate
pip install -e .
sudo apt-get install -y p7zip-full
7za x src/hbo_bench/data/raw/raw_data.7z -osrc/hbo_bench/data/raw
python3 process_raw_data.py
pytest || [ $? -eq 5 ]
```

# 🗂️ Data Structure & Execution Workflow

The `raw_data.7z` archive contains results obtained by running the following pseudocode (all queries were executed sequentially on a free server, with the cache warmed up beforehand):

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

The key object that allows emulation of DBMS operation is `Oracle` (terminology is taken from mathematics, not connected with @Oracle). Simple examples of using its functionality are presented in `example.ipynb`

[![example.ipynb](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/zinchse/hbo_bench/blob/main/src/hbo_bench/example.ipynb)

**Example:** How to access the stored data _directly_:
```python
import json
dop = 1
benchmark_name = "JOB"
with open(f"src/hbo_bench/data/raw/dop{dop}/{benchmark_name}.json", "r") as f:
    data = json.load(f)
    query_data = data["1b.sql"]
    explain_plan = query_data["hs_to_explain_plan"]["42"]
    explain_analyze_plan = query_data["explain_plan_to_explain_analyze_plan"][json.dumps(explain_plan)]
    planning_time = query_data["hs_to_planning_time"]["42"]
    # sometimes it won't work due to T/O, there's guarantee only for default hintset (0)
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
  
  The following list of hints was used, controlled by the corresponding global user configuration parameters (`GUC`s):
  
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

  To enumerate all combinations of such hints, we simply use **bit masks** corresponding to the order above (the high bit is responsible for "Nested Loop", and the low bit for "Seq Scan").
</details>

<details>
  <summary>Hint-Based Optimization Approach</summary>

 Due to errors during planning, the most optimal operators or the order of their application might not be selected. To help the optimizer correct these errors, you can tell it something like "don't use `operator_X`" using the `set enable_operator_X to off;` command. The planner will then assume that any use of this operator is much more expensive than it initially thought (a _hardcoded_ constant is added), and will _likely_ prefer another operator.
</details>

<details>
  <summary>Exploration Strategies</summary>
 <br>

 
   <b>Exhaustive Search</b>. 
   When searching for the best set of hints, the problem of exploring all possible combinations inevitably arises. The basic approach of examining every possible combination is computationally expensive. Below is a visualization of such an algorithm for 4 hints (the set of hints is represented by a _bitmask_, where green shows useful combinations of hints and red shows bad ones). During optimization by the exhaustive algorithm, we are required to explore all states:
  </p>

  <div style="text-align: center;">
    <figure style="display: inline-block;">
      <img src="https://github.com/zinchse/hbo_bench/blob/main/images/exhaustive_search.svg" alt="Exhaustive search" width="400"/>
    </figure>
  </div>

  <b>Greedy Search.</b> 
  Instead of the exhaustive algorithm, a **greedy** one can be employed. This approach iteratively expands the set of applied hints by adding one new hint that provides the greatest improvement to the current set. It reduces the search space from exponential to quadratic. However, there are some **drawbacks** to the greedy algorithm. Firstly, it may not always lead to the optimal solution (purple star) due to its greedy nature. Secondly, it is difficult to parallelize since it requires a sequential execution of several iterations.

  <div style="text-align: center;">
    <figure style="display: inline-block;">
      <img src="https://github.com/zinchse/hbo_bench/blob/main/images/greedy_search.svg" alt="Local Search" width="400"/>
    </figure>
  </div>

  <b>Local Search.</b> 
  The **local search** algorithm differs primarily in that it considers the specificity of hint sets and proposes using additional transitions (dotted green line, referred to as **shortcut**). As a result, it reaches the optimum more a) **often** and b) **faster**.
  </p>

  <div style="text-align: center;">
    <figure style="display: inline-block;">
      <img src="https://github.com/zinchse/hbo_bench/blob/main/images/local_search.svg" alt="Local Search" width="400"/>
    </figure>
  </div>
</details>


# 📚 References

There are two main papers on the hint-based query optimization approach:

1. [Marcus, Ryan, et al. "Bao: Making learned query optimization practical." *Proceedings of the 2021 International Conference on Management of Data*, 2021, pp. 1275-1288.](https://people.csail.mit.edu/hongzi/content/publications/BAO-Sigmod21.pdf)

2. [Anneser, Christoph, et al. "Autosteer: Learned query optimization for any SQL database." *Proceedings of the VLDB Endowment*, vol. 16, no. 12, 2023, pp. 3515-3527.](https://vldb.org/pvldb/vol16/p3515-anneser.pdf)
