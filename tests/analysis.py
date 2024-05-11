# to use analytics tools you need to install some extra libraries
# !pip install pandas

from tests.candidate import complete_interview
from tests.grader import grade
import pandas as pd
from functools import partial
import concurrent.futures
import os
from IPython.display import display


def complete_and_grade(interview_params, exp_name="GPT4", grader_model="gpt-4-turbo", candidate_model="gpt-3.5-turbo"):
    interview_type, attempt_num = interview_params
    feedback = {}

    try:
        file_path, _ = complete_interview(interview_type, exp_name, model=candidate_model)
        feedback = grade(file_path, grader_model)

        # Just a heuristic check of the JSON format TODO: add a proper check
        if "problem_statement_topic" not in feedback:
            raise Exception("Grading failed")

        print(f"Attempt {attempt_num + 1} of {interview_type} completed successfully")
        print(f"Overall score: {feedback['overall_score']}")

    except Exception as e:
        print(f"Attempt {attempt_num + 1} of {interview_type} failed with error: {e}")

    return feedback


def run_evaluation(
    exp_name,
    num=5,
    interview_types=["ml_design", "math", "ml_theory", "system_design", "sql", "coding"],
    grader_model="gpt-4-turbo",
    candidate_model="gpt-3.5-turbo",
    num_workers=3,
):
    exp_name = f"{exp_name}_{pd.Timestamp.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    os.makedirs(f"records/{exp_name}", exist_ok=True)
    tasks = [(interview_type, i) for i in range(num) for interview_type in interview_types]
    complete_f = partial(complete_and_grade, exp_name=exp_name, grader_model=grader_model, candidate_model=candidate_model)
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(complete_f, tasks))

    # Filter out empty results and count them
    non_empty_results = [res for res in results if res]
    empty_count = len(results) - len(non_empty_results)

    print(f"Number of empty results (errors or failed grading): {empty_count}")

    # Store non-empty results in a DataFrame
    df = pd.DataFrame(non_empty_results)
    df.to_csv(os.path.join("records", exp_name, "results.csv"), index=False)

    return exp_name


def highlight_color(val):
    color = "red" if val < 0.7 else "orange" if val < 0.9 else "lightgreen" if val < 0.95 else "green"
    return f"color: {color}"


def generate_and_display_tables(df):
    # Grouping by prefix
    prefixes = ["problem", "interviewer", "feedback"]
    prefix_columns = [col for col in df.columns if any(col.startswith(prefix) for prefix in prefixes)]

    criteria_summary_df = pd.DataFrame(df[prefix_columns].mean(), columns=["avg score"])
    criteria_summary_df_styled = criteria_summary_df.style.map(highlight_color)
    criteria_summary_df_styled.set_caption("Aggregated Scores per Criteria")

    # Aggregated scores per stage
    grouped_scores = {}
    for prefix in prefixes:
        prefix_cols = [col for col in df.columns if col.startswith(prefix)]
        grouped_scores[prefix] = df[prefix_cols].mean(axis=1).mean()

    grouped_scores_df = pd.DataFrame([grouped_scores]).T
    grouped_scores_df.columns = ["avg score"]
    grouped_scores_styled = grouped_scores_df.style.map(highlight_color)
    grouped_scores_styled.set_caption("Aggregated Scores per Stage")

    # Grouped by unique type
    grouped_by_type = pd.DataFrame(df.groupby("type")[prefix_columns].mean().mean(axis=1), columns=["avg score"])
    grouped_by_type_styled = grouped_by_type.style.map(highlight_color)
    grouped_by_type_styled.set_caption("Scores Grouped by Unique Type")

    # Grouped by unique interviewer model and sorted by descending total score
    total_llm_scores = df.groupby("agent_llm")[prefix_columns].mean().mean(axis=1).sort_values(ascending=False)
    grouped_by_interviewer = pd.DataFrame(total_llm_scores, columns=["avg score"])
    grouped_by_interviewer_styled = grouped_by_interviewer.style.map(highlight_color)
    grouped_by_interviewer_styled.set_caption("Scores Grouped by Unique Interviewer Model")

    for prefix in prefixes:
        prefix_cols = [col for col in prefix_columns if col.startswith(prefix)]
        df[prefix] = df[prefix_cols].mean(axis=1)

    # Pivot table: Agent model vs Stage
    pivot1 = pd.pivot_table(df, values=prefixes, index="agent_llm", aggfunc="mean").reindex(total_llm_scores.index)
    pivot1_styled = pivot1.style.map(highlight_color)
    pivot1_styled.set_caption("Pivot Table: Agent Model vs Stage")

    # Pivot table: Agent model vs Type (Single aggregated score per type)
    pivot2 = pd.pivot_table(df, values="overall_score", index="agent_llm", columns="type", aggfunc="mean").reindex(total_llm_scores.index)
    pivot2_styled = pivot2.style.map(highlight_color)
    pivot2_styled.set_caption("Pivot Table: Agent Model vs Type")

    # Pivot table: Type vs Stage
    pivot3 = pd.pivot_table(df, values=prefixes, index="type", aggfunc="mean")
    pivot3_styled = pivot3.style.map(highlight_color)
    pivot3_styled.set_caption("Pivot Table: Type vs Stage")

    # Pivot table: Agent Model x Stage vs Type (MultiIndex)
    multi_index_data = [(llm, stage) for llm in total_llm_scores.index for stage in prefixes]
    multi_index = pd.MultiIndex.from_tuples(multi_index_data, names=["agent_llm", "stage"])
    types = df["type"].unique()
    pivot4_df = pd.DataFrame(index=multi_index, columns=types)

    # Fill the DataFrame with the aggregated scores grouped by type
    for llm in total_llm_scores.index:
        for stage in prefixes:
            mask = df["agent_llm"] == llm
            stage_values = df.loc[mask, ["type", stage]].groupby("type").mean()[stage]
            pivot4_df.loc[(llm, stage), :] = stage_values

    pivot4_styled = pivot4_df.style.map(highlight_color)
    pivot4_styled.set_caption("Pivot Table: Agent Model x Stage vs Type")

    tables_dict = {
        "criteria_summary_df_styled": criteria_summary_df_styled,
        "grouped_scores_styled": grouped_scores_styled,
        "grouped_by_type_styled": grouped_by_type_styled,
        "grouped_by_interviewer_styled": grouped_by_interviewer_styled,
        "pivot1_styled": pivot1_styled,
        "pivot2_styled": pivot2_styled,
        "pivot3_styled": pivot3_styled,
        "pivot4_styled": pivot4_styled,
    }

    for table in tables_dict.values():
        display(table)

    return tables_dict
