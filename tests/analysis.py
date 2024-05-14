# This file contains some functions I use for automated analysis and evaluation
# It is not used in the main functionality of the service
# It is quite messy so far
# to use analytics tools you need to install some extra libraries
# !pip install pandas

from tests.candidate import complete_interview
from tests.grader import grade
import pandas as pd
import numpy as np
from functools import partial
import concurrent.futures
import os
from IPython.display import Markdown, display
from openai import OpenAI
from tests.testing_prompts import feedback_analyzer
from resources.prompts import prompts, base_prompts

criteria_list = {
    "problem_statement",
    "problem_statement_difficulty",
    "problem_statement_topic",
    "problem_statement_solvability",
    "problem_statement_relevance",
    "problem_statement_mistakes",
    "problem_statement_solution",
    "problem_statement_hints",
    "problem_statement_answer_plan",
    "problem_statement_instructions",
    "problem_statement_goals_alignment",
    "problem_statement_skill_test",
    "interviewer_solution",
    "interviewer_mistakes",
    "interviewer_answers",
    "interviewer_relevance",
    "interviewer_support",
    "interviewer_questions",
    "interviewer_repeat",
    "interviewer_found_mistakes",
    "interviewer_hallucinations",
    "interviewer_summary",
    "interviewer_gaslighting",
    "interviewer_leaks",
    "interviewer_empty",
    "interviewer_notes",
    "interviewer_stuck",
    "interviewer_end",
    "interviewer_adaptability",
    "interviewer_flow_control",
    "interviewer_preparation",
    "interviewer_responsive",
    "interviewer_depth",
    "feedback_quality",
    "feedback_overview",
    "feedback_relevance",
    "feedback_clarity",
    "feedback_solution",
    "feedback_result",
    "feedback_hallucinations",
    "feedback_focus",
    "feedback_completeness",
    "feedback_examples",
    "feedback_specificity",
    "comments",
}


def grade_attempt(file_path, grader_model, attempt_index):
    for retry in range(3):  # Retry mechanism
        try:
            feedback = grade(file_path, grader_model, str(attempt_index))
            if np.mean([x in criteria_list for x in feedback.keys()]) > 0.8:
                return feedback
        except Exception as e:
            print(f"The {retry+1} attempt to grade using {grader_model} failed with error {e}")
    return None


def complete_and_grade(interview_params, exp_name, grader_models, candidate_model):
    interview_type, attempt_num, llm_config = interview_params

    feedback_list = []
    attempt_successful = False
    for attempt in range(3):  # Retry up to 3 times
        try:
            file_path, _ = complete_interview(interview_type, exp_name, llm_config, model=candidate_model, pause=attempt * 5)
            print(
                f"Attempt {attempt_num + 1}, retry {attempt + 1} interview simulation of {interview_type} by {llm_config.name} completed successfully"
            )
            attempt_successful = True
            break
        except Exception as e:
            print(f"Retry {attempt + 1} for attempt {attempt_num + 1} of {interview_type} by {llm_config.name} failed with error: {e}")

    if not attempt_successful:
        print(f"All retries failed for attempt {attempt_num + 1} of {interview_type} by {llm_config.name}")
        return feedback_list

    try:
        for i, grader_model in enumerate(grader_models):
            feedback = grade_attempt(file_path, grader_model, i)
            if feedback:
                feedback_list.append(feedback)
                print(f"Attempt {attempt_num + 1} of {interview_type} by {llm_config.name} graded by {grader_model} successfully")
                print(f"Overall score: {feedback['overall_score']}")

    except Exception as e:
        print(f"Grading for attempt {attempt_num + 1} of {interview_type} by {llm_config.name} failed with error: {e}")

    if len(feedback_list) == 0:
        print(f"Attempt {attempt_num + 1} of {interview_type} by {llm_config.name} returned an empty list")

    return feedback_list


def run_evaluation(
    exp_name, num_attempts=5, interview_types=None, grader_models=None, llm_configs=None, candidate_model="gpt-3.5-turbo", num_workers=3
):
    if interview_types is None:
        interview_types = ["ml_design", "math", "ml_theory", "system_design", "sql", "coding"]
    if grader_models is None:
        grader_models = ["gpt-4o"]
    if llm_configs is None:
        llm_configs = [None]

    exp_name = f"{exp_name}_{pd.Timestamp.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    os.makedirs(f"records/{exp_name}", exist_ok=True)
    tasks = [(type_, i, llm_config) for i in range(num_attempts) for type_ in interview_types for llm_config in llm_configs]
    complete_f = partial(complete_and_grade, exp_name=exp_name, grader_models=grader_models, candidate_model=candidate_model)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(complete_f, tasks))

    # Filter out empty results
    non_empty_results = [res for res in results if res]
    empty_count = len(results) - len(non_empty_results)
    print(f"Number of empty results (errors or failed grading): {empty_count}")

    non_empty_results = [f for res in non_empty_results for f in res]
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

    total_llm_scores = df.groupby("agent_llm")[prefix_columns].mean().mean(axis=1).sort_values(ascending=False)
    # Grouped by unique interviewer model and sorted by descending total score
    grouped_by_interviewer = (
        df.groupby("agent_llm")[["overall_score", "average_response_time_seconds", "number_of_messages"]]
        .mean()
        .reindex(total_llm_scores.index)
    )
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


