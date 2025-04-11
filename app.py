from flask import Flask, request, Response, jsonify, stream_with_context
from flask_cors import CORS
from openai import OpenAI
import mysql.connector
from mysql.connector import Error
from datetime import datetime, date
import json
from dotenv import load_dotenv
import os
from decimal import Decimal
import re

# Custom JSON encoder to handle Decimal and date
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
app.json_encoder = CustomJSONEncoder

# Initialize OpenAI clients for SQL generation and summarization
sql_client = OpenAI(
    api_key=os.getenv("SQL_API_KEY", os.getenv("OPENAI_API_KEY")),
    base_url=os.getenv("SQL_BASE_URL", os.getenv("OPENAI_BASE_URL"))
)

summary_client = OpenAI(
    api_key=os.getenv("SUMMARY_API_KEY", os.getenv("OPENAI_API_KEY")),
    base_url=os.getenv("SUMMARY_BASE_URL", os.getenv("OPENAI_BASE_URL"))
)

def get_db_connection():
    config = {
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'host': os.getenv('MYSQL_HOST'),
        'port': int(os.getenv('MYSQL_PORT')),
        'database': os.getenv('MYSQL_DATABASE'),
        'raise_on_warnings': os.getenv('MYSQL_RAISE_ON_WARNINGS') == 'True',
        'auth_plugin': os.getenv('MYSQL_AUTH_PLUGIN'),
        'connection_timeout': int(os.getenv('MYSQL_CONNECTION_TIMEOUT')),
        'use_pure': True,  # 使用纯Python实现，避免C扩展可能导致的段错误
        'get_warnings': True,  # 启用警告获取
        'buffered': True  # 使用缓冲查询，避免内存问题
    }
    return mysql.connector.connect(**config)

