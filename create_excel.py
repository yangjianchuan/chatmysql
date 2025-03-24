import json
import pandas as pd
import re

# Read the training data
data = []
with open('training_data.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            data.append(json.loads(line))

# Extract the questions and answers
qa_pairs = []
for item in data:
    messages = item['messages']
    question = messages[0]['content']
    
    # Extract just the SQL query from the answer
    answer_content = messages[1]['content']
    sql_match = re.search(r'```sql\n(.*?)```', answer_content, re.DOTALL)
    if sql_match:
        sql_query = sql_match.group(1).strip()
        qa_pairs.append({"问题": question, "答案": sql_query})

# Create a DataFrame and save as Excel
df = pd.DataFrame(qa_pairs)
df.to_excel('output/qa_table.xlsx', index=False)

print("Excel file created successfully at output/qa_table.xlsx") 