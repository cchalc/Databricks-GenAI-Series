# Databricks notebook source
dbutils.widgets.text("catalog_name","cjc")

# COMMAND ----------

# MAGIC %run ./init/config $catalog_name=$catalog_name

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

current_user = spark.sql("SELECT current_user() as username").collect()[0].username
schema_name = f'genai_workshop_{current_user.split("@")[0].split(".")[0]}'

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC # Prompt Engineering
# MAGIC
# MAGIC Prompt engineering is a critical aspect of interacting effectively with Large Language Models (LLMs). It involves crafting prompts that can be appended to user inputs that guide the model to generate the most relevant and accurate outputs. This skill is valuable for several reasons:
# MAGIC
# MAGIC 1. **Precision and Relevance**: Well-engineered prompts help the model understand the context and specificity of the query, leading to more precise and relevant responses.
# MAGIC 2. **Efficiency**: Effective prompts can reduce the number tokens generated by the model, while still maintaining accuracy/correctness. This saves time and computational resources.
# MAGIC 3. **Creative and Complex Tasks**: For tasks that require creativity or complex problem-solving, carefully designed prompts can significantly improve the quality of the model's output.

# COMMAND ----------

# MAGIC %md
# MAGIC %md
# MAGIC <img src="https://daxg39y63pxwu.cloudfront.net/images/blog/langchain/LangChain.webp" alt="LangChain" width="700"/>
# MAGIC
# MAGIC
# MAGIC ## LangChain 
# MAGIC LangChain is a framework designed to simplify the creation of applications using large It enables applications that:
# MAGIC     - Are context-aware: connect a language model to sources of context (prompt instructions, few shot examples, content to ground its response in, etc.)
# MAGIC     - Reason: rely on a language model to reason (about how to answer based on provided context, what actions to take, etc.) language models.

# COMMAND ----------

import langchain
print(langchain.__version__)

# COMMAND ----------

# DBTITLE 1,Call Llama 70B for this Lab
import os
from langchain.llms import HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain.chat_models import ChatDatabricks

#call llama2 70B, hosted by Databricks (context length of 4,096 tokens)
llama_model = ChatDatabricks(endpoint="databricks-llama-2-70b-chat", max_tokens = 400)

# COMMAND ----------

# DBTITLE 1,Start with a Simple Question about Spark Joins
user_question = "How can I speed up my Spark join operation?"
llama_model.predict(user_question)

# COMMAND ----------

# DBTITLE 1,Creating a Prompt Template to Append to our Inputs
from langchain import PromptTemplate # PromptTemplate is a class in LangChain used to create reusable and parameterized prompt templates
from langchain.chains import LLMChain

#now, let's create a prompt template to make our incoming queries databricks-specific
intro_template = """
You are a Databricks support engineer tasked with answering questions about Spark. Include Databricks-relevant information in your response and be as prescriptive as possible. Cite Databricks documentation for your answers
User Question:" {question}"
"""

# COMMAND ----------

# DBTITLE 1,Create an LLM Chain that appends our Template to the User Input
prompt_template = PromptTemplate(
    input_variables=["question"],
    template=intro_template,
)

llama_chain = LLMChain(
    llm=llama_model,
    prompt=prompt_template,
    output_key="Support Response",
    verbose=False
)

llama_chain_response = llama_chain.run({"question":user_question})
print(llama_chain_response)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## Zero-Shot Prompting
# MAGIC Don't provide any examples to the model, and just ask the question
# MAGIC
# MAGIC ## Few Shot Prompting
# MAGIC Provide N examples to the model to help guide it's response

# COMMAND ----------

# DBTITLE 1,Helper Function to our LLM Chains
def run_llm_chain(input_string, template_string, model):
  """
  given an input string, template, and model, execute a langchain chain on the input with a given prompt template

  params
  ==========
  input_string (str): the incoming query from a user to be evaluated
  template_string (str): prompt template append or pre-pend to input_string (required for prompt engineering)
  model (langchain model): the name of the model 
  """
  prompt_template = PromptTemplate(
    input_variables=["input_string"],
    template=template_string,
  )
  model_chain = LLMChain(
    llm=model,
    prompt=prompt_template,
    output_key="Response",
    verbose=False
  )

  return model_chain.run({"input_string": input_string})

# COMMAND ----------

# DBTITLE 1,Create our Zero and Few Shot Prompts
zero_shot_template = """For each tweet, describe its sentiment:
                        [Tweet]: {input_string}
                      """