def execute_sql(sql):
    try:
        # 添加 Match 类用于模拟正则匹配对象
        class Match:
            def __init__(self, string, start, end, groups):
                self.string = string
                self.start = lambda: start
                self.end = lambda: end
                self._groups = groups
            
            def group(self, index):
                return self._groups[index] if index < len(self._groups) else None

        # Clean up SQL query by removing newlines, backslashes and normalizing spaces
        cleaned_sql = sql.strip()
        # Remove backslashes that are followed by whitespace or newline
        cleaned_sql = cleaned_sql.replace('\\\n', '\n').replace('\\ ', ' ')
        
        # 定义 SQL 关键字列表
        sql_keywords = {
            'SELECT', 'FROM', 'WHERE', 'GROUP', 'ORDER', 'BY', 'HAVING', 'JOIN',
            'LEFT', 'RIGHT', 'INNER', 'WITH', 'AS', 'ON', 'AND', 'OR', 'IN', 'NOT',
            'NULL', 'IS', 'OVER', 'PARTITION', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'DISTINCT',
            'UNION', 'ALL', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'LIKE', 'IN',
            'BETWEEN', 'EXISTS', 'ANY', 'SOME', 'LIMIT', 'OFFSET', 'ASC', 'DESC',
            'UPDATE', 'DELETE', 'INSERT', 'INTO', 'VALUES', 'SET', 'TRUNCATE',
            'TABLE', 'DATABASE', 'SCHEMA', 'INDEX', 'VIEW', 'PROCEDURE', 'FUNCTION'
        }

        # 添加检测中文字符的函数
        def contains_chinese(text):
            return any('\u4e00' <= char <= '\u9fff' for char in text)
        
        # Fix double percentage signs in date format strings
        cleaned_sql = re.sub(r"(DATE_FORMAT\([^,]+,\s*)'%%([^']*)'", r"\1'%\2'", cleaned_sql)
        
        # Handle DATE_FORMAT with specific format string cleaning
        def clean_date_format(match):
            column = match.group(1).strip()
            format_string = match.group(2)
            # Clean specific date format patterns - handle any number of spaces between components
            format_string = re.sub(r'%Y\s*-\s*%m', '%Y-%m', format_string)
            format_string = re.sub(r'%y\s*-\s*%m', '%y-%m', format_string)
            format_string = re.sub(r'%Y\s*-\s*%M', '%Y-%M', format_string)
            format_string = re.sub(r'%y\s*-\s*%M', '%y-%M', format_string)
            # Remove any remaining spaces between format components
            format_string = re.sub(r'%([YyMmDd])\s*-\s*%([YyMmDd])', r'%\1-%\2', format_string)
            format_string = re.sub(r'%([YyMmDd])\s+%([YyMmDd])', r'%\1%\2', format_string)
            return f"DATE_FORMAT({column},'{format_string}')"
            
        cleaned_sql = re.sub(r"DATE_FORMAT\s*\(\s*([^,]+)\s*,\s*'([^']+)'\s*\)", 
                           clean_date_format, 
                           cleaned_sql)
        
        # 清理列名中的多余空格
        def clean_column_name(match):
            # 获取引号类型和列名
            quote = match.group(1)
            column = match.group(2)
            # 清理列名内部的空格
            cleaned_column = column.strip()
            return f"{quote}{cleaned_column}{quote}"
        
        # 清理被反引号、单引号或双引号包围的列名中的空格
        cleaned_sql = re.sub(r"([`'\"])\s*([^`'\"]+?)\s*\1", clean_column_name, cleaned_sql)
        
        # 存储别名映射，用于后续替换
        alias_mapping = {}
        
        # 处理 AS 别名中的空格和引号
        def clean_alias(match):
            expr = match.group(1)
            # 获取别名，优先使用第一个非 None 的匹配组
            alias = next((g for g in (match.group(2), match.group(3), match.group(4)) if g is not None), '')
            if not alias:
                return expr  # 如果没有找到有效的别名，直接返回表达式
            
            # 移除别名中的空格
            cleaned_alias = alias.strip()
            
            # 存储原始别名（去除空格后）和引号样式
            if match.group(3):  # 单引号
                alias_mapping[cleaned_alias] = f"'{cleaned_alias}'"
            elif match.group(4):  # 反引号
                alias_mapping[cleaned_alias] = f"`{cleaned_alias}`"
            else:  # 双引号或无引号
                alias_mapping[cleaned_alias] = f"\"{cleaned_alias}\""
            
            return f"{expr} AS {alias_mapping[cleaned_alias]}"
        
        # 匹配三种情况：无引号、单引号、反引号的别名，使用非捕获组 (?:...)
        cleaned_sql = re.sub(
            r'(\S+)\s+AS\s+(?:([a-zA-Z0-9_\u4e00-\u9fff]+)|\'([^\']+)\'|`([^`]+)`)',
            clean_alias,
            cleaned_sql,
            flags=re.IGNORECASE  # 添加忽略大小写标志
        )
        
        # Add spaces around SQL keywords
        keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING', 'JOIN',
                   'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'WITH', 'AS', 'ON', 'AND', 'OR',
                   'IN', 'NOT', 'NULL', 'IS', 'OVER', 'PARTITION BY']
        
        # Create a regex pattern that matches whole words only
        pattern = r'\b(' + '|'.join(keywords) + r')\b'
        # Add spaces before and after keywords
        cleaned_sql = re.sub(pattern, r' \1 ', cleaned_sql, flags=re.IGNORECASE)
        
        # 在处理减号运算符之前，先保护日期字符串中的连字符
        # 找出所有日期字符串模式并临时替换
        def protect_date_hyphens(match):
            date_str = match.group(1)
            # 将日期字符串中的连字符替换为特殊标记
            protected_date = date_str.replace('-', '§§§')
            return f"'{protected_date}'"
            
        # 保护日期字符串中的连字符，匹配 'YYYY-MM-DD' 格式
        cleaned_sql = re.sub(r"'(\d{4}-\d{2}-\d{2})'", protect_date_hyphens, cleaned_sql)
        
        # Add spaces around operators
        operators = [r'=', r'<', r'>', r'<=', r'>=', r'<>', r'\+', r'\*', r'/']  # Removed '-' from operators list
        for op in operators:
            cleaned_sql = re.sub(fr'(?<!\s){op}(?!\s)', f' {op} ', cleaned_sql)
            
        # Handle minus operator separately, excluding date patterns
        def handle_minus(match):
            # Get context before and after the minus sign
            before = match.string[max(0, match.start() - 20):match.start()]
            after = match.string[match.end():min(len(match.string), match.end() + 20)]
            
            # Check if we're inside quotes
            single_quotes_before = before.count("'") % 2 == 1
            double_quotes_before = before.count('"') % 2 == 1
            
            # If we're inside quotes, don't add spaces
            if single_quotes_before or double_quotes_before:
                return '-'  # 在引号内的减号不添加空格
                
            # Check if it's part of a number (negative number)
            if re.search(r'[\d.)]$', before) and re.search(r'^\d', after):
                return ' - '  # Arithmetic operation
            
            # Check if it's between numbers or identifiers
            if re.search(r'[a-zA-Z0-9_)]$', before) and re.search(r'^[a-zA-Z0-9_(]', after):
                return ' - '  # Likely an arithmetic operation
                
            # Default case - don't add spaces
            return '-'
            
        cleaned_sql = re.sub(r'-', handle_minus, cleaned_sql)
        
        # 恢复被保护的日期连字符
        cleaned_sql = cleaned_sql.replace('§§§', '-')
        
        # Fix multiple spaces
        cleaned_sql = re.sub(r'\s+', ' ', cleaned_sql)
        
        # Fix parentheses spacing (remove space after opening and before closing)
        cleaned_sql = re.sub(r'\(\s+', '(', cleaned_sql)
        cleaned_sql = re.sub(r'\s+\)', ')', cleaned_sql)
        
        # Trim spaces around dots in qualified names
        cleaned_sql = re.sub(r'\s*\.\s*', '.', cleaned_sql)
        
        # 处理 GROUP BY 和 ORDER BY 子句中的列引用
        def clean_by_clause(match):
            clause = match.group(1)  # GROUP BY 或 ORDER BY
            columns = match.group(2).split(',')
            cleaned_columns = []
            for col in columns:
                col = col.strip()
                
                # 检查是否是表达式（包含函数调用或运算符）
                if '(' in col or ')' in col:
                    # 如果是函数调用，保持原样
                    cleaned_columns.append(col)
                else:
                    # 移除所有空格但保留原始引号
                    if col.startswith('"') and col.endswith('"'):
                        # 如果有双引号，保持双引号并只清理内部空格
                        inner_content = col[1:-1].strip()
                        cleaned_columns.append(f"\"{inner_content}\"")
                    elif col.startswith("'") and col.endswith("'"):
                        # 如果有单引号，保持单引号并只清理内部空格
                        inner_content = col[1:-1].strip()
                        cleaned_columns.append(f"'{inner_content}'")
                    elif col.startswith('`') and col.endswith('`'):
                        # 如果有反引号，保持反引号并只清理内部空格
                        inner_content = col[1:-1].strip()
                        cleaned_columns.append(f"`{inner_content}`")
                    else:
                        # 如果没有引号，保持原样，只清理空格
                        cleaned_columns.append(col.strip())
            
            return f"{clause} {', '.join(cleaned_columns)}"
        
        # 处理 GROUP BY 子句
        cleaned_sql = re.sub(r'(GROUP BY)\s+([^()]+?)(?=\s+HAVING|\s+ORDER BY|\s+LIMIT|$)', 
                           clean_by_clause, 
                           cleaned_sql, 
                           flags=re.IGNORECASE)
        
        # 处理 ORDER BY 子句
        cleaned_sql = re.sub(r'(ORDER BY)\s+([^()]+?)(?=\s+LIMIT|$)', 
                           clean_by_clause, 
                           cleaned_sql, 
                           flags=re.IGNORECASE)
        
        # 确保 HAVING 关键字前后有空格
        cleaned_sql = re.sub(r'\s*HAVING\s*', ' HAVING ', cleaned_sql, flags=re.IGNORECASE)
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            cursor.execute(cleaned_sql)
            results = cursor.fetchall()
            
            # Convert Decimal to float in results
            for row in results:
                for key, value in row.items():
                    if isinstance(value, Decimal):
                        row[key] = float(value)
            
            return results
        except Error as e:
            # Return more detailed error information
            return {
                "error": str(e),
                "sql_state": e.sqlstate if hasattr(e, 'sqlstate') else None,
                "errno": e.errno if hasattr(e, 'errno') else None,
                "executed_query": cleaned_sql
            }
        finally:
            cursor.close()
            
    except Error as e:
        return {
            "error": f"Database connection error: {str(e)}",
            "connection_error": True
        }
    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()

