**`TL;DR`** This is a reusable platform (data + wrappers) that allows running tens of thousands of experiments for query optimization using "hints" in just a few minutes on a laptop.

**⚡ Key Features:**
- Super fast prototyping of hint-based approaches cause of using look-up insted of real execution.
- Implemented `torch`-like `Dataset` and `DataLoader` objects for efficient data handling.
- Prototype (`query_explorer.py`) for experimenting with different query exploration strategies.

# 💡 Concept

Save all necessary data while developing a hint-based optimization approach, enabling a single look-up later instead of real execution. This dramatically reduces computation time during algorithm development.
We conducted ~2 week of computes and collected results for ~60K plans.


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


# ⓘ FAQ

<details>
  <summary><strong>What is the hint-based optimization?</strong></summary>

  Hint-Based query Optimization (HBO) is an approach to optimizing query execution time that accelerates workload execution without changing a single line of the DBMS kernel code. This is achieved by selecting planner hyperparameters (hints) that influence the construction of the query execution plan. Although this approach can greatly speed up query execution, it faces a fundamental challenges. In first, there's no universal hint. In second, the search space is exponential, and the cost of exploring a "point" within it depends on its execution time. As result, we must construct and train an intelligent hint-advisor to cope with them.

</details>

<details>
  <summary><strong>Why that platform is useful?</strong></summary>

  The main problem in hint-based optimization is that we don't know in advance what is the best hint set for a query. To find it, in general, we need to try all combinations. And the cost of each try is the time the query executes with such hints. This platform helped make us free from real execution, as a result, we can prototype solutions much faster. In practice, that platform allowed us to develop a well-balanced query explorer for selecting the best hint combination, outperforming state-of-the-art results of hint-based query optimization in both speed and overall performance. For details, see the repository of our paper **[HERO: New Learned Hint-based Efficient and Reliable Query Optimizer](https://github.com/zinchse/hero)**.
    
</details>

<details>
  <summary>How data were collected?</summary>

  For fast experimentation with tens of thousands of different hint exploration strategies we implemented the following approach: for every query from these benchmarks and for all possible hint combinations, we saved execution plans and their latencies obtained on [OpenGauss DB](https://opengauss.org/en/aboutUs/). This allowed us to replace actual query execution with a simple table lookup. To ensure the consistency of the collected data, the server was exclusively used during idle periods, with statistics updates disabled, and the database pre-warmed before each query execution.
  
</details>

<details>
  <summary><strong>What data benchmark are used?</strong></summary>
    
  For experimental evaluation, we used two IMDb-based benchmarks: [JOB benchmark](https://www.vldb.org/pvldb/vol9/p204-leis.pdf) consisting of 113 queries and its skewed version SQ (sample_queries from the [repository](https://dl.acm.org/doi/10.1145/3448016.3452838) of [Marcus, Ryan, et al. "Bao: Making learned query optimization practical."](https://people.csail.mit.edu/hongzi/content/publications/BAO-Sigmod21.pdf)) with 40 queries. Additionally, we used [TPCH benchmark](https://www.tpc.org/tpch/) with 22 queries, with a scale factor of 10.

</details>

<details>
  <summary>Which hints were used?</summary>
  
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
  <summary>What is the configuration of used server?</summary>

  All data were obtained on [OpenGauss DB](https://opengauss.org/en/aboutUs/) 
 on the server with the following settings:

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

# 📚 References

There are two main papers on the hint-based query optimization approach and useful links:

1. [Marcus, Ryan, et al. "Bao: Making learned query optimization practical." *Proceedings of the 2021 International Conference on Management of Data*, 2021, pp. 1275-1288.](https://people.csail.mit.edu/hongzi/content/publications/BAO-Sigmod21.pdf)

2. [Anneser, Christoph, et al. "Autosteer: Learned query optimization for any SQL database." *Proceedings of the VLDB Endowment*, vol. 16, no. 12, 2023, pp. 3515-3527.](https://vldb.org/pvldb/vol16/p3515-anneser.pdf)