few_shot_template = """For each tweet, describe its sentiment:
                        [Tweet]: "I hate it when my phone battery dies."
                        [Sentiment]: Negative
                        ###
                        [Tweet]: "My day has been 👍"
                        [Sentiment]: Positive
                        ###
                        [Tweet]: "This is the link to the article"
                        [Sentiment]: Neutral
                        ###
                        [Tweet]: {input_string}
                        [Sentiment]:
                      """

# COMMAND ----------

tweet = "My day has been ugh"
zero_shot_response = run_llm_chain(tweet, zero_shot_template, llama_model)
print(zero_shot_response)

# COMMAND ----------

few_shot_response = run_llm_chain(tweet, few_shot_template, llama_model)
print(few_shot_response)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Chain of Thought Prompting
# MAGIC
# MAGIC Chain of thought prompting makes the LLM step through it's decision-making process. This makes it easier to better understand model outputs or identify hallucinations

# COMMAND ----------

apples = """
"Imagine you are at a grocery store and need to buy apples. They are sold in bags of 6 apples each and cost $2 per bag. If you need 20 apples for a recipe, how many bags should you buy and how much will it cost?
"""

llama_model.predict(apples)

# COMMAND ----------

chain_of_reasoning_prompt = """
                            For the following question, answer the question, but walk through your line of reasining step by step to arrive at the answer:

                            {input_string}
                            """

cor_response = run_llm_chain(apples, chain_of_reasoning_prompt, llama_model)
print(cor_response)

# COMMAND ----------

# MAGIC %md
# MAGIC # No Hallucinations!
# MAGIC
# MAGIC Finally, you can tell your model not to hallucinate. LLMs typically return a confidence score for their output sequence, so you can explicitly tell the model not to respond if it feels it does not have enough information to answer

# COMMAND ----------

no_hallucinations_prompt = """
                            For the following question, only respond if you have sufficient information to generate a confident answer. If you cannot do so, then simply respond 'Sorry - I don't have enough information to answer that.'

                            Question:
                            {input_string}
                            """

# COMMAND ----------

liquid_cluster = "What is liquid clustering on Databricks?"
llama_model.predict(liquid_cluster)

# COMMAND ----------

run_llm_chain(liquid_cluster, no_hallucinations_prompt, llama_model)

# COMMAND ----------

# MAGIC %md
# MAGIC # Saving our LangChain LLM Chain to MLflow
# MAGIC This should look familiar!

# COMMAND ----------

from mlflow.models import infer_signature

input_str="How can I speed up my Spark joins?"
prediction = llama_chain.run(input_str)
input_columns = [
    {"type": "string", "name": input_key} for input_key in llama_chain.input_keys
]
signature = infer_signature(input_columns, prediction)

# COMMAND ----------

print(type(signature))
signature.to_dict()

# COMMAND ----------

import mlflow
import cloudpickle

# Create a new mlflow experiment or get the existing one if already exists.
current_user = spark.sql("SELECT current_user() as username").collect()[0].username
experiment_name = f"/Users/{current_user}/genai-prompt-engineering-workshop"
mlflow.set_experiment(experiment_name)

# set the name of our model
model_name = "2langchainz-llama70b"

# get experiment id to pass to the run
experiment_id = mlflow.get_experiment_by_name(experiment_name).experiment_id
with mlflow.start_run(experiment_id=experiment_id):
    mlflow.langchain.log_model(
        llama_chain,
        model_name,
        signature=signature,
        input_example=input_str,
        pip_requirements=[
            "mlflow==" + mlflow.__version__,
            "langchain==" + langchain.__version__,
            "databricks-vectorsearch",
            "pydantic==2.5.2 --no-binary pydantic",
            "cloudpickle==" + cloudpickle.__version__,
        ]
    )

# COMMAND ----------

import mlflow

#grab our most recent run (which logged the model) using our experiment ID
runs = mlflow.search_runs([experiment_id])
last_run_id = runs.sort_values('start_time', ascending=False).iloc[0].run_id

#grab the model URI that's generated from the run
model_uri = f"runs:/{last_run_id}/{model_name}"

#log the model to catalog.schema.model. The schema name referenced below is generated for you in the init script
catalog = dbutils.widgets.get("catalog_name")
schema = schema_name

#set our registry location to Unity Catalog
mlflow.set_registry_uri("databricks-uc")
mlflow.register_model(
    model_uri=model_uri,
    name=f"{catalog}.{schema}.{model_name}"
)

# COMMAND ----------