def filter_df(df, prefixes=["problem", "interviewer", "feedback"]):
    # Identify all columns starting with any of the prefixes
    columns_to_check = [col for col in df.columns if any(col.startswith(prefix) for prefix in prefixes)]

    # Function to check if a value is a boolean, None, or string representations of boolean types
    def is_valid_value(val):
        return isinstance(val, bool) or val is None or val is np.nan or val in {"True", "False", "None", "NaN"}

    # Function to convert string representations to actual booleans
    def to_bool(val):
        if val == "True":
            return True
        elif val == "False":
            return False
        elif val == "None":
            return None
        return val

    # Check if all values in the specified columns are valid
    def all_values_valid(row):
        return all(is_valid_value(row[col]) for col in columns_to_check)

    # Apply filtering to keep only rows with valid values
    valid_df = df[df.apply(all_values_valid, axis=1)].copy()

    # Convert string representations to booleans
    for col in columns_to_check:
        valid_df[col] = valid_df[col].apply(to_bool)

    # Identify removed rows
    removed_rows = df[~df.index.isin(valid_df.index)]

    # Print the number of rows removed
    num_removed = len(removed_rows)
    print(f"Number of rows removed: {num_removed}")

    # Print the value from the "file_name" column for each removed row, or `None` if not present
    if "file_name" in removed_rows.columns:
        for value in removed_rows["file_name"].tolist():
            print(f"Removed row file_name: {value}")
    else:
        print("Removed row file_name: None")

    return valid_df


def generate_analysis_report(df, folder, focus=None, model="gpt-4o"):

    client = OpenAI(base_url="https://api.openai.com/v1")

    all_comments = "\n\n".join([f"Interview type: {t}. Feedback: {str(f)}" for t, f in zip(df["type"].values, df["comments"].values)])

    messages = [
        {"role": "system", "content": feedback_analyzer},
        {"role": "user", "content": f"Interview feedback: {all_comments}"},
    ]

    if focus:
        messages.append({"role": "user", "content": f"Focus only on comments about {focus} part of the interview"})

    response = client.chat.completions.create(model=model, messages=messages, temperature=1)

    comments_analysis = response.choices[0].message.content
    display(Markdown(comments_analysis))

    if folder is not None:
        with open(os.path.join(folder, "analysis.md"), "w") as f:
            f.write(comments_analysis)
            f.write("\n\n")
            for t in np.unique(df["type"]):
                f.write(f"Type: {t}\n")
                f.write(df[[c for c in df.columns if c != "comments"]][df["type"] == t].T.to_markdown())
                f.write("\n\n")
            f.write(f"Type: all\n")
            f.write("\n\n")
            f.write("Feedback:\n")
            f.write(all_comments)

    return comments_analysis


def analyze_and_improve_segment(df, segment_to_improve=None):

    sorted_stages = df[["problem", "interviewer", "feedback"]].mean().sort_values()
    if not segment_to_improve:
        segment_to_improve = sorted_stages.index[0]
    th_score = sorted_stages.iloc[0] + 0.1

    print(f"Let's try to improve {segment_to_improve}")
    print(f"Quality threshold {th_score}")

    # Identifying types that need improvement
    type_stage_scores = df.groupby("type")[segment_to_improve].mean()
    types_to_improve = []
    for t, s in type_stage_scores.items():
        if s < th_score:
            types_to_improve.append(t)

    print(f"We will focus on {types_to_improve}")

    # Filtering DataFrame based on identified types and scoring criteria
    filtered_df = df[df["type"].apply(lambda x: x in types_to_improve)]
    prefix_columns = [col for col in df.columns if col.startswith(segment_to_improve)]
    filtered_df = filtered_df[filtered_df[prefix_columns].mean(axis=1) < th_score]

    # Generating an analysis report
    comments_analysis = generate_analysis_report(filtered_df, None, focus=segment_to_improve, model="gpt-4o")

    # Constructing improvement prompt
    improvement_prompt = """You want to improve the prompts for LLM interviewer.
Below you will see some of the prompts that are used right now. 
As well as a summary of mistakes that interviewer make.
You can add 1-3 lines to each of prompts if needed, but you can't change or remove anything.
"""

    # Selecting the base prompt for the segment to improve
    base_prompt = base_prompts.get(f"base_{segment_to_improve}", "Base prompt not found for the segment")

    # Constructing the current prompts display
    current_prompts = "The current prompts are below. \n"
    current_prompts += "BASE PROMPT (applied to all interview types): \n"
    current_prompts += base_prompt + "\n"

    for k, v in prompts.items():
        if segment_to_improve in k:
            current_prompts += f"{k}: {v[len(base_prompt):]} \n\n"

    # Making API call to OpenAI
    client = OpenAI(base_url="https://api.openai.com/v1")
    model = "gpt-4o"
    messages = [
        {"role": "system", "content": improvement_prompt},
        {"role": "user", "content": current_prompts},
        {"role": "user", "content": f"Interview feedback: {comments_analysis}"},
        {"role": "user", "content": "Please return any additional instructions you would like to add to any of the prompts."},
    ]

    response = client.chat.completions.create(model=model, messages=messages, temperature=1).choices[0].message.content
    print(response)