def recommend_chart_type(data):
    """
    根据数据特征推荐合适的图表类型
    返回: {
        'type': 图表类型,
        'options': echarts配置项
    }
    """
    if not data or not isinstance(data, list) or len(data) == 0:
        return None
        
    # 获取列名
    columns = list(data[0].keys())
    
    # 分析数据类型
    numeric_columns = []
    categorical_columns = []
    date_columns = []
    
    for col in columns:
        sample = data[0][col]
        if isinstance(sample, (int, float, Decimal)):
            numeric_columns.append(col)
        elif isinstance(sample, (datetime, date)) or (isinstance(sample, str) and col.lower() == 'date'):
            date_columns.append(col)
        else:
            categorical_columns.append(col)
    
    # 根据数据特征推荐图表类型
    if len(numeric_columns) >= 1 and (len(date_columns) == 1 or len(categorical_columns) == 1):
        # 时间序列或分类数据 -> 折线图或柱状图
        x_axis = date_columns[0] if date_columns else categorical_columns[0]
        series_data = []
        
        for numeric_col in numeric_columns:
            series_data.append({
                'name': numeric_col,
                'type': 'line' if date_columns else 'bar',
                'smooth': True if date_columns else False,
                'data': [float(row[numeric_col]) if isinstance(row[numeric_col], Decimal) else row[numeric_col] for row in data]
            })
            
        return {
            'type': 'line' if date_columns else 'bar',
            'options': {
                
                'tooltip': {'trigger': 'axis'},
                'legend': {'data': numeric_columns},
                'xAxis': {
                    'type': 'category',
                    'data': [str(row[x_axis]) for row in data]
                },
                'yAxis': {'type': 'value'},
                'series': series_data
            }
        }
    
    elif len(numeric_columns) == 1 and len(categorical_columns) == 1:
        # 单个数值和单个分类 -> 饼图
        categories = []
        values = []
        for row in data:
            categories.append(str(row[categorical_columns[0]]))
            values.append(float(row[numeric_columns[0]]) if isinstance(row[numeric_columns[0]], Decimal) else row[numeric_columns[0]])
        
        return {
            'type': 'pie',
            'options': {
                
                'tooltip': {'trigger': 'item'},
                'legend': {'orient': 'vertical', 'left': 'left'},
                'series': [{
                    'type': 'pie',
                    'radius': '50%',
                    'data': [{'value': v, 'name': n} for v, n in zip(values, categories)]
                }]
            }
        }
    
    elif len(numeric_columns) >= 2:
        # 多个数值列 -> 散点图
        return {
            'type': 'scatter',
            'options': {
                
                'tooltip': {'trigger': 'item'},
                'xAxis': {'type': 'value', 'name': numeric_columns[0]},
                'yAxis': {'type': 'value', 'name': numeric_columns[1]},
                'series': [{
                    'type': 'scatter',
                    'data': [[float(row[numeric_columns[0]]) if isinstance(row[numeric_columns[0]], Decimal) else row[numeric_columns[0]],
                             float(row[numeric_columns[1]]) if isinstance(row[numeric_columns[1]], Decimal) else row[numeric_columns[1]]]
                            for row in data]
                }]
            }
        }
    
    return None

def generate_response(user_query):
    current_date = datetime.now().strftime("%Y-%m-%d")
    sql_model = os.getenv("SQL_MODEL", os.getenv("OPENAI_MODEL"))
    summary_model = os.getenv("SUMMARY_MODEL", os.getenv("OPENAI_MODEL"))
    # 获取 databaseTableSchema.md 里面的内容，给 databaseTableSchema 赋值
    with open('databaseTableSchema.md', 'r', encoding='utf-8') as file:
        databaseTableSchema = file.read()
    
    messages = []
    messages.append({"role": "system", "content": f"{databaseTableSchema}"})
    
    # 根据环境变量决定是否加载训练数据
    if os.getenv('LOAD_TRAINING_DATA', '否') == '是':
        try:
            with open('training_data.jsonl', 'r', encoding='utf-8') as file:
                for line in file:
                    if line.strip():  # 跳过空行
                        training_data = json.loads(line)
                        # 将训练数据中的消息添加到messages列表
                        messages.extend(training_data.get("messages", []))
            messages.append({"role": "user", "content": "后续的问题请参考我们之前的聊天内容。"})
            messages.append({"role": "assistant", "content": "好的，请继续提问。"})
        except Exception as e:
            print(f"Warning: Could not load training data: {str(e)}")
    
    # messages.append({"role": "user", "content": user_query})
    messages.append({"role": "user", "content": f"""当前日期是 {current_date}。{user_query}"""})

    tools = [
        {
            "type": "function",
            "function": {
                "name": "execute_sql",
                "description": "执行SQL查询语句",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "要执行的SQL查询语句"
                        }
                    },
                    "required": ["sql"]
                }
            }
        }
    ]

    try:
        # First, get SQL query using sql_client
        response = sql_client.chat.completions.create(
            model=sql_model,
            messages=messages,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "execute_sql"}},
            stream=True,
            temperature=0 # Add temperature=0 for SQL generation
        )

        # Initialize variables to collect the streaming response
        collected_sql = ""
        for chunk in response:
            if not hasattr(chunk, 'choices') or not chunk.choices:
                continue
            
            choice = chunk.choices[0]
            if not hasattr(choice, 'delta') or not choice.delta:
                continue
                
            # Handle tool calls in delta
            if hasattr(choice.delta, 'tool_calls') and choice.delta.tool_calls:
                tool_call = choice.delta.tool_calls[0]
                if hasattr(tool_call, 'function') and hasattr(tool_call.function, 'arguments'):
                    collected_sql += tool_call.function.arguments
            
            # Handle direct content in delta
            elif hasattr(choice.delta, 'content') and choice.delta.content:
                collected_sql += choice.delta.content

        # Process the collected SQL
        if collected_sql:
            try:
                # Try to parse as JSON first (for tool calls)
                try:
                    sql_args = json.loads(collected_sql)
                    sql_query = sql_args.get("sql", "")
                except json.JSONDecodeError:
                    # If not JSON, try to extract SQL from markdown blocks
                    sql_match = re.search(r'```sql\s*(.*?)\s*```', collected_sql, re.DOTALL)
                    if sql_match:
                        sql_query = sql_match.group(1).strip()
                    else:
                        # If no markdown blocks, use the raw content
                        sql_query = collected_sql.strip()

                if not sql_query:
                    raise ValueError("No SQL query could be extracted from the response")

                # Yield the SQL query
                yield {
                    "type": "sql_generation",
                    "content": sql_query
                }

                # Execute the SQL query
                query_results = execute_sql(sql_query)
                
                # 添加图表推荐
                chart_recommendation = recommend_chart_type(query_results) if isinstance(query_results, list) else None
                
                yield {
                    "type": "query_results",
                    "content": query_results,
                    "chart": chart_recommendation
                }

                # Continue with summary generation
                summary_messages =[]
                summary_messages.append({"role": "user", "content": user_query})          
                summary_messages.append({
                    "role": "assistant",
                    "content": f"已成功查询到满足条件的相关数据，具体信息如下：\n{json.dumps(query_results, cls=CustomJSONEncoder, ensure_ascii=False)}"
                })               

                # Get summary prompt from environment variable
                summary_prompt = os.getenv('SUMMARY_PROMPT', '请根据查询结果直接回答用户问题，使用简洁明了的语言。对于数值型结果，保留适当小数位数并使用合适的格式（如：313.07万元/套、1,000,000万元）。不要重复用户的问题，直接给出答案。')
                summary_messages.append({"role": "user", "content": summary_prompt})
                
                # 打印出summary_messages
                print("Summary Messages:")
                for msg in summary_messages:
                    print(f"{msg['role']}: {msg['content']}\n")

                final_response = summary_client.chat.completions.create(
                    model=summary_model,
                    messages=summary_messages,
                    stream=True,
                    temperature=0.6
                )

                summary = ""
                for chunk in final_response:
                    if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        summary += chunk.choices[0].delta.content
                        yield {
                            "type": "summary",
                            "content": summary
                        }

            except Exception as e:
                yield {"error": f"Error processing SQL response: {str(e)}"}
        else:
            yield {"error": "No valid response received from the API"}

    except Exception as e:
        yield {"error": f"API调用错误: {str(e)}"}

@app.route('/api/chat', methods=['POST'])
def chat():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
    data = request.json
    user_query = data.get('query', '')
    
    if not user_query:
        return jsonify({"error": "Query parameter is required"}), 400
    
    def generate():
        try:
            for response_chunk in generate_response(user_query):
                yield f"data: {json.dumps(response_chunk, cls=CustomJSONEncoder, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_response = {"error": str(e)}
            yield f"data: {json.dumps(error_response, cls=CustomJSONEncoder, ensure_ascii=False)}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*'
        }
    )

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/env-config')
def env_config():
    # Get sample questions from env
    sample_questions_str = os.getenv('SAMPLE_QUESTION', '[]')
    try:
        # Parse the string as JSON array
        sample_questions = json.loads(sample_questions_str)
    except json.JSONDecodeError:
        sample_questions = []
        
    return jsonify({
        'showSqlQuery': os.getenv('SHOW_SQL_QUERY', '是'),
        'showQueryResult': os.getenv('SHOW_QUERY_RESULT', '是'),
        'sampleQuestions': sample_questions
    })

@app.route('/favicon.ico')
def favicon():
    return '', 204  # No content

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)